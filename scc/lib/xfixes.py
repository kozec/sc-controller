#!/usr/bin/env python2

"""
Basic and incomplete wrapper for XFixes library.
"""

from ctypes import CDLL, POINTER, c_void_p, Structure
from ctypes import c_ulong, c_int, c_short, c_ushort

libXFixes = CDLL('libXfixes.so.3')

# Types
XID = c_ulong
XserverRegion = c_ulong
Display = c_void_p
class XRectangle(Structure):
	_fields_ = [
		('x', c_short),
		('y', c_short),
		('width', c_ushort),
		('height', c_ushort),
	]

# Consants
SHAPE_BOUNDING	= 0
SHAPE_CLIP		= 1
SHAPE_INPUT		= 2


# Functions
create_region = libXFixes.XFixesCreateRegion
create_region.argtypes = [c_void_p, POINTER(XRectangle), c_int]
create_region.restype = XserverRegion
set_window_shape_region = libXFixes.XFixesSetWindowShapeRegion
set_window_shape_region.argtypes = [c_void_p, XID, c_int, c_int, c_int, XserverRegion]
destroy_region = libXFixes.XFixesDestroyRegion
destroy_region.argtypes = [c_void_p, XserverRegion]
