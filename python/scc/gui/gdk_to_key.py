#!/usr/bin/env python2
"""
SC-Controller - gdk_to_key

Maps Gdk.EventKey objects into Keys.KEY_* constants.
Used by ActionEditor (when grabbing the key)
"""
from __future__ import unicode_literals

from scc.find_library import find_library
from scc.uinput import Keys
import ctypes

lib_bindings = find_library("libscc-bindings")
lib_bindings.scc_hardware_keycode_to_keycode.argtypes = [ ctypes.c_uint16 ]
lib_bindings.scc_hardware_keycode_to_keycode.restype = ctypes.c_uint16


def keyevent_to_key(event):
	key = lib_bindings.scc_hardware_keycode_to_keycode(event.hardware_keycode)
	if not key:
		return None
	try:
		return Keys(key)
	except ValueError:
		return None

