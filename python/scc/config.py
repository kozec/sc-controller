#!/usr/bin/env python2
"""
SC-Controller - Config

Handles loading, storing and querying config file
"""
from __future__ import unicode_literals

from scc.find_library import find_library
from scc.actions import lib_bindings
import logging, ctypes

log = logging.getLogger("Config")
lib_config = find_library("libscc-config")

class Config(object):
	CVT_STR_ARRAY		= 1
	CVT_DOUBLE			= 2
	CVT_STRING			= 3
	CVT_BOOL			= 4
	CVT_INT				= 10
	
	def __init__(self, filename=None):
		self.filename = filename
		self._cfg = None
		self.reload()
	
	def __del__(self):
		if self._cfg:
			lib_bindings.scc_config_unref(self._cfg)
			self._cfg = None
	
	def reload(self):
		""" (Re)loads configuration. Works as load(), but handles exceptions """
		self.__del__()
		if self.filename:
			f, err, cfg = None, None, None
			try:
				f = open(self.filename, "r")
			except IOError, e:
				err = str(e)
			if f:
				err = ctypes.create_string_buffer(255)
				cfg = lib_config.config_load_from(f.fileno,
						ctypes.by_ref(err), 255)
				f.close()
			if cfg:
				self.__del__()
				self._cfg = cfg
				return
			log.warning("Failed to load configuration; Creating new one.")
			log.warning("Reason: %s", err)
		
		self.__del__()
		self._cfg = lib_config.config_init()
	
	load = reload
	
	def get(self, key, default=None):
		cvt = lib_config.config_get_type(self._cfg, key)
		if cvt == 0:
			raise KeyError("Invalid config key: %s" % (key,))
		elif cvt == Config.CVT_INT:
			return lib_config.config_get_int(self._cfg, key)
		elif cvt == Config.CVT_DOUBLE:
			return lib_config.config_get_double(self._cfg, key)
		elif cvt == Config.CVT_BOOL:
			return True if lib_config.config_get_int(self._cfg, key) else False
		elif cvt == Config.CVT_STRING:
			return lib_config.config_get(self._cfg, key).decode("utf-8")
		else:
			raise TypeError("Unknown config value type: %i" % (cvt,))
	
	def set(self, key, value):
		t, r = type(value), -1
		if t in (str, unicode):
			r = lib_config.config_set(self._cfg, key, value.encode("utf-8"))
		elif t in (int, long, bool):
			r = lib_config.config_set_int(self._cfg, key, value)
		elif t == float:
			r = lib_config.config_set_double(self._cfg, key, value)
		else:
			raise TypeError("Cannot set %s" % (t,))
		if r == 1:
			return
		elif r == 0:
			raise MemoryError
		elif r == -1:
			raise KeyError("Invalid config key: %s" % (key,))
		elif r == -2:
			raise TypeError("Cannot set %s to '%s'" % (t, key))
		else:
			raise OSError(r)
	
	def __contains__(self, key):
		""" Returns true if there is such value """
		cvt = lib_config.config_get_type(self._cfg, key)
		return cvt != 0
	
	__getitem__ = get
	__setitem__ = set


lib_config.config_init.argtypes = []
lib_config.config_init.restype = ctypes.c_void_p

lib_config.config_load.argtypes = []
lib_config.config_load.restype = ctypes.c_void_p

lib_config.config_load_from.argtypes = [ ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t ]
lib_config.config_load_from.restype = ctypes.c_void_p

lib_config.config_get_type.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_get_type.restype = ctypes.c_int

lib_config.config_get_int.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_get_int.restype = ctypes.c_int64

lib_config.config_get_double.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_get_double.restype = ctypes.c_double

lib_config.config_get.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_get.restype = ctypes.c_char_p

lib_config.config_set.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p ]
lib_config.config_set.restype = ctypes.c_int

lib_config.config_set_int.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int64 ]
lib_config.config_set_int.restype = ctypes.c_int

lib_config.config_set_double.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.c_double ]
lib_config.config_set_double.restype = ctypes.c_int

