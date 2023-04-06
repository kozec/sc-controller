#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
udevmonitor.py - enumerates and monitors devices using (e)udev

Copyright (C) 2018 by Kozec

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as published by
the Free Software Foundation

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

from collections import namedtuple
from ctypes.util import find_library
import os, ctypes, errno

class Eudev:
	LIB_NAME = "udev"
	
	def __init__(self):
		self._ctx = None
		try:
			self._lib = ctypes.cdll.LoadLibrary("libudev.so")
		except OSError:
			self._lib = ctypes.CDLL(find_library(self.LIB_NAME))
			if self._lib is None:
				raise ImportError("No library named udev")
		Eudev._setup_lib(self._lib)
		self._ctx = self._lib.udev_new()
		if self._ctx is None:
			raise OSError("Failed to initialize udev context")
	
	@staticmethod
	def _setup_lib(l):
		""" Just so it's away from init and can be folded in IDE """
		# udev
		l.udev_new.restype = ctypes.c_void_p
		l.udev_unref.argtypes = [ ctypes.c_void_p ]
		# enumeration
		l.udev_enumerate_new.argtypes = [ ctypes.c_void_p ]
		l.udev_enumerate_new.restype = ctypes.c_void_p
		l.udev_enumerate_unref.argtypes = [ ctypes.c_void_p ]
		l.udev_enumerate_scan_devices.argtypes = [ ctypes.c_void_p ]
		l.udev_enumerate_scan_devices.restype = ctypes.c_int
		l.udev_enumerate_get_list_entry.argtypes = [ ctypes.c_void_p ]
		l.udev_enumerate_get_list_entry.restype = ctypes.c_void_p
		l.udev_list_entry_get_next.argtypes = [ ctypes.c_void_p ]
		l.udev_list_entry_get_next.restype = ctypes.c_void_p
		l.udev_list_entry_get_value.argtypes = [ ctypes.c_void_p ]
		l.udev_list_entry_get_value.restype = ctypes.c_char_p
		l.udev_list_entry_get_name.argtypes = [ ctypes.c_void_p ]
		l.udev_list_entry_get_name.restype = ctypes.c_char_p
		# monitoring
		l.udev_monitor_new_from_netlink.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
		l.udev_monitor_new_from_netlink.restype = ctypes.c_void_p
		l.udev_monitor_unref.argtypes = [ ctypes.c_void_p ]
		l.udev_monitor_enable_receiving.argtypes = [ ctypes.c_void_p ]
		l.udev_monitor_enable_receiving.restype = ctypes.c_int
		l.udev_monitor_set_receive_buffer_size.argtypes = [ ctypes.c_void_p, ctypes.c_int ]
		l.udev_monitor_set_receive_buffer_size.restype = ctypes.c_int
		l.udev_monitor_get_fd.argtypes = [ ctypes.c_void_p ]
		l.udev_monitor_get_fd.restype = ctypes.c_int
		l.udev_monitor_receive_device.argtypes = [ ctypes.c_void_p ]
		l.udev_monitor_receive_device.restype = ctypes.c_void_p
		l.udev_monitor_filter_update.argtypes = [ ctypes.c_void_p ]
		l.udev_monitor_filter_update.restype = ctypes.c_int
		l.udev_monitor_filter_add_match_subsystem_devtype.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p ]
		l.udev_monitor_filter_add_match_subsystem_devtype.restype = ctypes.c_int
		l.udev_monitor_filter_add_match_tag.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
		l.udev_monitor_filter_add_match_tag.restype = ctypes.c_int
		# device
		l.udev_device_get_action.argtypes = [ ctypes.c_void_p ]
		l.udev_device_get_action.restype = ctypes.c_char_p
		l.udev_device_get_devnode.argtypes = [ ctypes.c_void_p ]
		l.udev_device_get_devnode.restype = ctypes.c_char_p
		l.udev_device_get_subsystem.argtypes = [ ctypes.c_void_p ]
		l.udev_device_get_subsystem.restype = ctypes.c_char_p
		l.udev_device_get_devtype.argtypes = [ ctypes.c_void_p ]
		l.udev_device_get_devtype.restype = ctypes.c_char_p
		l.udev_device_get_syspath.argtypes = [ ctypes.c_void_p ]
		l.udev_device_get_syspath.restype = ctypes.c_char_p
		l.udev_device_get_sysname.argtypes = [ ctypes.c_void_p ]
		l.udev_device_get_sysname.restype = ctypes.c_char_p
		l.udev_device_get_is_initialized.argtypes = [ ctypes.c_void_p ]
		l.udev_device_get_is_initialized.restype = ctypes.c_int
		l.udev_device_get_devnum.argtypes = [ ctypes.c_void_p ]
		l.udev_device_get_devnum.restype = ctypes.c_int
		l.udev_device_unref.argtypes = [ ctypes.c_void_p ]
		
		for name in dir(Enumerator):
			if "match_" in name:
				twoargs = getattr(getattr(Enumerator, name), "twoargs", False)
				fn = getattr(l, "udev_enumerate_add_" + name)
				if twoargs:
					fn.argtypes = [ ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p ]
				else:
					fn.argtypes = [ ctypes.c_void_p, ctypes.c_char_p ]
				fn.restype = ctypes.c_int
	
	
	def __del__(self):
		if self._ctx is not None:
			self._lib.udev_unref(self._ctx)
			self._ctx = None
	
	
	def enumerate(self, subclass=None):
		"""
		Returns new Enumerator instance.
		"""
		enumerator = self._lib.udev_enumerate_new(self._ctx)
		if enumerator is None:
			raise OSError("Failed to initialize enumerator")
		if subclass is not None:
			assert issubclass(subclass, Enumerator)
		subclass = subclass or Enumerator
		return subclass(self, enumerator)
	
	
	def monitor(self, subclass=None):
		"""
		Returns new Monitor instance.
		"""
		monitor = self._lib.udev_monitor_new_from_netlink(self._ctx, b"udev")
		if monitor is None:
			raise OSError("Failed to initialize monitor")
		if subclass is not None:
			assert issubclass(subclass, Monitor)
		subclass = subclass or Monitor
		return subclass(self, monitor)


def twoargs(fn):
	fn.twoargs = True
	return fn


class Enumerator:
	"""
	Iterable object used for enumerating available devices.
	Yields syspaths (strings).
	
	All match_* methods are returning self for chaining.
	"""
	def __init__(self, eudev, enumerator):
		self._eudev = eudev
		self._enumerator = enumerator
		self._keep_in_mem = []
		self._enumeration_started = False
		self._next = None
	
	
	def __del__(self):
		if self._enumerator is not None:
			self._eudev._lib.udev_enumerate_unref(self._enumerator)
			self._enumerator = None
	
	
	def _add_match(self, whichone, *pars):
		if self._enumeration_started:
			raise RuntimeError("Cannot add match after enumeration is started")
		fn = getattr(self._eudev._lib, "udev_enumerate_add_" + whichone)
		pars = [ ctypes.c_char_p(p) for p in pars ]
		self._keep_in_mem += pars
		err = fn(self._enumerator, *pars)
		if err < 0:
			raise OSError("udev_enumerate_add_%s: error %s" % (whichone, err))
		return self
	
	
	@twoargs
	def match_sysattr(self, sysattr, value): return self._add_match("match_sysattr", sysattr, value)
	@twoargs
	def nomatch_sysattr(self, sysattr, value): return self._add_match("nomatch_sysattr", sysattr, value)
	@twoargs
	def match_property(self, property, value): return self._add_match("match_property", property, value)
	def match_subsystem(self, subsystem): return self._add_match("match_subsystem", subsystem)
	def nomatch_subsystem(self, subsystem): return self._add_match("nomatch_subsystem", subsystem)
	def match_sysname(self, sysname): return self._add_match("match_sysname", sysname)
	def match_tag(self, tag): return self._add_match("match_tag", tag)
	def match_is_initialized(self): return self._add_match("match_is_initialized")
	# match_parent is not implemented
	
	
	def __iter__(self):
		if self._enumeration_started:
			raise RuntimeError("Cannot iterate same Enumerator twice")
		self._enumeration_started = True
		err = self._eudev._lib.udev_enumerate_scan_devices(self._enumerator)
		if err < 0:
			raise OSError("udev_enumerate_scan_devices: error %s" % (err, ))
		self._next = self._eudev._lib.udev_enumerate_get_list_entry(self._enumerator)
		return self
	
	
	def __next__(self):
		if not self._enumeration_started:
			self.__iter__()	# Starts the enumeration
		if self._next is None:
			raise StopIteration()
		rv = self._eudev._lib.udev_list_entry_get_name(self._next)
		if rv is None:
			raise OSError("udev_list_entry_get_name failed")
		self._next = self._eudev._lib.udev_list_entry_get_next(self._next)
		return str(rv)


class Monitor:
	"""
	Monitor object recieves device events.
	receive_device method blocks until next event is processed, so it can be
	used either in dumb loop, or called when select syscall reports descriptor
	returned by get_fd has data available.
	
	All match_* methods are returning self for chaining
	"""
	DeviceEvent = namedtuple("DeviceEvent", "action,node,initialized,subsystem,devtype,syspath,devnum")
	
	def __init__(self, eudev, monitor):
		self._eudev = eudev
		self._monitor = monitor
		self._monitor_started = False
		self._keep_in_mem = []
		self._enabled_matches = set()
	
	
	def __del__(self):
		if self._monitor is not None:
			self._eudev._lib.udev_monitor_unref(self._monitor)
			self._monitor = None
	
	
	def _add_match(self, whichone, *pars):
		key = tuple([whichone] + list(pars))
		if key in self._enabled_matches:
			# Already done
			return self
		fn = getattr(self._eudev._lib, "udev_monitor_filter_add_" + whichone)
		pars = [ ctypes.c_char_p(p) for p in pars ]
		self._keep_in_mem += pars
		err = fn(self._monitor, *pars)
		if err < 0:
			raise OSError("udev_monitor_filter_add_%s: error %s" % (whichone, errno.errorcode.get(err, err)))
		self._enabled_matches.add(key)
		if self._monitor_started:
			err = self._eudev._lib.udev_monitor_filter_update(self._monitor)
			if err < 0:
				raise OSError("udev_monitor_filter_update: error %s" % (errno.errorcode.get(err, err), ))
		return self
	
	
	def match_subsystem_devtype(self, subsystem, devtype=None):
		return self._add_match("match_subsystem_devtype", subsystem, devtype)
	def match_subsystem(self, subsystem):
		return self._add_match("match_subsystem_devtype", subsystem, None)
	def match_tag(self, tag):
		return self._add_match("match_tag", tag)
	
	def is_started(self):
		return self._monitor_started
	
	
	def get_fd(self):
		fileno = self._eudev._lib.udev_monitor_get_fd(self._monitor)
		if fileno < 0:
			raise OSError("udev_monitor_get_fd: error %s" % (errno.errorcode.get(fileno, fileno), ))
		return fileno
	
	
	def enable_receiving(self):
		""" Returns self for chaining """
		if self._monitor_started:
			return # Error, but unimportant
		err = self._eudev._lib.udev_monitor_enable_receiving(self._monitor)
		if err < 0:
			raise OSError("udev_monitor_enable_receiving: error %s" % (errno.errorcode.get(err, err)))
		self._monitor_started = True
		return self
	
	
	def set_receive_buffer_size(self, size):
		""" Returns self for chaining """
		err = self._eudev._lib.udev_monitor_set_receive_buffer_size(self._monitor, size)
		if err < 0:
			raise OSError("udev_monitor_set_receive_buffer_size: error %s" % (errno.errorcode.get(err, err)))
		return self
	
	
	fileno = get_fd				# python stuff likes this name better
	start = enable_receiving	# I like this name better
	
	
	def receive_device(self):
		if not self._monitor_started:
			self.enable_receiving()
		
		dev = self._eudev._lib.udev_monitor_receive_device(self._monitor)
		if dev is None:
			# udev_monitor_receive_device is _supposed_ to be blocking.
			# It doesn't looks that way
			return None
		
		event = Monitor.DeviceEvent(
			str(self._eudev._lib.udev_device_get_action(dev)),
			str(self._eudev._lib.udev_device_get_devnode(dev)),
			self._eudev._lib.udev_device_get_is_initialized(dev) == 1,
			str(self._eudev._lib.udev_device_get_subsystem(dev)),
			str(self._eudev._lib.udev_device_get_devtype(dev)),
			str(self._eudev._lib.udev_device_get_syspath(dev)),
			self._eudev._lib.udev_device_get_devnum(dev),
		)
		
		self._eudev._lib.udev_device_unref(dev)
		return event


if __name__ == "__main__":
	udev = Eudev()
	en = udev.enumerate().match_subsystem("hidraw")
	for i in en:
		print(i)
	
	m = udev.monitor().match_subsystem("hidraw").start()
	while True:
		d = m.receive_device()
		if d:
			print(os.major(d.devnum), os.minor(d.devnum), d)
