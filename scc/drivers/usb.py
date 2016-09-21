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

import struct, time, select, traceback, atexit, logging
log = logging.getLogger("USB")

class SelectPoller(object):
	"""
	Dummy poller based on select, because it exists on all platforms.
	WARNING: this class is just for a trivial demonstration, and
	inherits select() limitations. The most important limitation is
	that regitering descriptors does not wake/affect a running poll.
	"""
	def __init__(self):
		self._fd_dict = {}
	
	
	def register(self, fd, events):
		self._fd_dict[fd] = events
	
	
	def unregister(self, fd):
		self._fd_dict.pop(fd)
	
	
	def poll(self, timeout=None):
		flag_list = (select.POLLIN, select.POLLOUT, select.POLLPRI)
		result = {}
		zp = zip(
			select.select(*([[
				fd for fd, events in self._fd_dict.iteritems() if events & flag ]
				for flag in flag_list] + [timeout])
			), flag_list, )
		for fd_list, happened_flag in zp:
			result[fd] = result.get(fd, 0) | happened_flag
		return result.items()


class USBDevice(object):
	""" Base class for all handled usb devices """
	def __init__(self, device, handle):
		self.device = device
		self.handle = handle
		self._claimed = []
		self._cmsg = []
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
	
	
	def make_request(self, index, data, len=64, timeout=0):
		"""
		Synchronously sends request and waits for response.
		Note that timeout may be doubled as it is used both for sending
		and reading data.
		
		Note that this may crash horribly if used after
		set_input_interrupt is called.
		"""
		self.handle.controlWrite(
			0x21,	# request_type
			0x09,	# request
			0x0300,	# value
			index, data,
			timeout = timeout
		)
		
		return self.handle.controlRead(
			0xA1,	# request_type
			0x01,	# request
			0x0300,	# value
			index, len,
			timeout = timeout
		)
	
	
	def flush(self):
		""" Flushes all prepared control messages to device """
		while len(self._cmsg):
			msg = self._cmsg.pop()
			self.handle.controlWrite(*msg)
	
	
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
		self._known_ids = {}
		self._devices = {}
		self._context = None	# Set by start method
		self._poller = None		# Set by start method
	
	
	def close_all(self):
		""" Closes all devices and unclaims all interfaces """
		log.debug("Releasing devices...")
		for d in self._devices.values():
			d.close()
	
	def __del__(self):
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
		self._poller = usb1.USBPoller(self._context, SelectPoller())
	
	
	def on_hotplug_event(self, context, device, event):
		if event == usb1.HOTPLUG_EVENT_DEVICE_LEFT:
			if device in self._devices:
				tp = device.getVendorID(), device.getProductID()
				log.debug("USB device removed: %x:%x", *tp)
				d = self._devices[device]
				del self._devices[device]
				d.close()
			return
		
		tp = device.getVendorID(), device.getProductID()
		if tp in self._known_ids:
			try:
				handle = device.open()
			except usb1.USBError:
				log.error("Failed to open USB device: %x:%x", *tp)
				return
			handled_device = self._known_ids[tp](device, handle)
			if handled_device:
				self._devices[device] = handled_device
				log.debug("USB device added: %x:%x", *tp)
			else:
				log.warning("Known USB device ignored: %x:%x", *tp)
				device.close()
	
	
	def register_hotplug_device(self, callback, vendor_id, product_id):
		self._known_ids[vendor_id, product_id] = callback
		log.debug("Registered hotplug USB driver for %x:%x", vendor_id, product_id)
	
	
	def mainloop(self):
		self._poller.poll()
		for d in self._devices.values():		# TODO: don't use .values() here
			d.flush()


# USBDriver should be instance-wide singleton
_usb = USBDriver()


def init(daemon):
	daemon.add_to_mainloop(_usb.mainloop)

def start(daemon):
	_usb.start()

def __del__():
	_usb.close_all()

atexit.register(__del__)


def register_hotplug_device(callback, vendor_id, product_id):
	_usb.register_hotplug_device(callback, vendor_id, product_id)
