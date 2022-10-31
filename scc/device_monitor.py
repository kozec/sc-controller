#!/usr/bin/env python2
"""
SC-Controller - Device Monitor

Extends eudevmonitor with options to register callbacks and
manage plugging/releasing devices.
"""
from scc.lib.eudevmonitor import Eudev, Monitor
from scc.lib.ioctl_opt import IOR
from ctypes.util import find_library
import os, ctypes, fcntl, re, logging

log = logging.getLogger("DevMon")

RE_BT_NUMBERS = re.compile(r"[0-9A-F]{4}:([0-9A-F]{4}):([0-9A-F]{4}).*")
HCIGETCONNLIST = IOR(ord('H'), 212, ctypes.c_int)
HAVE_BLUETOOTH_LIB = False
try:
	btlib_name = find_library('bluetooth')
	assert btlib_name
	btlib = ctypes.CDLL(btlib_name)
	HAVE_BLUETOOTH_LIB = True
except: pass


class DeviceMonitor(Monitor):
	
	def __init__(self, *a):
		Monitor.__init__(self, *a)
		self.daemon = None
		self.dev_added_cbs = {}
		self.dev_removed_cbs = {}
		self.bt_addresses = {}
		self.known_devs = {}
	
	
	def add_callback(self, subsystem, vendor_id, product_id, added_cb, removed_cb):
		"""
		Adds function that is called when eudev monitor detects new, ready
		to use device.
		
		This has to be called from something called by init_drivers method.
		"""
		key = (subsystem, vendor_id, product_id)
		assert key not in self.dev_added_cbs
		self.match_subsystem(subsystem)
		
		self.dev_added_cbs[key] = added_cb
		self.dev_removed_cbs[key] = removed_cb
	
	
	def add_remove_callback(self, syspath, cb):
		"""
		Adds (possibly replaces) callback that will be called once
		device with specified syspath is disconnected.
		"""
		if syspath in self.known_devs:
			vendor, product, old_cb = self.known_devs.pop(syspath)
			self.known_devs[syspath] = (vendor, product, cb)
	
	
	def start(self):
		""" Registers poller and starts listening for events """
		if not HAVE_BLUETOOTH_LIB:
			log.warning("Failed to load libbluetooth.so, bluetooth support will be incomplete")
		poller = self.daemon.poller
		poller.register(self.fileno(), poller.POLLIN, self.on_data_ready)
		Monitor.start(self)
	
	
	def _on_new_syspath(self, subsystem, syspath):
		try:
			if subsystem == "input":
				vendor, product = None, None
			else:
				vendor, product = self.get_vendor_product(syspath, subsystem)
		except (OSError, IOError):
			# Cannot grab vendor & product, probably subdevice or bus itself
			return
		key = (subsystem, vendor, product)
		cb = self.dev_added_cbs.get(key)
		rem_cb = self.dev_removed_cbs.get(key)
		if cb:
			self.known_devs[syspath] = (vendor, product, rem_cb)
			try:
				if cb(syspath, vendor, product) is None:
					del self.known_devs[syspath]
			except Exception, e:
				log.exception(e)
				del self.known_devs[syspath]
	
	
	def _get_hci_addresses(self):
		if not HAVE_BLUETOOTH_LIB:
			return
		cl = hci_conn_list_req()
		cl.dev_id = btlib.hci_get_route(ctypes.c_void_p(0))
		if cl.dev_id < 0 or cl.dev_id > 65534:
			return
		cl.conn_num = 256
		
		s = btlib.hci_open_dev(cl.dev_id)
		if fcntl.ioctl(s, HCIGETCONNLIST, cl, True):
			log.error("Failed to list bluetooth collections")
			return
		
		for i in xrange(cl.conn_num):
			ci = cl.conn_info[i]
			id = "hci%s:%s" % (cl.dev_id, ci.handle)
			address = ":".join([ hex(x).lstrip("0x").zfill(2).upper() for x in reversed(ci.bdaddr) ])
			self.bt_addresses[id] = address
	
	
	def _dev_for_hci(self, syspath):
		"""
		For given syspath leading to ../hciX:ABCD, returns input device node
		"""
		name = syspath.split("/")[-1]
		if ":" not in name:
			return None
		addr = self.bt_addresses.get(name)
		for fname in os.listdir("/sys/bus/hid/devices/"):
			node = os.path.join("/sys/bus/hid/devices/", fname)
			try:
				node_addr = DeviceMonitor._find_bt_address(node)
			except IOError:
				continue
			try:
				# SteamOS 3 "Holo" return caps
				if node_addr.lower() == addr.lower():
					return node
			# None
			except AttributeError:
				pass
		return None
	
	
	def on_data_ready(self, *a):
		event = self.receive_device()
		if event:
			if event.action == "bind" and event.initialized:
				if event.syspath not in self.known_devs:
					self._on_new_syspath(event.subsystem, event.syspath)
			elif event.action == "add" and event.initialized and event.subsystem in ("input", "bluetooth"):
				# those are not bound
				if event.syspath not in self.known_devs:
					if event.subsystem == "bluetooth":
						self._get_hci_addresses()
					self._on_new_syspath(event.subsystem, event.syspath)
			elif event.action in ("remove", "unbind") and event.syspath in self.known_devs:
				vendor, product, cb = self.known_devs.pop(event.syspath)
				if cb:
					cb(event.syspath, vendor, product)
	
	
	def rescan(self):
		""" Scans and calls callbacks for already connected devices """
		self._get_hci_addresses()
		enumerator = self._eudev.enumerate()
		subsystem_to_vp_to_callback = {}
		
		for key, cb in self.dev_added_cbs.items():
			subsystem, vendor_id, product_id = key
			enumerator.match_subsystem(subsystem)
			if subsystem not in subsystem_to_vp_to_callback:
				subsystem_to_vp_to_callback[subsystem] = {}
			subsystem_to_vp_to_callback[subsystem][vendor_id, product_id] = cb
		
		for syspath in enumerator:
			if syspath not in self.known_devs:
				try:
					subsystem = DeviceMonitor.get_subsystem(syspath)
				except (IOError, OSError):
					continue
				if subsystem in subsystem_to_vp_to_callback:
					self._on_new_syspath(subsystem, syspath)
	
	
	def get_vendor_product(self, syspath, subsystem=None):
		"""
		For given syspath, reads and returns (vendor_id, product_id) as ints.
		
		May throw all kinds of OSErrors or IOErrors
		"""
		if os.path.exists(os.path.join(syspath, "idVendor")):
			vendor  = int(open(os.path.join(syspath, "idVendor")).read().strip(), 16)
			product = int(open(os.path.join(syspath, "idProduct")).read().strip(), 16)
			return vendor, product
		if subsystem is None:
			subsystem = DeviceMonitor.get_subsystem(syspath)
		if subsystem == "bluetooth":
			# Search for folder that matches regular expression...
			names = [ name for name in os.listdir(syspath)
				if os.path.isdir(syspath) and RE_BT_NUMBERS.match(name) ]
			if len(names) > 0:
				vendor, product = [ int(x, 16) for x in RE_BT_NUMBERS.match(names[0]).groups() ]
				return vendor, product
			# Above method works for anything _but_ SteamController
			# For that one, following desperate mess is needed
			node = self._dev_for_hci(syspath)
			if node:
				name = node.split("/")[-1]
				if RE_BT_NUMBERS.match(name):
					vendor, product = [ int(x, 16) for x in RE_BT_NUMBERS.match(name).groups() ]
					return vendor, product
		raise OSError("Cannot determine vendor and product IDs")
	
	
	def get_hidraw(self, syspath):
		"""
		For given syspath, returns name of assotiated hidraw device.
		Returns None if there is no such thing.
		"""
		node = self._dev_for_hci(syspath)
		if node is None:
			return None
		hidrawsubdir = os.path.join(node, "hidraw")
		for fname in os.listdir(hidrawsubdir):
			if fname.startswith("hidraw"):
				return fname
		return None
	
	
	@staticmethod
	def _find_bt_address(syspath):
		"""
		Recursivelly searchs for "input*" subdirectories until "uniq" file
		is found. Then, returns address from that file.
		"""
		uniq = os.path.join(syspath, "uniq")
		if os.path.exists(uniq):
			return open(uniq, "r").read().strip()
		for name in os.listdir(syspath):
			if name.startswith("input"):
				path = os.path.join(syspath, name)
				if os.path.isdir(path) and not os.path.islink(path):
					addr = DeviceMonitor._find_bt_address(path)
					if addr: return addr
		return None
	
	
	@staticmethod
	def get_usb_address(syspath):
		"""
		For given syspath, reads and returns (busnum, devnum) as ints.
		
		May throw all kinds of OSErrors or IOErrors
		"""
		busnum  = int(open(os.path.join(syspath, "busnum")).read().strip())
		devnum = int(open(os.path.join(syspath, "devnum")).read().strip())
		return busnum, devnum
	
	
	@staticmethod
	def get_subsystem(syspath):
		"""
		For given syspath, reads and returns subsystem as string.
		
		May throw OSError if directory is not readable.
		"""
		return os.readlink(os.path.join(syspath, "subsystem")).split("/")[-1]


class hci_conn_info(ctypes.Structure):
	_fields_ = [
		('handle', ctypes.c_uint16),
		('bdaddr', ctypes.c_uint8 * 6),
		('type', ctypes.c_uint8),
		('out', ctypes.c_uint8),
		('state', ctypes.c_uint16),
		('link_mode', ctypes.c_uint32),
	]


class hci_conn_list_req(ctypes.Structure):
	_fields_ = [
		('dev_id', ctypes.c_uint16),
		('conn_num', ctypes.c_uint16),
		('conn_info', hci_conn_info * 256),
	]


def create_device_monitor(daemon):
	m = Eudev().monitor(subclass=DeviceMonitor)
	m.daemon = daemon
	return m
