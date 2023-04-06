"""
Common code for all (one) USB-based drivers.

Driver that uses USB has to call
register_hotplug_device(callback, vendor_id, product_id, on_failure=None)
method to get notified about connected USB devices.

Callback will be called with following arguments:
	callback(device, handle)
Callback has to return created USBDevice instance or None.
"""
from scc.lib import usb1

import time, traceback, logging
log = logging.getLogger("USB")

class USBDevice(object):
	""" Base class for all handled usb devices """
	def __init__(self, device, handle):
		self.device = device
		self.handle = handle
		self._claimed = []
		self._cmsg = []		# controll messages
		self._rmsg = []		# requests (excepts response)
		self._transfer_list = []
	
	
	def set_input_interrupt(self, endpoint, size, callback):
		"""
		Helper method for setting up input transfer.
		
		callback(endpoint, data) is called repeadedly with every packed recieved.
		"""
		def callback_wrapper(transfer):
			if (transfer.getStatus() != usb1.TRANSFER_COMPLETED or
				transfer.getActualLength() != size):
				return
			
			data = transfer.getBuffer()
			try:
				callback(endpoint, data)
			except Exception as e:
				log.error("Failed to handle recieved data")
				log.error(e)
				log.error(traceback.format_exc())
			finally:
				transfer.submit()
		
		transfer = self.handle.getTransfer()
		transfer.setInterrupt(
			usb1.ENDPOINT_IN | endpoint,
			size,
			callback=callback_wrapper,
		)
		transfer.submit()
		self._transfer_list.append(transfer)
	
	
	def send_control(self, index, data):
		""" Schedules writing control to device """
		zeros = b'\x00' * (64 - len(data))
		
		self._cmsg.insert(0, (
			0x21,	# request_type
			0x09,	# request
			0x0300,	# value
			index,
			data + zeros,
			0		# Timeout
		))
	
	
	def overwrite_control(self, index, data):
		"""
		Similar to send_control, but this one checks and overwrites
		already scheduled controll for same device/index.
		"""
		for x in self._cmsg:
			x_index, x_data, x_timeout = x[-3:]
			# First 3 bytes are for PacketType, size and ConfigType
			if x_index == index and x_data[0:3] == data[0:3]:
				self._cmsg.remove(x)
				break
		self.send_control(index, data)
	
	
	def make_request(self, index, callback, data, size=64):
		"""
		Schedules synchronous request that requires response.
		Request is done ASAP and provided callback is called with recieved data.
		"""
		self._rmsg.append((
			(
				0x21,	# request_type
				0x09,	# request
				0x0300,	# value
				index, data
			), index, size, callback
		))
	
	
	def flush(self):
		""" Flushes all prepared control messages to the device """
		while len(self._cmsg):
			msg = self._cmsg.pop()
			self.handle.controlWrite(*msg)
		
		while len(self._rmsg):
			msg, index, size, callback = self._rmsg.pop()
			self.handle.controlWrite(*msg)
			data = self.handle.controlRead(
				0xA1,	# request_type
				0x01,	# request
				0x0300,	# value
				index, size
			)
			callback(data)
	
	
	def force_restart(self):
		"""
		Restarts device, closes handle and tries to re-grab it again.
		Don't use unless absolutelly necessary.
		"""
		tp = self.device.getVendorID(), self.device.getProductID()
		self.close()
		_usb._retry_devices.append(tp)
	
	
	def claim(self, number):
		"""
		Helper method; Remembers list of claimed interfaces and allows to
		unclaim them all at once using unclaim() method or automatically when
		device is closed.
		"""
		self.handle.claimInterface(number)
		self._claimed.append(number)
	
	
	def claim_by(self, klass, subclass, protocol):
		"""
		Claims all interfaces with specified parameters.
		Returns number of claimed interfaces
		"""
		rv = 0
		for inter in self.device[0]:
			for setting in inter:
				number = setting.getNumber()
				if self.handle.kernelDriverActive(number):
					self.handle.detachKernelDriver(number)
				ksp = setting.getClass(), setting.getSubClass(), setting.getProtocol()
				if ksp == (klass, subclass, protocol):
					self.claim(number)
					rv += 1
		return rv
	
	
	def unclaim(self):
		""" Unclaims all claimed interfaces """
		for number in self._claimed:
			try:
				self.handle.releaseInterface(number)
				self.handle.attachKernelDriver(number)
			except usb1.USBErrorNoDevice:
				# Safe to ignore, happens when USB is removed
				pass
		self._claimed = []
	
	
	def close(self):
		""" Called after device is disconnected """
		try:
			self.unclaim()
		except: pass
		try:
			self.handle.resetDevice()
			self.handle.close()
		except: pass


class USBDriver(object):
	def __init__(self):
		self.daemon = None
		self._known_ids = {}
		self._fail_cbs = {}
		self._devices = {}
		self._syspaths = {}
		self._started = False
		self._retry_devices = []
		self._retry_devices_timer = 0
		self._ctx = None	# Set by start method
		self._changed = 0
	
	
	def set_daemon(self, daemon):
		self.daemon = daemon
	
	
	def on_exit(self, *a):
		""" Closes all devices and unclaims all interfaces """
		if len(self._devices):
			log.debug("Releasing devices...")
			to_release, self._devices, self._syspaths = list(self._devices.values()), {}, {}
			for d in to_release:
				d.close()
	
	
	def start(self):
		self._ctx = usb1.USBContext()
		
		def fd_cb(*a):
			self._changed += 1
		
		def register_fd(fd, events, *a):
			self.daemon.get_poller().register(fd, events, fd_cb)
		
		def unregister_fd(fd, *a):
			self.daemon.get_poller().unregister(fd)
		
		self._ctx.setPollFDNotifiers(register_fd, unregister_fd)
		for fd, events in self._ctx.getPollFDList():
			register_fd(fd, events)	
		self._started = True
	
	
	def handle_new_device(self, syspath, vendor, product):
		tp = vendor, product
		handle = None
		if tp not in self._known_ids:
			return
		bus, dev = self.daemon.get_device_monitor().get_usb_address(syspath)
		for device in self._ctx.getDeviceIterator():
			if (bus, dev) == (device.getBusNumber(), device.getDeviceAddress()):
				try:
					handle = device.open()
					break
				except usb1.USBError as e:
					log.error("Failed to open USB device %.4x:%.4x : %s", tp[0], tp[1], e)
					if tp in self._fail_cbs:
						self._fail_cbs[tp](syspath, *tp)
						return
					if self.daemon:
						self.daemon.add_error(
							"usb:%s:%s" % (tp[0], tp[1]),
							"Failed to open USB device: %s" % (e,)
						)
					return
		else:
			return
		
		callback = self._known_ids[tp]
		handled_device = None
		try:
			handled_device = callback(device, handle)
		except usb1.USBErrorBusy as e:
			log.error("Failed to claim USB device %.4x:%.4x : %s", tp[0], tp[1], e)
			if tp in self._fail_cbs:
				device.close()
				self._fail_cbs[tp](*tp)
				return False
			else:
				if self.daemon:
					self.daemon.add_error(
						"usb:%s:%s" % (tp[0], tp[1]),
						"Failed to claim USB device: %s" % (e,)
					)
				self._retry_devices.append((syspath, tp))
				device.close()
				return True
		if handled_device:
			self._devices[device] = handled_device
			self._syspaths[syspath] = device
			log.debug("USB device added: %.4x:%.4x", *tp)
			self.daemon.remove_error("usb:%s:%s" % (tp[0], tp[1]))
			return True
		else:
			log.warning("Known USB device ignored: %.4x:%.4x", *tp)
			device.close()
			return False
	
	
	def handle_removed_device(self, syspath, vendor, product):
		if syspath in self._syspaths:
			device = self._syspaths[syspath]
			handled_device = self._devices[device]
			del self._syspaths[syspath]
			del self._devices[device]
			handled_device.close()
			try:
				device.close()
			except usb1.USBErrorNoDevice:
				# Safe to ignore, happens when device is physiucally removed
				pass
	
	
	def register_hotplug_device(self, callback, vendor_id, product_id, on_failure):
		self._known_ids[vendor_id, product_id] = callback
		if on_failure:
			self._fail_cbs[vendor_id, product_id] = on_failure
		monitor = self.daemon.get_device_monitor()
		monitor.add_callback("usb", vendor_id, product_id,
				self.handle_new_device, self.handle_removed_device)
		log.debug("Registered USB driver for %.4x:%.4x", vendor_id, product_id)
	
	
	def unregister_hotplug_device(self, callback, vendor_id, product_id):
		if self._known_ids.get((vendor_id, product_id)) == callback:
			del self._known_ids[vendor_id, product_id]
			if (vendor_id, product_id) in self._fail_cbs:
				del self._fail_cbs[vendor_id, product_id]
			log.debug("Unregistred USB driver for %.4x:%.4x", vendor_id, product_id)
	
	
	def mainloop(self):
		if self._changed > 0:
			self._ctx.handleEventsTimeout()
			self._changed = 0
		
		for d in list(self._devices.values()):		# TODO: don't use .values() here
			try:
				d.flush()
			except usb1.USBErrorPipe:
				log.error("USB device %s disconnected durring flush", d)
				d.close()
				break
		if len(self._retry_devices):
			if time.time() > self._retry_devices_timer:
				self._retry_devices_timer = time.time() + 5.0
				lst, self._retry_devices = self._retry_devices, []
				for syspath, (vendor, product) in lst:
					self.handle_new_device(syspath, vendor, product)


# USBDriver should be process-wide singleton
_usb = USBDriver()

def init(daemon, config):
	_usb.set_daemon(daemon)
	daemon.add_on_exit(_usb.on_exit)
	daemon.add_mainloop(_usb.mainloop)
	return True

def start(daemon):
	_usb.start()


def register_hotplug_device(callback, vendor_id, product_id, on_failure=None):
	_usb.register_hotplug_device(callback, vendor_id, product_id, on_failure)


def unregister_hotplug_device(callback, vendor_id, product_id):
	_usb.unregister_hotplug_device(callback, vendor_id, product_id)
