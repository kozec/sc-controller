"""
Windows code for USB-based drivers.

Attempts to emulate interface of usb.py, but uses
HID identifiers for registering
"""
import platform
if platform.system() == "Windows":
	import scc.lib.pywinusb.hid as hid
	from scc.lib.pywinusb.hid.helpers import HIDError
	
	import struct, os, time, select, traceback, atexit, logging
	log = logging.getLogger("WINUSB")
	
	
	class USBDevice(object):
		""" Base class for all handled usb devices """
		def __init__(self, device, handle):
			self.device = device
			self.handle = handle
			self._interrupt = None
		
		
		def _raw_data_handler(self, data):
			if self._interrupt:
				data = "".join([ chr(x) for x in data[1:] ])
				self._interrupt(0, data)
		
		
		def set_input_interrupt(self, endpoint, size, callback):
			"""
			Helper method for setting up input transfer.
			
			callback(endpoint, data) is called repeadedly with every packed recieved.
			
			# Funny part is there is no endpoint support on Windows.
			God knows what this will break.
			"""
			if size != 64:
				raise ValueError("Only 64B pacets supported")
			if self._interrupt:
				raise RuntimeError("input_interrupt already registerde")
			self._interrupt = callback
		
		
		def send_control(self, index, data):
			""" Schedules writing control to device """
			pass
		
		
		def overwrite_control(self, index, data):
			"""
			Similar to send_control, but this one checks and overwrites
			already scheduled controll for same device/index.
			"""
			pass
		
		
		def make_request(self, index, callback, data, size=64):
			"""
			Schedules synchronous request that requires response.
			Request is done ASAP and provided callback is called with recieved data.
			"""
			pass
		
		
		def flush(self):
			""" Flushes all prepared control messages to device """
			pass
		
		
		def claim(self, number):
			"""
			Helper method; Remembers list of claimed interfaces and allows to
			unclaim them all at once using unclaim() method or automatically when
			device is closed.
			"""
			pass
		
		
		def claim_by(self, klass, subclass, protocol):
			""" Claims all interfaces with specified parameters """
			pass
		
		
		def unclaim(self):
			""" Unclaims all claimed interfaces """
			pass
		
		
		def close(self):
			""" Called after device is disconnected """
			pass
	
	
		def get_bus_number(self):
			return self.device.device_path.split("&")[2]
		
		
		def get_port_number(self):
			return self.device.device_path.split("&")[3]
	
	
	class USBDriver(object):
		def __init__(self):
			self._daemon = None
			self._known_ids = {}
			self._devices = {}
		
		
		def _enumerate_devices(self):
			"""
			Called on few ocassions to check if there is new known
			device available
			"""
			all_devices = hid.find_all_hid_devices()
			if all_devices:
				for device in all_devices:
					self.handle_new_device(device)
		
		
		def close_all(self):
			""" Closes all devices and unclaims all interfaces """
			if len(self._devices):
				log.debug("Releasing devices...")
				for d in self._devices.values():
					d.close()
				self._devices = {}
		
		
		def handle_new_device(self, device):
			tp = device.vendor_id, device.product_id
			if tp in self._known_ids:
				try:
					handle = device.open()
				except HIDError, e:
					log.error("Failed to open USB device %x:%x : %s", tp[0], tp[1], e)
					if self._daemon:
						self._daemon.add_error(
							"usb:%s:%s" % (tp[0], tp[1]),
							"Failed to open USB device: %s" % (e,)
						)
					return
				try:
					handled_device = self._known_ids[tp](device, handle)
				except HIDError, e:
					log.error("Failed to claim USB device %x:%x : %s", tp[0], tp[1], e)
					if self._daemon:
						self._daemon.add_error(
							"usb:%s:%s" % (tp[0], tp[1]),
							"Failed to claim USB device: %s" % (e,)
						)
					device.close()
					return
				if handled_device:
					device.set_raw_data_handler(handled_device._raw_data_handler)
					self._devices[device] = handled_device
					log.debug("USB device added: %x:%x", *tp)
					self._daemon.remove_error("usb:%s:%s" % (tp[0], tp[1]))
				else:
					log.warning("Known USB device ignored: %x:%x", *tp)
					device.close()
		
		
		def register_hotplug_device(self, callback, vendor_id, product_id):
			self._known_ids[vendor_id, product_id] = callback
			log.debug("Registered hotplug USB driver for %x:%x", vendor_id, product_id)
			self._enumerate_devices()
	
	# USBDriver should be process-wide singleton
	_usb = USBDriver()
	
	def init(daemon):
		_usb._daemon = daemon
		# daemon.on_daemon_exit(_usb.on_exit)
		# daemon.add_mainloop(_usb.mainloop)
	
	
	def start(daemon):
		_usb._enumerate_devices()
	
	
	def __del__():
		_usb.close_all()
	
	atexit.register(__del__)
	
	
	def register_hotplug_device(callback, vendor_id, product_id):
		_usb.register_hotplug_device(callback, vendor_id, product_id)
