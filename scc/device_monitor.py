#!/usr/bin/env python2
"""
SC-Controller - Device Monitor

Extends eudevmonitor with options to register callbacks and
manage plugging/releasing devices.
"""
from scc.lib.eudevmonitor import Eudev, Monitor
from scc.lib.eudevmonitor import get_vendor_product, get_subsystem


class DeviceMonitor(Monitor):
	
	def __init__(self, *a):
		Monitor.__init__(self, *a)
		self.daemon = None
		self.dev_added_cbs = {}
		self.dev_removed_cbs = {}
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
	
	
	def start(self):
		""" Registers poller and starts listening for events """
		poller = self.daemon.poller
		poller.register(self.fileno(), poller.POLLIN, self.on_data_ready)
		Monitor.start(self)
	
	
	def _on_new_syspath(self, subsystem, syspath):
		try:
			if subsystem == "input":
				vendor, product = None, None
			else:
				vendor, product = get_vendor_product(syspath)
		except IOError:
			# Cannot grab vendor & product, probably subdevice or bus itself
			return
		key = (subsystem, vendor, product)
		cb = self.dev_added_cbs.get(key)
		if cb:
			if cb(syspath, vendor, product):
				self.known_devs[syspath] = (vendor, product)
	
	
	def on_data_ready(self, *a):
		event = self.receive_device()
		if event:
			if event.action == "bind" and event.initialized:
				if event.syspath not in self.known_devs:
					self._on_new_syspath(event.subsystem, event.syspath)
			elif event.action == "add" and event.initialized and event.subsystem == "input":
				# those are not bound
				if event.syspath not in self.known_devs:
					self._on_new_syspath(event.subsystem, event.syspath)
			elif event.action in ("remove", "unbind") and event.syspath in self.known_devs:
				vendor, product = self.known_devs.pop(event.syspath)
				key = (event.subsystem, vendor, product)
				cb = self.dev_removed_cbs.get(key)
				if cb:
					cb(event.syspath, vendor, product)
	
	
	def rescan(self):
		""" Scans and calls callbacks for already connected devices """
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
				subsystem = get_subsystem(syspath)
				if subsystem in subsystem_to_vp_to_callback:
					self._on_new_syspath(subsystem, syspath)


def create_device_monitor(daemon):
	m = Eudev().monitor(subclass=DeviceMonitor)
	m.daemon = daemon
	return m
