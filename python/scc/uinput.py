"""
SC Controller - UInput constants

Long time ago, this module actually handled uinput-related stuff.
Since that is now handled in c, now it just loads and keeps list of constants.
"""
from scc.find_library import find_library
from scc.lib.enum import IntEnum
from itertools import chain
import ctypes


class CEnumValue(ctypes.Structure):
	_fields_ = [
		("name",	ctypes.c_char_p),
		("value",	ctypes.c_uint32),
	]

def _load_constants():
	CEnumValueA = CEnumValue * 256
	
	lib_bindings = find_library("libscc-bindings")
	lib_bindings.scc_get_key_constants.argtypes = [ CEnumValueA, ctypes.c_size_t ]
	lib_bindings.scc_get_key_constants.restype = ctypes.c_size_t
	lib_bindings.scc_get_axis_constants.argtypes = [ CEnumValueA, ctypes.c_size_t ]
	lib_bindings.scc_get_axis_constants.restype = ctypes.c_size_t
	lib_bindings.scc_get_rels_constants.argtypes = [ CEnumValueA, ctypes.c_size_t ]
	lib_bindings.scc_get_rels_constants.restype = ctypes.c_size_t
	lib_bindings.scc_get_button_constants.argtypes = [ CEnumValueA, ctypes.c_size_t ]
	lib_bindings.scc_get_button_constants.restype = ctypes.c_size_t
	
	a = CEnumValueA()
	count = lib_bindings.scc_get_axis_constants(a, len(a))
	assert count <= len(a)
	Axes = IntEnum(value='Axes', names=( (a[i].name, a[i].value) for i in xrange(count) ))
	
	count = lib_bindings.scc_get_rels_constants(a, len(a))
	assert count <= len(a)
	Rels = IntEnum(value='Rels', names=( (a[i].name, a[i].value) for i in xrange(count) ))
	
	count = lib_bindings.scc_get_button_constants(a, len(a))
	assert count <= len(a)
	buttons = [ (a[i].name, a[i].value) for i in xrange(count) ]
	
	count = lib_bindings.scc_get_key_constants(a, len(a))
	assert count <= len(a)
	Keys = IntEnum(value='Keys', names=chain(
			( (a[i].name, a[i].value) for i in xrange(count) ),
			buttons
	))
	
	return Keys, Axes, Rels


__all__ = ['Keys', 'Axes', 'Rels']
Keys, Axes, Rels = _load_constants()

