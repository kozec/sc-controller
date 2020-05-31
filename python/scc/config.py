#!/usr/bin/env python2
"""
SC-Controller - Config

Handles loading, storing and querying config file
"""
from __future__ import unicode_literals

from scc.find_library import find_library
from scc.actions import lib_bindings
from weakref import WeakValueDictionary
import logging, platform, ctypes

log = logging.getLogger("Config")
lib_config = find_library("libscc-config")
SCC_CONFIG_ERROR_LIMIT = 1024


class Config(object):
	CVT_OBJECT			= 0
	CVT_STR_ARRAY		= 1
	CVT_DOUBLE			= 2
	CVT_STRING			= 3
	CVT_BOOL			= 4
	CVT_INVALID			= 6
	CVT_INT				= 11
	
	def __init__(self, filename=None, c_ptr=None):
		self._refs = WeakValueDictionary()
		self.filename = filename
		if c_ptr:
			self._fixed_cptr = True
			self._cfg = c_ptr
		else:
			self._fixed_cptr = False
			self._cfg = None
			self.reload()
	
	def __del__(self):
		if self._cfg:
			lib_bindings.scc_config_unref(self._cfg)
			self._cfg = None
	
	def save(self):
		if self._cfg:
			if not lib_config.config_save(self._cfg):
				raise OSError("Save failed")
	
	def set_prefix(self, prefix):
		assert self._cfg
		if platform.system() == "Windows":
			raise OSError("Not available")
		if not lib_config.config_set_prefix(self._cfg, prefix):
			raise MemoryError("Out of memory")
	
	class StrArray(object):
		"""
		Emulates list while updating target array in config
		"""
		def __init__(self, parent, key):
			self._parent = parent
			self._key = key
			data = (ctypes.c_char_p * 1024)()
			count = lib_config.config_get_strings(parent._cfg, key, data, 1024)
			if count < 0:
				# TODO: Retry with larger array if -2 is returned
				raise MemoryError("Out of memory")
			self._data = [ data[i].decode("utf-8") for i in xrange(count) ]
		
		def __len__(self):
			return len(self._data)
		
		def __iter__(self):
			return iter(self._data)
		
		def __getitem__(self, key):
			return self._data[key]
		
		# @staticdecorator
		def update_parent(fn):
			"""
			After array is changed, updates value on parent object.
			Decorator.
			"""
			def wrapper(self, *a, **b):
				rv = fn(self, *a, **b)
				if self._parent._refs.get(self._key) is self:
					self._parent.set(self._key, self)
				return rv
			wrapper.__name__ = fn.__name__
			return wrapper
		
		@update_parent
		def __setitem__(self, key, value):
			if type(value) not in (unicode, str):
				raise TypeError(type(value))
			self._data[key] = value
			
		@update_parent
		def append(self, value):
			self._data.append(value)
		
		@update_parent
		def pop(self, index=-1):
			return self._data.pop(index)
		
		@update_parent
		def reverse(self):
			return self._data.reverse()
		
		@update_parent
		def sort(self, *a, **b):
			return self._data.sort(*a, **b)
	
	class Subkey(object):
		"""
		Helper class that allows to use expressions like config['gui']['value']
		to access values deeper in hierarchy and treat configs like dictionaries.
		
		It supports only __getitem__ / __setitem__ protocol.
		"""
		
		def __init__(self, parent, prefix):
			self._parent = parent
			self._prefix = prefix
		
		def __repr__(self):
			return "<Subkey '%s'>" % (self._prefix,)
		
		def __getitem__(self, key, default=None):
			return self._parent.get("%s/%s" % (self._prefix, key), default)
		
		def __setitem__(self, key, value):
			return self._parent.set("%s/%s" % (self._prefix, key), value)
		
		def __iter__(self):
			return iter(self.keys())
		
		get = __getitem__
		
		def clear(self):
			self._parent.delete_key(self._prefix)
		
		def keys(self):
			return self._parent.keys(self._prefix)
		
		def values(self):
			return [ self[x] for x in self.keys() ]
	
	def reload(self):
		""" (Re)loads configuration. Works as load(), but handles exceptions """
		if self._fixed_cptr:
			log.warning("Attempted to reload Config object bound to specific c object")
			return
		self.__del__()
		if self.filename:
			err, cfg = None, None
			err = ctypes.create_string_buffer(SCC_CONFIG_ERROR_LIMIT)
			if platform.system() == "Windows":
				cfg = lib_config.config_load_from_key(self.filename, err)
			else:
				cfg = lib_config.config_load_from(self.filename, err)
			if cfg:
				self.__del__()
				self._cfg = cfg
				return
			if platform.system() == "Windows":
				raise OSError("Failed to open registry key '%s': %s" % (self.filename, err.value))
			log.warning("Failed to load configuration; Creating new one.")
			log.warning("Reason: %s", err.value)
		
		self.__del__()
		self._cfg = lib_config.config_init()
	
	load = reload
	
	def _get_key(self, key):
		rv = self._refs.get(key)
		if rv is None:
			self._refs[key] = rv = Config.Subkey(self, key)
		return rv
	
	def get(self, key, default=None):
		cvt = lib_config.config_get_type(self._cfg, key)
		if cvt == Config.CVT_INVALID:
			if lib_config.config_is_parent(self._cfg, key):
				return self._get_key(key)
			raise KeyError("Invalid config key: %s" % (key,))
		elif cvt == Config.CVT_OBJECT:
			return self._get_key(key)
		elif cvt == Config.CVT_INT:
			return lib_config.config_get_int(self._cfg, key)
		elif cvt == Config.CVT_DOUBLE:
			return lib_config.config_get_double(self._cfg, key)
		elif cvt == Config.CVT_BOOL:
			return True if lib_config.config_get_int(self._cfg, key) else False
		elif cvt == Config.CVT_STRING:
			return lib_config.config_get(self._cfg, key).decode("utf-8")
		elif cvt == Config.CVT_STR_ARRAY:
			rv = self._refs.get(key)
			if rv is None:
				self._refs[key] = rv = Config.StrArray(self, key)
			return rv
		else:
			raise TypeError("Unknown config value type: %i" % (cvt,))
	
	def set(self, key, value):
		t, r = type(value), -1
		if t in (str, unicode):
			r = lib_config.config_set(self._cfg, key, value.encode("utf-8"))
		elif t in (int, long, bool):
			r = lib_config.config_set_int(self._cfg, key, value)
		elif t == list or isinstance(value, Config.StrArray):
			values = (ctypes.c_char_p * len(value))()
			for (index, x) in enumerate(value):
				if type(x) not in (str, unicode):
					raise TypeError("Invalid list: Item at index %i is %s, not string" %
							(index, type(x)))
				values[index] = x
			
			r = lib_config.config_set_strings(self._cfg, key, values, len(value))
			if r == 1:
				self._refs.pop(key, None)
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
	
	def keys(self, path="/"):
		# TODO: Retry if exactly 1024 strings are returned - there may be more
		data = (ctypes.c_char_p * 1024)()
		count = lib_config.config_get_strings(self._cfg, path, data, 1024)
		if count < 0:
			# TODO: Retry with larger array if -2 is returned
			raise MemoryError("Out of memory")
		rv = [ data[i].decode("utf-8") for i in xrange(count) ]
		return rv
	
	def delete_key(self, path):
		lib_config.config_delete_key(self._cfg, path)
	
	def __iter__(self):
		return iter(self.keys())
	
	def __contains__(self, key):
		""" Returns true if there is such value """
		cvt = lib_config.config_get_type(self._cfg, key)
		return cvt != Config.CVT_INVALID
	
	def get_controller_config(self, controller_id, return_none=False):
		"""
		Returns Config object bound to configuration of controller with specified id.
		Throws OSError if config cannot be loaded, unless return_none is set.
		"""
		err = ctypes.create_string_buffer(SCC_CONFIG_ERROR_LIMIT)
		ptr = lib_config.config_get_controller_config(self._cfg,
					controller_id.encode("utf-8"), ctypes.byref(err))
		if not ptr:
			if return_none: return none
			raise OSError(err.value)
		return Config(c_ptr=ptr)
	
	def create_controller_config(self, controller_id):
		err = ctypes.create_string_buffer(SCC_CONFIG_ERROR_LIMIT)
		ptr = lib_config.config_create_controller_config(self._cfg,
					controller_id.encode("utf-8"), ctypes.byref(err))
		if not ptr:
			raise OSError(err.value)
		return Config(c_ptr=ptr)
	
	def get_controllers(self):
		# TODO: Retry if exactly 1024 strings are returned - there may be more
		data = (ctypes.c_char_p * 1024)()
		count = lib_config.config_get_controllers(self._cfg, data, 1024)
		rv = [ data[i].decode("utf-8") for i in xrange(count) ]
		# TODO: Is this a memory leak? Are pointers from 'data' deallocated automatically?
		return rv
	
	__getitem__ = get
	__setitem__ = set


lib_config.config_init.argtypes = []
lib_config.config_init.restype = ctypes.c_void_p

lib_config.config_load.argtypes = []
lib_config.config_load.restype = ctypes.c_void_p

if platform.system() == "Windows":
	lib_config.config_load_from_key.argtypes = [ ctypes.c_char_p, ctypes.c_char_p ]
	lib_config.config_load_from_key.restype = ctypes.c_void_p
else:
	lib_config.config_load_from.argtypes = [ ctypes.c_char_p, ctypes.c_char_p ]
	lib_config.config_load_from.restype = ctypes.c_void_p
	
	lib_config.config_set_prefix.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
	lib_config.config_set_prefix.restype = ctypes.c_bool

lib_config.config_set_strings.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_size_t ]
lib_config.config_set_strings.restype = ctypes.c_int

lib_config.config_save.argtypes = [ ctypes.c_void_p ]
lib_config.config_save.restype = ctypes.c_void_p

lib_config.config_get_type.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_get_type.restype = ctypes.c_int

lib_config.config_is_parent.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_is_parent.restype = ctypes.c_bool

lib_config.config_get_int.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_get_int.restype = ctypes.c_int64

lib_config.config_get_double.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_get_double.restype = ctypes.c_double

lib_config.config_get.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_get.restype = ctypes.c_char_p

lib_config.config_get_controllers.argtypes = [ ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_ssize_t ]
lib_config.config_set.restype = ctypes.c_ssize_t

lib_config.config_get_strings.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_ssize_t ]
lib_config.config_get_strings.restype = ctypes.c_ssize_t

lib_config.config_delete_key.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_delete_key.restype = None

lib_config.config_get_controller_config.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_get_controller_config.restype = ctypes.c_void_p

lib_config.config_create_controller_config.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
lib_config.config_create_controller_config.restype = ctypes.c_void_p

lib_config.config_set.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p ]
lib_config.config_set.restype = ctypes.c_int

lib_config.config_set_int.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int64 ]
lib_config.config_set_int.restype = ctypes.c_int

lib_config.config_set_double.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.c_double ]
lib_config.config_set_double.restype = ctypes.c_int

lib_bindings.scc_config_unref.argtypes = [ ctypes.c_void_p ]
lib_bindings.scc_config_unref.restype = None

