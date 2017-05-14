#!/usr/bin/env python
# -*- coding: Latin-1 -*-

"""
This is the main module, the main interface classes and functions
are available in the top level hid package
"""
from __future__ import absolute_import
from __future__ import print_function

import sys
import ctypes
import threading
import collections
if sys.version_info >= (3,):
    import winreg
else:
    import _winreg as winreg

from ctypes import c_ubyte, c_ulong, c_ushort, c_wchar, byref, sizeof, \
        create_unicode_buffer
from ctypes.wintypes import DWORD

#local modules
from . import helpers
HIDError = helpers.HIDError

from . import winapi
setup_api    = winapi.setup_api
hid_dll      = winapi.hid_dll
HidP_Input   = winapi.HidP_Input
HidP_Output  = winapi.HidP_Output
HidP_Feature = winapi.HidP_Feature
HidStatus    = winapi.HidStatus

MAX_HID_STRING_LENGTH = 128

if not hasattr(threading.Thread, "is_alive"):
    # in python <2.6 is_alive was called isAlive
    threading.Thread.is_alive = threading.Thread.isAlive

USAGE = c_ushort
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

USAGE_EVENTS = [
    HID_EVT_NONE,
    HID_EVT_ALL,
    HID_EVT_CHANGED,
    HID_EVT_PRESSED,
    HID_EVT_RELEASED,
    HID_EVT_SET,
    HID_EVT_CLEAR,
] = list(range(7))

def get_full_usage_id(page_id, usage_id):
    """Convert to composite 32 bit page and usage ids"""
    return (page_id << 16) | usage_id

def get_usage_page_id(full_usage_id):
    """Extract 16 bits page id from full usage id (32 bits)"""
    return (full_usage_id >> 16) & 0xffff

def get_short_usage_id(full_usage_id):
    """Extract 16 bits usage id from full usage id (32 bits)"""
    return full_usage_id & 0xffff

def hid_device_path_exists(device_path, guid = None):
    """Test if required device_path is still valid
    (HID device connected to host)
    """
    # expecing HID devices
    if not guid:
        guid = winapi.GetHidGuid()

    info_data         = winapi.SP_DEVINFO_DATA()
    info_data.cb_size = sizeof(winapi.SP_DEVINFO_DATA)

    with winapi.DeviceInterfaceSetInfo(guid) as h_info:
        for interface_data in winapi.enum_device_interfaces(h_info, guid):
            test_device_path = winapi.get_device_path(h_info,
                    interface_data,
                    byref(info_data))
            if test_device_path == device_path:
                return True
    # Not any device now with that path
    return False

def find_all_hid_devices():
    "Finds all HID devices connected to the system"
    #
    # From DDK documentation (finding and Opening HID collection):
    # After a user-mode application is loaded, it does the following sequence
    # of operations:
    #
    #   * Calls HidD_GetHidGuid to obtain the system-defined GUID for HIDClass
    #     devices.
    #
    #   * Calls SetupDiGetClassDevs to obtain a handle to an opaque device
    #     information set that describes the device interfaces supported by all
    #     the HID collections currently installed in the system. The
    #     application should specify DIGCF_PRESENT and DIGCF_INTERFACEDEVICE
    #     in the Flags parameter passed to SetupDiGetClassDevs.
    #
    #   * Calls SetupDiEnumDeviceInterfaces repeatedly to retrieve all the
    #     available interface information.
    #
    #   * Calls SetupDiGetDeviceInterfaceDetail to format interface information
    #     for each collection as a SP_INTERFACE_DEVICE_DETAIL_DATA structure.
    #     The device_path member of this structure contains the user-mode name
    #     that the application uses with the Win32 function CreateFile to
    #     obtain a file handle to a HID collection.
    #
    # get HID device class guid
    guid = winapi.GetHidGuid()

    # retrieve all the available interface information.
    results = []
    required_size = DWORD()

    info_data         = winapi.SP_DEVINFO_DATA()
    info_data.cb_size = sizeof(winapi.SP_DEVINFO_DATA)

    with winapi.DeviceInterfaceSetInfo(guid) as h_info:
        for interface_data in winapi.enum_device_interfaces(h_info, guid):
            device_path = winapi.get_device_path(h_info,
                    interface_data,
                    byref(info_data))

            parent_device = c_ulong()

            #get parent instance id (so we can discriminate on port)
            if setup_api.CM_Get_Parent(byref(parent_device),
                    info_data.dev_inst, 0) != 0: #CR_SUCCESS = 0
                parent_device.value = 0 #null

            #get unique instance id string
            required_size.value = 0
            winapi.SetupDiGetDeviceInstanceId(h_info, byref(info_data),
                    None, 0,
                    byref(required_size) )

            device_instance_id = create_unicode_buffer(required_size.value)
            if required_size.value > 0:
                winapi.SetupDiGetDeviceInstanceId(h_info, byref(info_data),
                        device_instance_id, required_size,
                        byref(required_size) )

                hid_device = HidDevice(device_path,
                        parent_device.value, device_instance_id.value )
            else:
                hid_device = HidDevice(device_path, parent_device.value )

            # add device to results, if not protected
            if hid_device.vendor_id:
                results.append(hid_device)
    return results

class HidDeviceFilter(object):
    """This class allows searching for HID devices currently connected to
    the system, it also allows to search for specific devices  (by filtering)
    """
    def __init__(self, **kwrds):
        """Initialize filter from a named target parameters.
        I.e. product_id=0x0123
        """
        self.filter_params = kwrds

    def get_devices_by_parent(self, hid_filter=None):
        """Group devices returned from filter query in order \
        by devcice parent id.
        """
        all_devs = self.get_devices(hid_filter)
        dev_group = dict()
        for hid_device in all_devs:
            #keep a list of known devices matching parent device Ids
            parent_id = hid_device.get_parent_instance_id()
            device_set = dev_group.get(parent_id, [])
            device_set.append(hid_device)
            if parent_id not in dev_group:
                #add new
                dev_group[parent_id] = device_set
        return dev_group

    def get_devices(self, hid_filter = None):
        """Filter a HID device list by current object parameters. Devices
        must match the all of the filtering parameters
        """
        if not hid_filter: #empty list or called without any parameters
            if type(hid_filter) == type(None):
                #request to query connected devices
                hid_filter = find_all_hid_devices()
            else:
                return hid_filter
        #initially all accepted
        results = {}.fromkeys(hid_filter)

        #the filter parameters
        validating_attributes = list(self.filter_params.keys())

        #first filter out restricted access devices
        if not len(results):
            return {}

        for device in list(results.keys()):
            if not device.is_active():
                del results[device]

        if not len(results):
            return {}

        #filter out
        for item in validating_attributes:
            if item.endswith("_includes"):
                item = item[:-len("_includes")]
            elif item.endswith("_mask"):
                item = item[:-len("_mask")]
            elif item +"_mask" in self.filter_params or item + "_includes" \
                    in self.filter_params:
                continue # value mask or string search is being queried
            elif item not in HidDevice.filter_attributes:
                continue # field does not exist sys.error.write(...)
            #start filtering out
            for device in list(results.keys()):
                if not hasattr(device, item):
                    del results[device]
                elif item + "_mask" in validating_attributes:
                    #masked value
                    if getattr(device, item) & self.filter_params[item + \
                            "_mask"] != self.filter_params[item] \
                            & self.filter_params[item + "_mask"]:
                        del results[device]
                elif item + "_includes" in validating_attributes:
                    #subset item
                    if self.filter_params[item + "_includes"] not in \
                            getattr(device, item):
                        del results[device]
                else:
                    #plain comparison
                    if getattr(device, item) != self.filter_params[item]:
                        del results[device]
            #
        return list(results.keys())

MAX_DEVICE_ID_LEN = 200 + 1 #+EOL (just in case)
class HidDeviceBaseClass(object):
    "Utility parent class for main HID device class"
    _raw_reports_lock = threading.Lock()

    def __init__(self):
        "initializer"
        pass

class HidDevice(HidDeviceBaseClass):
    """This class is the main interface to physical HID devices"""
    MAX_MANUFACTURER_STRING_LEN = 128 #it's actually 126 + 1 (null)
    MAX_PRODUCT_STRING_LEN      = 128 #it's actually 126 + 1 (null)
    MAX_SERIAL_NUMBER_LEN       = 64

    filter_attributes = ["vendor_id", "product_id", "version_number",
        "product_name", "vendor_name"]

    def get_parent_instance_id(self):
        """Retreive system instance id (numerical value)"""
        return self.parent_instance_id

    def get_parent_device(self):
        """Retreive parent device string id"""
        if not self.parent_instance_id:
            return ""
        dev_buffer_type = winapi.c_tchar * MAX_DEVICE_ID_LEN
        dev_buffer = dev_buffer_type()
        try:
            if winapi.CM_Get_Device_ID(self.parent_instance_id, byref(dev_buffer),
                    MAX_DEVICE_ID_LEN, 0) == 0: #success
                return dev_buffer.value
            return ""
        finally:
            del dev_buffer
            del dev_buffer_type

    def __init__(self, device_path, parent_instance_id = 0, instance_id=""):
        "Interface for HID device as referenced by device_path parameter"
        #allow safe access (and object browsing)
        self.__open_status = False
        self.__input_report_templates = dict()

        #initialize hardware related vars
        self.__button_caps_storage     = list()
        self.report_set                = dict()
        self.__evt_handlers            = dict()
        self.__reading_thread          = None
        self.__input_processing_thread = None
        self.__raw_handler             = None
        self._input_report_queue       = None
        self.hid_caps                  = None
        self.ptr_preparsed_data        = None
        self.hid_handle                = None
        self.usages_storage            = dict()

        self.device_path        = device_path
        self.instance_id        = instance_id
        self.parent_instance_id = parent_instance_id
        self.product_name       = ""
        self.vendor_name        = ""
        self.serial_number      = ""
        self.vendor_id          = 0
        self.product_id         = 0
        self.version_number     = 0
        HidDeviceBaseClass.__init__(self)

        # HID device handle first
        h_hid = INVALID_HANDLE_VALUE
        try:
            h_hid = int( winapi.CreateFile(device_path,
                winapi.GENERIC_READ | winapi.GENERIC_WRITE,
                winapi.FILE_SHARE_READ | winapi.FILE_SHARE_WRITE,
                None, winapi.OPEN_EXISTING, 0, 0))
        except:
            pass

        if h_hid == INVALID_HANDLE_VALUE:
            return

        try:
            # get device attributes
            hidd_attributes = winapi.HIDD_ATTRIBUTES()
            hidd_attributes.cb_size = sizeof(hidd_attributes)
            if not hid_dll.HidD_GetAttributes(h_hid, byref(hidd_attributes)):
                del hidd_attributes
                return #can't read attributes

            #set local references
            self.vendor_id  = hidd_attributes.vendor_id
            self.product_id = hidd_attributes.product_id
            self.version_number = hidd_attributes.version_number
            del hidd_attributes

            # manufacturer string
            vendor_string_type = c_wchar * self.MAX_MANUFACTURER_STRING_LEN
            vendor_name = vendor_string_type()
            if not hid_dll.HidD_GetManufacturerString(h_hid,
                    byref(vendor_name),
                    sizeof(vendor_name)) or not len(vendor_name.value):
                # would be any possibility to get a vendor id table?,
                # maybe not worth it
                self.vendor_name = "Unknown manufacturer"
            else:
                self.vendor_name = vendor_name.value
            del vendor_name
            del vendor_string_type

            # string buffer for product string
            product_name_type = c_wchar * self.MAX_PRODUCT_STRING_LEN
            product_name = product_name_type()
            if not hid_dll.HidD_GetProductString(h_hid,
                        byref(product_name),
                        sizeof(product_name)) or not len(product_name.value):
                # alternate method, refer to windows registry for product
                # information
                path_parts = device_path[len("\\\\.\\"):].split("#")
                h_register = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                    "SYSTEM\\CurrentControlSet\\Enum\\" + \
                    path_parts[0] + "\\" + \
                    path_parts[1] + "\\" + \
                    path_parts[2] )
                self.product_name, other = winreg.QueryValueEx(h_register,
                        "DeviceDesc")
                winreg.CloseKey(h_register)
            else:
                self.product_name = product_name.value
            del product_name
            del product_name_type

            # serial number string
            serial_number_string = c_wchar * self.MAX_SERIAL_NUMBER_LEN
            serial_number = serial_number_string()
            if not hid_dll.HidD_GetSerialNumberString(h_hid,
                    byref(serial_number),
                    sizeof(serial_number)) or not len(serial_number.value):
                self.serial_number = ""
            else:
                self.serial_number = serial_number.value
            del serial_number
            del serial_number_string
        finally:
            # clean up
            winapi.CloseHandle(h_hid)

    def is_active(self):
        """Poll if device is still valid"""
        if not self.vendor_id:
            return False
        return True

    def open(self, output_only = False, shared = True):
        """Open HID device and obtain 'Collection Information'.
        It effectively prepares the HidDevice object for reading and writing
        """
        if self.is_opened():
            raise HIDError("Device already opened")
        sharing_flags = 0
        if shared:
            sharing_flags = winapi.FILE_SHARE_READ | winapi.FILE_SHARE_WRITE
        hid_handle = winapi.CreateFile(
            self.device_path,
            winapi.GENERIC_READ | winapi.GENERIC_WRITE,
            sharing_flags,
            None, # no security
            winapi.OPEN_EXISTING,
            winapi.FILE_ATTRIBUTE_NORMAL | winapi.FILE_FLAG_OVERLAPPED,
            0 )

        if not hid_handle or hid_handle == INVALID_HANDLE_VALUE:
            raise HIDError("Error opening HID device: %s\n"%self.product_name)
        #get pre parsed data
        ptr_preparsed_data = ctypes.c_void_p()
        if not hid_dll.HidD_GetPreparsedData(int(hid_handle),
                byref(ptr_preparsed_data)):
            winapi.CloseHandle(int(hid_handle))
            raise HIDError("Failure to get HID pre parsed data")
        self.ptr_preparsed_data = ptr_preparsed_data

        self.hid_handle = hid_handle

        #get top level capabilities
        self.hid_caps = winapi.HIDP_CAPS()
        HidStatus( hid_dll.HidP_GetCaps(ptr_preparsed_data,
            byref(self.hid_caps)) )

        #proceed with button capabilities
        caps_length = c_ulong()

        all_items = [\
            (HidP_Input,   winapi.HIDP_BUTTON_CAPS,
                self.hid_caps.number_input_button_caps,
                hid_dll.HidP_GetButtonCaps
            ),
            (HidP_Input,   winapi.HIDP_VALUE_CAPS,
                self.hid_caps.number_input_value_caps,
                hid_dll.HidP_GetValueCaps
            ),
            (HidP_Output,  winapi.HIDP_BUTTON_CAPS,
                self.hid_caps.number_output_button_caps,
                hid_dll.HidP_GetButtonCaps
            ),
            (HidP_Output,  winapi.HIDP_VALUE_CAPS,
                self.hid_caps.number_output_value_caps,
                hid_dll.HidP_GetValueCaps
            ),
            (HidP_Feature, winapi.HIDP_BUTTON_CAPS,
                self.hid_caps.number_feature_button_caps,
                hid_dll.HidP_GetButtonCaps
            ),
            (HidP_Feature, winapi.HIDP_VALUE_CAPS,
                self.hid_caps.number_feature_value_caps,
                hid_dll.HidP_GetValueCaps
            ),
        ]

        for report_kind, struct_kind, max_items, get_control_caps in all_items:
            if not int(max_items):
                continue #nothing here
            #create storage for control/data
            ctrl_array_type = struct_kind * max_items
            ctrl_array_struct = ctrl_array_type()

            #target max size for API function
            caps_length.value = max_items
            HidStatus( get_control_caps(\
                report_kind,
                byref(ctrl_array_struct),
                byref(caps_length),
                ptr_preparsed_data) )
            #keep reference of usages
            for idx in range(caps_length.value):
                usage_item = HidPUsageCaps( ctrl_array_struct[idx] )
                #by report type
                if report_kind not in self.usages_storage:
                    self.usages_storage[report_kind] = list()
                self.usages_storage[report_kind].append( usage_item )
                #also add report_id to known reports set
                if report_kind not in self.report_set:
                    self.report_set[report_kind] = set()
                self.report_set[report_kind].add( usage_item.report_id )
            del ctrl_array_struct
            del ctrl_array_type

        # now is the time to consider the device opened, as report
        # handling threads enforce it
        self.__open_status = True

        #now prepare the input report handler
        self.__input_report_templates = dict()
        if not output_only and self.hid_caps.input_report_byte_length and \
                HidP_Input in self.report_set:
            #first make templates for easy parsing input reports
            for report_id in self.report_set[HidP_Input]:
                self.__input_report_templates[report_id] = \
                        HidReport( self, HidP_Input, report_id )
            #prepare input reports handlers
            self._input_report_queue = HidDevice.InputReportQueue( \
                    self.max_input_queue_size,
                    self.hid_caps.input_report_byte_length)
            self.__input_processing_thread = \
                    HidDevice.InputReportProcessingThread(self)
            self.__reading_thread = HidDevice.InputReportReaderThread( \
                self, self.hid_caps.input_report_byte_length)
        # clean up

    def get_physical_descriptor(self):
        """Returns physical HID device descriptor
        """
        raw_data_type = c_ubyte * 1024
        raw_data = raw_data_type()
        if hid_dll.HidD_GetPhysicalDescriptor(self.hid_handle,
            byref(raw_data), 1024 ):
            return [x for x in raw_data]
        return []

    def send_output_report(self, data):
        """Send input/output/feature report ID = report_id, data should be a
        c_ubyte object with included the required report data
        """
        assert( self.is_opened() )
        #make sure we have c_ubyte array storage
        if not ( isinstance(data, ctypes.Array) and \
                issubclass(data._type_, c_ubyte) ):
            raw_data_type = c_ubyte * len(data)
            raw_data = raw_data_type()
            for index in range( len(data) ):
                raw_data[index] = data[index]
        else:
            raw_data = data
        #
        # Adding a lock when writing (overlapped writes)
        over_write = winapi.OVERLAPPED()
        over_write.h_event = winapi.CreateEvent(None, 0, 0, None)
        if over_write.h_event:
            try:
                overlapped_write = over_write
                winapi.WriteFile(int(self.hid_handle), byref(raw_data), len(raw_data),
                    None, byref(overlapped_write)) #none overlapped
                error = ctypes.GetLastError()
                if error == winapi.ERROR_IO_PENDING:
                    # overlapped operation in progress
                    result = error
                elif error == 1167:
                    raise HIDError("Error device disconnected before write")
                else:
                    raise HIDError("Error %d when trying to write to HID "\
                        "device: %s"%(error, ctypes.FormatError(error)) )
                result = winapi.WaitForSingleObject(overlapped_write.h_event, 10000 )
                if result != winapi.WAIT_OBJECT_0:
                    # If the write times out make sure to
                    # cancel it, otherwise memory could
                    # get corrupted if the async write
                    # completes after this functions returns
                    winapi.CancelIo( int(self.hid_handle) )
                    raise HIDError("Write timed out")
            finally:
                # Make sure the event is closed so resources aren't leaked
                winapi.CloseHandle(over_write.h_event)
        else:
            return winapi.WriteFile(int(self.hid_handle), byref(raw_data),
                len(raw_data),
                None, None) #none overlapped
        return True #completed

    def send_feature_report(self, data):
        """Send input/output/feature report ID = report_id, data should be a
        c_byte object with included the required report data
        """
        assert( self.is_opened() )
        #make sure we have c_ubyte array storage
        if not ( isinstance(data, ctypes.Array) and issubclass(data._type_,
                c_ubyte) ):
            raw_data_type = c_ubyte * len(data)
            raw_data = raw_data_type()
            for index in range( len(data) ):
                raw_data[index] = data[index]
        else:
            raw_data = data

        return hid_dll.HidD_SetFeature(int(self.hid_handle), byref(raw_data),
                len(raw_data))

    def __reset_vars(self):
        """Reset vars (for init or gc)"""
        self.__button_caps_storage = list()
        self.usages_storage = dict()
        self.report_set = dict()
        self.ptr_preparsed_data = None
        self.hid_handle = None

        #don't clean up the report queue because the
        #consumer & producer threads might needed it
        self.__evt_handlers = dict()
        #other
        self.__reading_thread = None
        self.__input_processing_thread = None
        self._input_report_queue = None
        #

    def is_plugged(self):
        """Check if device still plugged to USB host"""
        return self.device_path and hid_device_path_exists(self.device_path)

    def is_opened(self):
        """Check if device path resource open status"""
        return self.__open_status

    def close(self):
        """Release system resources"""
        # free parsed data
        if not self.is_opened():
            return
        self.__open_status = False

        # abort all running threads first
        if self.__reading_thread and self.__reading_thread.is_alive():
            self.__reading_thread.abort()

        #avoid posting new reports
        if self._input_report_queue:
            self._input_report_queue.release_events()

        if self.__input_processing_thread and \
                self.__input_processing_thread.is_alive():
            self.__input_processing_thread.abort()

        #properly close API handlers and pointers
        if self.ptr_preparsed_data:
            ptr_preparsed_data = self.ptr_preparsed_data
            self.ptr_preparsed_data = None
            hid_dll.HidD_FreePreparsedData(ptr_preparsed_data)

        # wait for the reading thread to complete before closing device handle
        if self.__reading_thread:
            self.__reading_thread.join()

        if self.hid_handle:
            winapi.CloseHandle(self.hid_handle)

        # make sure report procesing thread is closed
        if self.__input_processing_thread:
            self.__input_processing_thread.join()

        #reset vars (for GC)
        button_caps_storage = self.__button_caps_storage
        self.__reset_vars()

        while button_caps_storage:
            item = button_caps_storage.pop()
            del item

    def __find_reports(self, report_type, usage_page, usage_id = 0):
        "Find input report referencing HID usage control/data item"
        if not self.is_opened():
            raise HIDError("Device must be opened")
        #
        results = list()
        if usage_page:
            for report_id in self.report_set.get( report_type, set() ):
                #build report object, gathering usages matching report_id
                report_obj = HidReport(self, report_type, report_id)
                if get_full_usage_id(usage_page, usage_id) in report_obj:
                    results.append( report_obj )
        else:
            #all (any one)
            for report_id in self.report_set.get(report_type, set()):
                report_obj = HidReport(self, report_type, report_id)
                results.append( report_obj )
        return results

    def count_all_feature_reports(self):
        """Retreive total number of available feature reports"""
        return self.hid_caps.number_feature_button_caps + \
            self.hid_caps.number_feature_value_caps

    def find_input_reports(self, usage_page = 0, usage_id = 0):
        "Find input reports referencing HID usage item"
        return self.__find_reports(HidP_Input, usage_page, usage_id)

    def find_output_reports(self, usage_page = 0, usage_id = 0):
        "Find output report referencing HID usage control/data item"
        return self.__find_reports(HidP_Output, usage_page, usage_id)

    def find_feature_reports(self, usage_page = 0, usage_id = 0):
        "Find feature report referencing HID usage control/data item"
        return self.__find_reports(HidP_Feature, usage_page, usage_id)

    def find_any_reports(self, usage_page = 0, usage_id = 0):
        """Find any report type referencing HID usage control/data item.
        Results are returned in a dictionary mapping report_type to usage
        lists.
        """
        items = [
            (HidP_Input,    self.find_input_reports(usage_page, usage_id)),
            (HidP_Output,   self.find_output_reports(usage_page, usage_id)),
            (HidP_Feature,  self.find_feature_reports(usage_page, usage_id)),
        ]
        return dict([(t, r) for t, r in items if r])

    max_input_queue_size = 20
    evt_decision = {
        #a=old_value, b=new_value
        HID_EVT_NONE:       lambda a,b: False,
        HID_EVT_ALL:        lambda a,b: True, #usage in report
        HID_EVT_CHANGED:    lambda a,b: a != b,
        HID_EVT_PRESSED:    lambda a,b: b and not a,
        HID_EVT_RELEASED:   lambda a,b: a and not b,
        HID_EVT_SET:        lambda a,b: bool(b),
        HID_EVT_CLEAR:      lambda a,b: not b,
    }

    @helpers.synchronized(HidDeviceBaseClass._raw_reports_lock)
    def _process_raw_report(self, raw_report):
        "Default raw input report data handler"
        if not self.is_opened():
            return
        if not self.__evt_handlers and not self.__raw_handler:
            return

        if not raw_report[0]  and \
                (raw_report[0] not in self.__input_report_templates):
            # windows sends an empty array when disconnecting
            # but, this might have a collision with report_id = 0
            if not hid_device_path_exists(self.device_path):
                #windows XP sends empty report when disconnecting
                self.__reading_thread.abort() #device disconnected
            return

        if self.__raw_handler:
            #this might slow down data throughput, but at the expense of safety
            self.__raw_handler(helpers.ReadOnlyList(raw_report))
            return

        # using pre-parsed report templates, by report id
        report_template = self.__input_report_templates[raw_report[0]]
        # old condition snapshot
        old_values = report_template.get_usages()
        # parse incoming data
        report_template.set_raw_data(raw_report)
        # and compare it
        event_applies = self.evt_decision
        evt_handlers  = self.__evt_handlers
        for key in report_template.keys():
            if key not in evt_handlers:
                continue
            #check if event handler exist!
            for event_kind, handlers in evt_handlers[key].items():
                #key=event_kind, values=handler set
                new_value = report_template[key].value
                if not event_applies[event_kind](old_values[key], new_value):
                    continue
                #decision applies, call handlers
                for function_handler in handlers:
                    #check if the application wants some particular parameter
                    if handlers[function_handler]:
                        function_handler(new_value,
                                event_kind, handlers[function_handler])
                    else:
                        function_handler(new_value, event_kind)

    def set_raw_data_handler(self, funct):
        "Set external raw data handler, set to None to restore default"
        self.__raw_handler = funct

    def find_input_usage(self, full_usage_id):
        """Check if full usage Id included in input reports set
        Parameters:
            full_usage_id       Full target usage, use get_full_usage_id

        Returns:
            Report ID as integer value, or None if report does not exist with
            target usage. Nottice that report ID 0 is a valid report.
        """
        for report_id, report_obj in self.__input_report_templates.items():
            if full_usage_id in report_obj:
                return report_id
        return None #report_id might be 0

    def add_event_handler(self, full_usage_id, handler_function,
            event_kind = HID_EVT_ALL, aux_data = None):
        """Add event handler for usage value/button changes,
        returns True if the handler function was updated"""
        report_id = self.find_input_usage(full_usage_id)
        if report_id != None:
            # allow first zero to trigger changes and releases events
            self.__input_report_templates[report_id][full_usage_id].__value = None
        if report_id == None or not handler_function:
            # do not add handler
            return False
        assert(isinstance(handler_function, collections.Callable)) # must be a function
        # get dictionary for full usages
        top_map_handler = self.__evt_handlers.get(full_usage_id, dict())
        event_handler_set = top_map_handler.get(event_kind, dict())
        # update handler
        event_handler_set[handler_function] = aux_data
        if event_kind not in top_map_handler:
            top_map_handler[event_kind] = event_handler_set
        if full_usage_id not in self.__evt_handlers:
            self.__evt_handlers[full_usage_id] = top_map_handler
        return True

    class InputReportQueue(object):
        """Multi-threaded queue. Allows to queue reports from reading thread"""
        def __init__(self, max_size, report_size):
            self.__locked_down = False
            self.max_size = max_size
            self.repport_buffer_type = c_ubyte * report_size
            self.used_queue = []
            self.fresh_queue = []
            self.used_lock = threading.Lock()
            self.fresh_lock = threading.Lock()
            self.posted_event = threading.Event()

        #@logging_decorator
        def get_new(self):
            "Allocates storage for input report"
            if self.__locked_down:
                return None
            self.used_lock.acquire()
            if len(self.used_queue):
                #we can reuse items
                empty_report = self.used_queue.pop(0)
                self.used_lock.release()
                ctypes.memset(empty_report, 0, sizeof(empty_report))
            else:
                self.used_lock.release()
                #create brand new storage
                #auto initialized to '0' by ctypes
                empty_report = self.repport_buffer_type()
            return empty_report

        def reuse(self, raw_report):
            "Reuse not posted report"
            if self.__locked_down:
                return
            if not raw_report:
                return
            self.used_lock.acquire()
            #we can reuse this item
            self.used_queue.append(raw_report)
            self.used_lock.release()


        #@logging_decorator
        def post(self, raw_report):
            """Used by reading thread to post a new input report."""
            if self.__locked_down:
                self.posted_event.set()
                return
            self.fresh_lock.acquire()
            self.fresh_queue.append( raw_report )
            self.posted_event.set()
            self.fresh_lock.release()

        #@logging_decorator
        def get(self):
            """Used to retreive one report form the queue"""
            if self.__locked_down:
                return None

            #wait for data
            self.posted_event.wait()
            self.fresh_lock.acquire()

            if self.__locked_down:
                self.fresh_lock.release()
                return None

            item = self.fresh_queue.pop(0)
            if not self.fresh_queue:
                # emtpy
                self.posted_event.clear()
            self.fresh_lock.release()
            return item

        def release_events(self):
            """Release thread locks."""
            self.__locked_down = True
            self.posted_event.set()

    class InputReportProcessingThread(threading.Thread):
        "Input reports handler helper class"
        def __init__(self, hid_object):
            threading.Thread.__init__(self)
            self.__abort = False
            self.hid_object = hid_object
            self.daemon = True
            self.start()

        def abort(self):
            """Cancel processing."""
            self.__abort = True

        def run(self):
            """Start collecting input reports and post it to subscribed
            Hid device"""
            hid_object = self.hid_object
            report_queue = hid_object._input_report_queue
            while not self.__abort and hid_object.is_opened():
                raw_report = report_queue.get()
                if not raw_report or self.__abort:
                    break
                hid_object._process_raw_report(raw_report)
                # reuse the report (avoid allocating new memory)
                report_queue.reuse(raw_report)

    class InputReportReaderThread(threading.Thread):
        "Helper to receive input reports"
        def __init__(self, hid_object, raw_report_size):
            threading.Thread.__init__(self)
            self.__abort = False
            self.__active = False
            self.hid_object = hid_object
            self.report_queue = hid_object._input_report_queue
            hid_handle = int( hid_object.hid_handle )
            self.raw_report_size = raw_report_size
            self.__h_read_event = None
            self.__abort_lock = threading.RLock()
            if hid_object and hid_handle and self.raw_report_size \
                    and self.report_queue:
                #only if input reports are available
                self.daemon = True
                self.start()
            else:
                hid_object.close()

        def abort(self):
            """Stop collectiong reports."""
            with self.__abort_lock:
                if not self.__abort:
                    # The abort variable must be set to true
                    # before sending the event, otherwise
                    # the reader thread might skip
                    # CancelIo
                    self.__abort = True
                    if self.__h_read_event:
                        # force overlapped events competition
                        winapi.SetEvent(self.__h_read_event)

        def is_active(self):
            "main reading loop is running (bool)"
            return bool(self.__active)

        def run(self):
            if not self.raw_report_size:
                # don't raise any error as the hid object can still be used
                # for writing reports
                raise HIDError("Attempting to read input reports on non "\
                    "capable HID device")

            over_read = winapi.OVERLAPPED()
            self.__h_read_event = winapi.CreateEvent(None, 0, 0, None)
            over_read.h_event = self.__h_read_event
            if not over_read.h_event:
                raise HIDError("Error when create hid event resource")
            try:
                bytes_read = c_ulong()
                #
                hid_object = self.hid_object
                input_report_queue = self.report_queue
                report_len = self.raw_report_size
                #main loop active
                self.__active = True
                while not self.__abort:
                    #get storage
                    buf_report = input_report_queue.get_new()
                    if not buf_report or self.__abort:
                        break
                    bytes_read.value = 0

                    with self.__abort_lock:
                        # Call to ReadFile must only be done if
                        # abort isn't set.
                        if self.__abort:
                            break
                        # async read from device
                        result = winapi.ReadFile(hid_object.hid_handle,
                            byref(buf_report), report_len, byref(bytes_read),
                            byref(over_read) )

                    if not result:
                        error = ctypes.GetLastError()
                        if error == winapi.ERROR_IO_PENDING:
                            # overlapped operation in progress
                            result = error
                        elif error == 1167:
                            # device disconnected
                            break
                        else:
                            raise HIDError("Error %d when trying to read from HID "\
                                "device: %s"%(error, ctypes.FormatError(error)) )
                    if result == winapi.ERROR_IO_PENDING:
                        #wait for event
                        result = winapi.WaitForSingleObject( \
                            over_read.h_event,
                            winapi.INFINITE )
                        if result != winapi.WAIT_OBJECT_0 or self.__abort: #success
                            #Cancel the ReadFile call.  The read must not be in
                            #progress when run() returns, since the buffers used
                            #in the call will go out of scope and get freed.  If
                            #new data arrives (the read finishes) after these
                            #buffers have been freed then this can cause python
                            #to crash.
                            winapi.CancelIo( hid_object.hid_handle )
                            break #device has being disconnected
                    # signal raw data already read
                    input_report_queue.post( buf_report )
            finally:
                #clean up
                self.__active = False
                self.__abort = True
                self.__h_read_event = None #delete read event so it isn't be used by abort()
                winapi.CloseHandle(over_read.h_event)
                del over_read

    def __repr__(self):
        return "HID device (vID=0x%04x, pID=0x%04x, v=0x%04x); %s; %s, " \
            "Path: %s" % (self.vendor_id, self.product_id, self.version_number,\
            self.vendor_name, self.product_name, self.device_path)

class ReportItem(object):
    """Represents a single usage field in a report."""
    def __init__(self, hid_report, caps_record, usage_id = 0):
        # from here we can get the parent hid_object
        self.hid_report = hid_report
        self.__is_button = caps_record.is_button
        self.__is_value  = caps_record.is_value
        self.__is_value_array = bool(self.__is_value and \
            caps_record.report_count > 1)
        self.__bit_size = 1
        self.__report_count = 1
        if not caps_record.is_range:
            self.usage_id = caps_record.usage
        else:
            self.usage_id = usage_id
        self.__report_id_value = caps_record.report_id
        self.page_id = caps_record.usage_page
        self.__value = 0
        if caps_record.is_range:
            #reference to usage within usage range
            offset = usage_id - caps_record.usage_min 
            self.data_index = caps_record.data_index_min + offset
            self.string_index = caps_record.string_min + offset
            self.designator_index = caps_record.designator_min + offset
        else:
            #straight reference
            self.data_index = caps_record.data_index
            self.string_index = caps_record.string_index
            self.designator_index = caps_record.designator_index
        #verify it item is value array
        if self.__is_value:
            if self.__is_value_array:
                byte_size = int((caps_record.bit_size * caps_record.report_count)//8)
                if (caps_record.bit_size * caps_record.report_count) % 8:
                    # TODO: This seems not supported by Windows
                    byte_size += 1
                value_type = c_ubyte * byte_size
                self.__value = value_type()
            self.__bit_size = caps_record.bit_size
            self.__report_count = caps_record.report_count

    def __len__(self):
        return self.__report_count

    def __setitem__(self, index, value):
        "Allow to access value array by index"
        if not self.__is_value_array:
            raise ValueError("Report item is not value usage array")
        if index < self.__report_count:
            byte_index = int( (index * self.__bit_size) // 8 )
            bit_index  = (index * self.__bit_size) % 8
            bit_mask = ((1 << self.__bit_size) - 1)
            self.__value[byte_index] &= ~(bit_mask << bit_index)
            self.__value[byte_index] |= (value & bit_mask) << bit_index
        else:
            raise IndexError

    def __getitem__(self, index):
        "Allow to access value array by index"
        if not self.__is_value_array:
            raise ValueError("Report item is not value usage array")
        if index < self.__report_count:
            byte_index = int( (index * self.__bit_size) // 8 )
            bit_index = (index * self.__bit_size) % 8
            return ((self.__value[byte_index] >> bit_index) & \
                    ((1 << self.__bit_size) - 1) )
        else:
            raise IndexError

    def set_value(self, value):
        """Set usage value within report"""
        if self.__is_value_array:
            if len(value) == self.__report_count:
                for index, item in enumerate(value):
                    self.__setitem__(index, item)
            else:
                raise ValueError("Value size should match report item size "\
                    "length" )
        else:
            self.__value = value & ((1 << self.__bit_size) - 1) #valid bits only

    def get_value(self):
        """Retreive usage value within report"""
        if self.__is_value_array:
            if self.__bit_size == 8: #matching c_ubyte
                return list(self.__value)
            else:
                result = []
                for i in range(self.__report_count):
                    result.append(self.__getitem__(i))
                return result
        else:
            return self.__value
    #value property
    value = property(get_value, set_value)

    @property
    def value_array(self):
        """Retreive usage value as value array"""
        #read only property
        return self.__value

    def key(self):
        "returns unique usage page & id long value"
        return (self.page_id << 16) | self.usage_id

    def is_value(self):
        """Validate if usage is value (not 'button')"""
        return self.__is_value

    def is_button(self):
        """Validate if usage is button (not value)"""
        return self.__is_button

    def is_value_array(self):
        """Validate if usage was described as value array"""
        return self.__is_value_array

    def get_usage_string(self):
        """Returns usage representation string (as embedded in HID device
        if available)
        """
        if self.string_index:
            usage_string_type = c_wchar * MAX_HID_STRING_LENGTH
            # 128 max string length
            abuffer = usage_string_type()
            hid_dll.HidD_GetIndexedString(
                self.hid_report.get_hid_object().hid_handle,
                self.string_index,
                byref(abuffer), MAX_HID_STRING_LENGTH-1 )
            return abuffer.value
        return ""

    #read only properties
    @property
    def report_id(self):
        """Retreive Report Id numeric value"""
        return self.__report_id_value

    def __repr__(self):
        res = []
        if self.string_index:
            res.append( self.get_usage_string() )
        res.append( "page_id=%s"%hex(self.page_id) )
        res.append( "usage_id=%s"%hex(self.usage_id) )
        if self.__value != None:
            res.append( "value=%s" % str(self.get_value()))
        else:
            res.append( "value=[None])" )
        usage_type = ""
        if self.is_button():
            usage_type = "Button"
        elif self.is_value():
            usage_type = "Value"
        return usage_type + "Usage item, %s (" % hex(get_full_usage_id ( \
            self.page_id, self.usage_id)) + ', '.join(res) + ')'
# class ReportItem finishes ***********************

class HidReport(object):
    """This class interfaces an actual HID physical report, providing a wrapper
    that exposes specific usages (usage page and usage ID) as a usage_id value
    map (dictionary).

    Example: A HID device might have an output report ID = 0x01, with the
    following usages; 0x20 as a boolean (button), and 0x21 as a 3 bit value,
    then querying the HID object for the output report (by using
    hid_object.get_output_report(0x01))
    """
    #
    def __init__(self, hid_object, report_type, report_id):
        hid_caps = hid_object.hid_caps
        if report_type == HidP_Input:
            self.__raw_report_size = hid_caps.input_report_byte_length
        elif report_type == HidP_Output:
            self.__raw_report_size = hid_caps.output_report_byte_length
        elif report_type == HidP_Feature:
            self.__raw_report_size = hid_caps.feature_report_byte_length
        else:
            raise HIDError("Unsupported report type")
        self.__report_kind = report_type  #target report type
        self.__value_array_items = list() #array of usages items
        self.__hid_object = hid_object      #parent hid object
        self.__report_id = c_ubyte(report_id)  #target report Id
        self.__items = dict()       #access items by 'full usage' key
        self.__idx_items = dict()  #access internal items by HID DLL usage index
        self.__raw_data = None       #buffer storage (if needed)
        self.__usage_data_list = None #hid API HIDP_DATA array (if allocated)
        #build report items list, browse parent hid object for report items
        for item in hid_object.usages_storage.get(report_type, []):
            if item.report_id == report_id:
                if not item.is_range:
                    #regular 'single' usage
                    report_item = ReportItem(self, item)
                    self.__items[report_item.key()] = report_item
                    self.__idx_items[report_item.data_index] = report_item
                    #item is value array?
                    if report_item.is_value_array():
                        self.__value_array_items.append(report_item)
                else:
                    for usage_id in range(item.usage_min,
                            item.usage_max):
                        report_item =  ReportItem(self, item, usage_id)
                        self.__items[report_item.key()] = report_item
                        self.__idx_items[report_item.data_index] = report_item

            #
        #
    __report_kind_dict = {
        HidP_Input: "Input",
        HidP_Output: "Output",
        HidP_Feature: "Feature",
    }
    #read only properties
    @property
    def report_id(self):
        """Retreive asociated report Id value"""
        return self.__report_id.value

    @property
    def report_type(self):
        """Retreive report type as numeric value (input, output, feature)"""
        return self.__report_kind_dict[self.__report_kind]

    @property
    def hid_object(self):
        """Retreive asociated HID device instance"""
        return self.__hid_object

    def __repr__(self):
        return "HID report object (%s report, id=0x%02x), %d items included" \
            % (self.report_type, self.__report_id.value, len(self.__items) )

    def __getitem__(self, key):
        if isinstance(key, ReportItem):
            key = key.key()
        return self.__items[key]

    def __setitem__(self, key, value):
        """set report item value"""
        item = self.__getitem__(key)
        item.value = value

    def __contains__(self, key):
        if isinstance(key, ReportItem):
            key = key.key()
        return key in self.__items

    def __len__(self):
        return len(self.__items)

    def has_key(self, key):
        """Test for key (as standard dicts)"""
        return self.__contains__(key)

    def items(self):
        """Return key, value pairs (as standard dicts)"""
        return list(self.__items.items())

    def keys(self):
        """Return stored element keys (as standard dicts)"""
        return self.__items.keys()

    def values(self):
        """Return stored elements (as standard dicts)"""
        return self.__items.values()

    def get_hid_object(self):
        """Retreive reference to parent HID device"""
        return self.__hid_object

    def get_usages(self):
        "Return a dictionary mapping full usages Ids to plain values"
        result = dict()
        for key, usage in self.items():
            result[key] = usage.value
        return result

    def __alloc_raw_data(self, initial_values=None):
        """Pre-allocate re-usagle memory"""
        #allocate c_ubyte storage
        if self.__raw_data == None: #first time only, create storage
            raw_data_type = c_ubyte * self.__raw_report_size
            self.__raw_data = raw_data_type()
        elif initial_values == self.__raw_data:
            # already
            return
        else:
            #initialize
            ctypes.memset(self.__raw_data, 0, len(self.__raw_data))
        if initial_values:
            for index in range(len(initial_values)):
                self.__raw_data[index] = initial_values[index]

    def set_raw_data(self, raw_data):
        """Set usage values based on given raw data, item[0] is report_id,
        length should match 'raw_data_length' value, best performance if
        raw_data is c_ubyte ctypes array object type
        """
        #pre-parsed data should exist
        assert(self.__hid_object.is_opened())
        #valid length
        if len(raw_data) != self.__raw_report_size:
            raise HIDError( "Report size has to be %d elements (bytes)" \
                % self.__raw_report_size )
        # copy to internal storage
        self.__alloc_raw_data(raw_data)

        if not self.__usage_data_list: # create HIDP_DATA buffer
            max_items = hid_dll.HidP_MaxDataListLength(self.__report_kind,
                self.__hid_object.ptr_preparsed_data)
            data_list_type = winapi.HIDP_DATA * max_items
            self.__usage_data_list = data_list_type()
        #reference HIDP_DATA buffer
        data_list = self.__usage_data_list
        data_len = c_ulong(len(data_list))

        #reset old values
        for item in self.values():
            if item.is_value_array():
                item.value = [0, ]*len(item)
            else:
                item.value = 0
        #ready, parse raw data
        HidStatus( hid_dll.HidP_GetData(self.__report_kind,
            byref(data_list), byref(data_len),
            self.__hid_object.ptr_preparsed_data,
            byref(self.__raw_data), len(self.__raw_data)) )

        #set values on internal report item objects
        for idx in range(data_len.value):
            value_item = data_list[idx]
            report_item = self.__idx_items.get(value_item.data_index)
            if not report_item:
                # This is not expected to happen
                continue
            if report_item.is_value():
                report_item.value = value_item.value.raw_value
            elif report_item.is_button():
                report_item.value = value_item.value.on
            else:
                pass # HID API should give us either, at least one of 'em
        #get values of array items
        for item in self.__value_array_items:
            #ask hid API to parse
            HidStatus( hid_dll.HidP_GetUsageValueArray(self.__report_kind,
                item.page_id,
                0, #link collection
                item.usage_id, #short usage
                byref(item.value_array), #output data (c_ubyte storage)
                len(item.value_array), self.__hid_object.ptr_preparsed_data,
                byref(self.__raw_data), len(self.__raw_data)) )
            #

    def __prepare_raw_data(self):
        "Format internal __raw_data storage according to usages setting"
        #pre-parsed data should exist
        if not self.__hid_object.ptr_preparsed_data:
            raise HIDError("HID object close or unable to request pre parsed "\
                "report data")

        # make sure pre-memory allocation already done
        self.__alloc_raw_data()

        try:
            HidStatus( hid_dll.HidP_InitializeReportForID(self.__report_kind,
                self.__report_id, self.__hid_object.ptr_preparsed_data,
                byref(self.__raw_data), self.__raw_report_size) )
            #
        except HIDError:
            self.__raw_data[0] = self.__report_id

        #check if we have pre-allocated usage storage
        if not self.__usage_data_list: # create HIDP_DATA buffer
            max_items = hid_dll.HidP_MaxDataListLength(self.__report_kind,
                self.__hid_object.ptr_preparsed_data)
            if not max_items:
                raise HIDError("Internal error while requesting usage length")
            data_list_type = winapi.HIDP_DATA * max_items
            self.__usage_data_list = data_list_type()

        #reference HIDP_DATA buffer
        data_list = self.__usage_data_list
        #set buttons and values usages first
        n_total_usages = 0
        single_usage = USAGE()
        single_usage_len = c_ulong()
        for data_index, report_item in self.__idx_items.items():
            if (not report_item.is_value_array()) and \
                    report_item.value != None:
                #set by user, include in request
                if report_item.is_button() and report_item.value:
                    # windows just can't handle button arrays!, we just don't
                    # know if usage is button array or plain single usage, so
                    # we set all usages at once
                    single_usage.value = report_item.usage_id
                    single_usage_len.value = 1
                    HidStatus( hid_dll.HidP_SetUsages(self.__report_kind,
                        report_item.page_id, 0,
                        byref(single_usage), byref(single_usage_len),
                        self.__hid_object.ptr_preparsed_data,
                        byref(self.__raw_data), self.__raw_report_size) )
                    continue
                elif report_item.is_value() and \
                        not report_item.is_value_array():
                    data_list[n_total_usages].value.raw_value = report_item.value
                else:
                    continue #do nothing
                data_list[n_total_usages].reserved = 0 #reset
                data_list[n_total_usages].data_index = data_index #reference
                n_total_usages += 1
        #set data if any usage is not 'none' (and not any value array)
        if n_total_usages:
            #some usages set
            usage_len = c_ulong(n_total_usages)
            HidStatus( hid_dll.HidP_SetData(self.__report_kind,
                byref(data_list), byref(usage_len),
                self.__hid_object.ptr_preparsed_data,
                byref(self.__raw_data), self.__raw_report_size) )
        #set values based on value arrays
        for report_item in self.__value_array_items:
            HidStatus( hid_dll.HidP_SetUsageValueArray(self.__report_kind,
                report_item.page_id,
                0, #all link collections
                report_item.usage_id,
                byref(report_item.value_array),
                len(report_item.value_array),
                self.__hid_object.ptr_preparsed_data, byref(self.__raw_data),
                len(self.__raw_data)) )

    def get_raw_data(self):
        """Get raw HID report based on internal report item settings,
        creates new c_ubytes storage
        """
        if self.__report_kind != HidP_Output \
                and self.__report_kind != HidP_Feature:
            raise HIDError("Only for output or feature reports")
        self.__prepare_raw_data()
        #return read-only object for internal storage
        return helpers.ReadOnlyList(self.__raw_data)

    def send(self, raw_data = None):
        """Prepare HID raw report (unless raw_data is provided) and send
        it to HID device
        """
        if self.__report_kind != HidP_Output \
                and self.__report_kind != HidP_Feature:
            raise HIDError("Only for output or feature reports")
        #valid length
        if raw_data and (len(raw_data) != self.__raw_report_size):
            raise HIDError("Report size has to be %d elements (bytes)" \
                % self.__raw_report_size)
        #should be valid report id
        if raw_data and raw_data[0] != self.__report_id.value:
            #hint, raw_data should be a plain list of integer values
            raise HIDError("Not matching report id")
        #
        if self.__report_kind != HidP_Output and \
                self.__report_kind != HidP_Feature:
            raise HIDError("Can only send output or feature reports")
        #
        if not raw_data:
            # we'll construct the raw report
            self.__prepare_raw_data()
        elif not ( isinstance(raw_data, ctypes.Array) and \
                issubclass(raw_data._type_, c_ubyte) ):
            # pre-memory allocation for performance
            self.__alloc_raw_data(raw_data)
        #reference proper object
        raw_data = self.__raw_data
        if self.__report_kind == HidP_Output:
            return self.__hid_object.send_output_report(raw_data)
        elif self.__report_kind == HidP_Feature:
            return self.__hid_object.send_feature_report(raw_data)
        else:
            pass #can't get here (yet)

    def get(self, do_process_raw_report = True):
        "Read report from device"
        assert(self.__hid_object.is_opened())
        if self.__report_kind != HidP_Input and \
                self.__report_kind != HidP_Feature:
            raise HIDError("Only for input or feature reports")
        # pre-alloc raw data
        self.__alloc_raw_data()

        # now use it
        raw_data = self.__raw_data
        raw_data[0] = self.__report_id
        read_function = None
        if self.__report_kind == HidP_Feature:
            read_function = hid_dll.HidD_GetFeature
        elif self.__report_kind == HidP_Input:
            read_function = hid_dll.HidD_GetInputReport
        if read_function and read_function(int(self.__hid_object.hid_handle),
                                           byref(raw_data), len(raw_data)):
            #success
            if do_process_raw_report:
                self.set_raw_data(raw_data)
                self.__hid_object._process_raw_report(raw_data)
            return helpers.ReadOnlyList(raw_data)
        return helpers.ReadOnlyList([])
    #class HIDReport finishes ***********************

class HidPUsageCaps(object):
    """Allow to keep usage parameters (regarless of windows type)
    in a common class."""
    def __init__(self, caps):
        # keep pylint happy
        self.report_id = 0

        for fname, ftype in caps._fields_:
            if fname.startswith('reserved'):
                continue
            if fname == 'union':
                continue
            setattr(self, fname, int(getattr(caps, fname)))
        if caps.is_range:
            range_struct = caps.union.range
        else:
            range_struct = caps.union.not_range
        for fname, ftype in range_struct._fields_:
            if fname.startswith('reserved'):
                continue
            if fname == 'union':
                continue
            setattr(self, fname, int(getattr(range_struct, fname)))
        self.is_value  = False
        self.is_button = False
        if isinstance(caps,  winapi.HIDP_BUTTON_CAPS):
            self.is_button = True
        elif isinstance(caps, winapi.HIDP_VALUE_CAPS):
            self.is_value = True
        else:
            pass

    def inspect(self):
        """Retreive dictionary of 'Field: Value' attributes"""
        results = {}
        for fname in dir(self):
            if not fname.startswith('_'):
                value = getattr(self, fname)
                if isinstance(value, collections.Callable):
                    continue
                results[fname] = value
        return results

def show_hids(target_vid = 0, target_pid = 0, output = None):
    """Check all HID devices conected to PC hosts."""
    # first be kind with local encodings
    if not output:
        # beware your script should manage encodings
        output = sys.stdout
    # then the big cheese...
    from . import tools
    all_hids = None
    if target_vid:
        if target_pid:
            # both vendor and product Id provided
            device_filter = HidDeviceFilter(vendor_id = target_vid,
                    product_id = target_pid)
        else:
            # only vendor id
            device_filter = HidDeviceFilter(vendor_id = target_vid)

        all_hids = device_filter.get_devices()
    else:
        all_hids = find_all_hid_devices()
    if all_hids:
        print("Found HID class devices!, writting details...")
        for dev in all_hids:
            device_name = str(dev)
            output.write(device_name)
            output.write('\n\n  Path:      %s\n' % dev.device_path)
            output.write('\n  Instance:  %s\n' % dev.instance_id)
            output.write('\n  Port (ID): %s\n' % dev.get_parent_instance_id())
            output.write('\n  Port (str):%s\n' % str(dev.get_parent_device()))
            #
            try:
                dev.open()
                tools.write_documentation(dev, output)
            finally:
                dev.close()
        print("done!")
    else:
        print("There's not any non system HID class device available")
#

