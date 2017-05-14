# -*- coding: utf-8 -*-
"""PnP Window Mixing.

Plug and Play nottifications are sent only to Window devices
(devices that have a window handle.

So regardless of the GUI toolkit used, the Mixin' classes
expose here can be used.
"""
from __future__ import absolute_import
from __future__ import print_function

import ctypes
from ctypes.wintypes import DWORD
from . import wnd_hook_mixin
from . import core
from . import winapi

WndProcHookMixin = wnd_hook_mixin.WndProcHookMixin
#for PNP notifications
class DevBroadcastDevInterface(ctypes.Structure):
    """DEV_BROADCAST_DEVICEINTERFACE ctypes structure wrapper"""
    _fields_ = [
        # size of the members plus the actual length of the dbcc_name string
        ("dbcc_size",       DWORD),
        ("dbcc_devicetype", DWORD),
        ("dbcc_reserved",   DWORD),
        ("dbcc_classguid",  winapi.GUID),
        ("dbcc_name",       ctypes.c_wchar),
    ]
    def __init__(self):
        """Initialize the fields for device interface registration"""
        ctypes.Structure.__init__(self)
        self.dbcc_size       = ctypes.sizeof(self)
        self.dbcc_devicetype = DBT_DEVTYP_DEVICEINTERFACE
        self.dbcc_classguid  = winapi.GetHidGuid()

#***********************************
# PnP definitions
WM_DEVICECHANGE     = 0x0219
# PC docked or undocked
DBT_CONFIGCHANGED   = 0x0018
# Device or piece of media has been inserted and is now available.
DBT_DEVICEARRIVAL   = 0x8000
# Device or piece of media has been removed.
DBT_DEVICEREMOVECOMPLETE = 0x8004

RegisterDeviceNotification = ctypes.windll.user32.RegisterDeviceNotificationW
RegisterDeviceNotification.restype  = ctypes.wintypes.HANDLE
RegisterDeviceNotification.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.LPVOID,
    DWORD
]

UnregisterDeviceNotification = ctypes.windll.user32.UnregisterDeviceNotification
UnregisterDeviceNotification.restype  = ctypes.wintypes.BOOL
UnregisterDeviceNotification.argtypes = [
    ctypes.wintypes.HANDLE,
]

#dbcc_devicetype, device interface only used
DBT_DEVTYP_DEVICEINTERFACE  = 0x00000005
DBT_DEVTYP_HANDLE           = 0x00000006

DEVICE_NOTIFY_WINDOW_HANDLE  = 0x00000000
DEVICE_NOTIFY_SERVICE_HANDLE = 0x00000001

class HidPnPWindowMixin(WndProcHookMixin):
    """Base for receiving PnP notifications.
    Just call HidPnPWindowMixin.__init__(my_hwnd) being
    my_hwnd the OS window handle (most GUI toolkits
    allow to get the system window handle).
    """
    def __init__(self, wnd_handle):
        """HidPnPWindowMixin initializer"""
        WndProcHookMixin.__init__(self, wnd_handle)
        self.__hid_hwnd = wnd_handle
        self.current_status = "unknown"
        #register hid notification msg handler
        self.__h_notify = self._register_hid_notification()
        if not self.__h_notify:
            raise core.HIDError("PnP notification setup failed!")
        else:
            WndProcHookMixin.add_msg_handler(self, WM_DEVICECHANGE,
                    self._on_hid_pnp)
            # add capability to filter out windows messages
            WndProcHookMixin.hook_wnd_proc(self)

    def unhook_wnd_proc(self):
        "This function must be called to clean up system resources"
        WndProcHookMixin.unhook_wnd_proc(self)
        if self.__h_notify:
            self._unregister_hid_notification() #ignore result

    def _on_hid_pnp(self, w_param, l_param):
        "Process WM_DEVICECHANGE system messages"
        new_status = "unknown"
        if w_param == DBT_DEVICEARRIVAL:
            # hid device attached
            notify_obj = None
            if int(l_param):
                # Disable this error since pylint doesn't reconize
                # that from_address actually exists
                # pylint: disable=no-member
                notify_obj = DevBroadcastDevInterface.from_address(l_param)
                #confirm if the right message received
            if notify_obj and \
                    notify_obj.dbcc_devicetype == DBT_DEVTYP_DEVICEINTERFACE:
                #only connect if already disconnected
                new_status = "connected"
        elif w_param == DBT_DEVICEREMOVECOMPLETE:
            # hid device removed
            notify_obj = None
            if int(l_param):
                # Disable this error since pylint doesn't reconize
                # that from_address actually exists
                # pylint: disable=no-member
                notify_obj = DevBroadcastDevInterface.from_address(l_param)
            if notify_obj and \
                    notify_obj.dbcc_devicetype == DBT_DEVTYP_DEVICEINTERFACE:
                #only connect if already disconnected
                new_status = "disconnected"

        #verify if need to call event handler
        if new_status != "unknown" and new_status != self.current_status:
            self.current_status = new_status
            self.on_hid_pnp(self.current_status)
        #
        return True

    def _register_hid_notification(self):
        """Register HID notification events on any window (passed by window
        handler), returns a notification handler"""
        # create structure, self initialized
        notify_obj = DevBroadcastDevInterface()
        h_notify = RegisterDeviceNotification(self.__hid_hwnd,
                ctypes.byref(notify_obj), DEVICE_NOTIFY_WINDOW_HANDLE)
        #
        return int(h_notify)

    def _unregister_hid_notification(self):
        "Remove PnP notification handler"
        if not int(self.__h_notify):
            return #invalid
        result          = UnregisterDeviceNotification(self.__h_notify)
        self.__h_notify = None
        return int(result)

    def on_hid_pnp(self, new_status):
        "'Virtual' like function to refresh update for connection status"
        print("HID:", new_status)
        return True

