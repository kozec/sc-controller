"""
Common code for all (one) USB-based drivers.

Driver that uses USB has to call
register_hotplug_device(callback, vendor_id, product_id) method to get notified
about connected USB devices.

Callback will be called with following arguments:
	callback(device, handle)
Callback has to return created USBDevice instance or None.
"""
from scc.lib import usb1

import struct, os, time, select, traceback, atexit, logging
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
			except Exception, e:
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
		""" Flushes all prepared control messages to device """
		while len(self._cmsg):
			msg = self._cmsg.pop()
			self.handle.controlWrite(*msg)
		
		while len(self._rmsg):
			msg, index, size, callback = self._rmsg.pop()
			if "SCC_DEBUG_USB_REQUESTS" in os.environ:
				# There are actually only very few messages wrote with controlWrite,
				# so this shouldn't have any performace penalty
				log.debug("controlWrite %s", msg)
			self.handle.controlWrite(*msg)
			data = self.handle.controlRead(
				0xA1,	# request_type
				0x01,	# request
				0x0300,	# value
				index, size
			)
			callback(data)
	
	
	def claim(self, number):
		"""
		Helper method; Remembers list of claimed interfaces and allows to
		unclaim them all at once using unclaim() method or automatically when
		device is closed.
		"""
		self.handle.claimInterface(number)
		self._claimed.append(number)
	
	
	def claim_by(self, klass, subclass, protocol):
		""" Claims all interfaces with specified parameters """
		for inter in self.device[0]:
			for setting in inter:
				number = setting.getNumber()
				if self.handle.kernelDriverActive(number):
					self.handle.detachKernelDriver(number)
				ksp = setting.getClass(), setting.getSubClass(), setting.getProtocol()
				if ksp == (klass, subclass, protocol):
					self.claim(number)
	
	
	def unclaim(self):
		""" Unclaims all claimed interfaces """
		for number in self._claimed:
			try:
				self.handle.releaseInterface(number)
			except usb1.USBErrorNoDevice, e:
				# Safe to ignore, happens when USB is removed
				pass
		self._claimed = []
	
	
	def close(self):
		""" Called after device is disconnected """
		self.unclaim()
		try:
			self.handle.close()
		except: pass
		try:
			self.device.close()
		except: pass


class USBDriver(object):
	def __init__(self):
		self._daemon = None
		self._known_ids = {}
		self._devices = {}
		self._retry_devices = []
		self._retry_devices_timer = 0
		self._context = None	# Set by start method
		self._changed = 0
	
	
	def close_all(self):
		""" Closes all devices and unclaims all interfaces """
		if len(self._devices):
			log.debug("Releasing devices...")
			for d in self._devices.values():
				d.close()
			self._devices = {}
	
	
	def __del__(self):
		self._context.setPollFDNotifiers(None, None)
		self.close_all()
	
	
	def start(self):
		self._context = usb1.USBContext()
		if not self._context.hasCapability(usb1.CAP_HAS_HOTPLUG):
			raise NoHotplugSupport('Hotplug support is missing. Please update your libusb version.')
		self._context.open()
		self._context.hotplugRegisterCallback(
			self.on_hotplug_event,
			events=usb1.HOTPLUG_EVENT_DEVICE_ARRIVED | usb1.HOTPLUG_EVENT_DEVICE_LEFT,
		)
		self._context.setPollFDNotifiers(self._register_fd, self._unregister_fd)
		for fd, events in self._context.getPollFDList():
			self._register_fd(fd, events)	
	
	
	def _fd_cb(self, *a):
		self._changed += 1
	
	
	def _register_fd(self, fd, events):
		self._daemon.get_poller().register(fd, events, self._fd_cb)
	
	
	def _unregister_fd(self, fd):
		self._daemon.get_poller().unregister(fd, events, self._fd_cb)	
	
	
	def on_hotplug_event(self, context, device, event):
		if event == usb1.HOTPLUG_EVENT_DEVICE_LEFT:
			if device in self._devices:
				tp = device.getVendorID(), device.getProductID()
				log.debug("USB device removed: %x:%x", *tp)
				d = self._devices[device]
				del self._devices[device]
				d.close()
			return
		
		self.handle_new_device(device)
	
	
	def handle_new_device(self, device):
		tp = device.getVendorID(), device.getProductID()
		if tp in self._known_ids:
			try:
				handle = device.open()
			except usb1.USBError, e:
				log.error("Failed to open USB device %x:%x : %s", tp[0], tp[1], e)
				if self._daemon:
					self._daemon.set_error("Failed to open USB device: %s" % (e,))
				return
			try:
				handled_device = self._known_ids[tp](device, handle)
			except usb1.USBErrorBusy, e:
				log.error("Failed to claim USB device %x:%x : %s", tp[0], tp[1], e)
				if self._daemon:
					self._daemon.set_error("Failed to claim USB device: %s" % (e,))
				self._retry_devices.append(tp)
				device.close()
				return
			if handled_device:
				self._devices[device] = handled_device
				log.debug("USB device added: %x:%x", *tp)
				self._daemon.set_error(None)
			else:
				log.warning("Known USB device ignored: %x:%x", *tp)
				device.close()
	
	
	def register_hotplug_device(self, callback, vendor_id, product_id):
		self._known_ids[vendor_id, product_id] = callback
		log.debug("Registered hotplug USB driver for %x:%x", vendor_id, product_id)
	
	
	def on_exit(self, daemon):
		self.close_all()
	
	
	def mainloop(self):
		if self._changed > 0:
			self._context.handleEventsTimeout()
			self._changed = 0
		
		for d in self._devices.values():		# TODO: don't use .values() here
			d.flush()
		if len(self._retry_devices):
			if time.time() > self._retry_devices_timer:
				self._retry_devices_timer = time.time() + 5.0
				lst, self._retry_devices = self._retry_devices, []
				for vendor, product in lst:
					try:
						device = self._context.getByVendorIDAndProductID(vendor, product)
					except:
						self._retry_devices.append(( vendor, product ))
						continue
					self.handle_new_device(device)


# USBDriver should be process-wide singleton
_usb = USBDriver()

def init(daemon):
	_usb._daemon = daemon
	daemon.on_daemon_exit(_usb.on_exit)
	daemon.add_mainloop(_usb.mainloop)

def start(daemon):
	_usb.start()

def __del__():
	_usb.close_all()

atexit.register(__del__)


def register_hotplug_device(callback, vendor_id, product_id):
	_usb.register_hotplug_device(callback, vendor_id, product_id)
