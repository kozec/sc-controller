#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
``pywinusb.hid`` -- A package that simplifies HID communications on Windows
---------------------------------------------------------------------------

On Windows(TM), HID communications can be handled from user space
applications, this means that no additional drivers are needed for simple
HID interfacing.

``pywinusb.hid``, allows to find specific HID class devices, and unless
most simple HID interfacing libraries, allows to work using *HID usages*.

Usages are the 'spices' of HID communications, in summary a HID device
provides descriptors describing the proper way to extract information from
raw reports.

Still ``pywinusb.hid`` allows to work at the low 'raw report' level, but
the convenience provided by working on top level usages allows a cleaner
interface.
"""
from __future__ import absolute_import

__version__ = '0.4.1'
__author__  = 'Rene F. Aguirre <rene.f.aguirre@gmail.com>'
__url__     = 'https://github.com/rene-aguirre/pywinusb'
__all__     = []

from . import core
get_full_usage_id      = core.get_full_usage_id
get_usage_page_id      = core.get_usage_page_id
get_short_usage_id     = core.get_short_usage_id
hid_device_path_exists = core.hid_device_path_exists
find_all_hid_devices   = core.find_all_hid_devices
HidDeviceFilter        = core.HidDeviceFilter
HidDevice              = core.HidDevice
HID_EVT_NONE           = core.HID_EVT_NONE
HID_EVT_ALL            = core.HID_EVT_ALL
HID_EVT_CHANGED        = core.HID_EVT_CHANGED
HID_EVT_PRESSED        = core.HID_EVT_PRESSED
HID_EVT_RELEASED       = core.HID_EVT_RELEASED
HID_EVT_SET            = core.HID_EVT_SET
HID_EVT_CLEAR          = core.HID_EVT_CLEAR

from . import helpers
HIDError = helpers.HIDError

from . import hid_pnp_mixin
HidPnPWindowMixin = hid_pnp_mixin.HidPnPWindowMixin

