#!/usr/bin/env python2
"""
SC Controller - Steam Controller Driver

Driver for Steam Controller over bluetooth (evdev)

Shares a lot of classes with sc_dongle.py
"""

from scc.lib.hidraw import HIDRaw
from scc.lib import IntEnum
from scc.drivers.evdevdrv import register_evdev_device
from scc.drivers.evdevdrv import HAVE_EVDEV, EvdevController
from scc.constants import ControllerFlags
from scc.tools import find_library
from sc_dongle import SCPacketType, SCPacketLength, SCConfigType
from sc_dongle import SCController
from math import pi as PI, sin, cos
import os, sys, time, struct, ctypes, logging

VENDOR_ID = 0x28de
PRODUCT_ID = 0x1106
PACKET_SIZE = 20

log = logging.getLogger("SCBT")


class SCByBtControllerInput(ctypes.Structure):
	_fields_ = [
		('buttons', ctypes.c_uint32),
		('ltrig', ctypes.c_uint8),
		('rtrig', ctypes.c_uint8),
		('stick_x', ctypes.c_int16),
		('stick_y', ctypes.c_int16),
		('lpad_x', ctypes.c_int16),
		('lpad_y', ctypes.c_int16),
		('rpad_x', ctypes.c_int16),
		('rpad_y', ctypes.c_int16),
		('gpitch', ctypes.c_int32),
		('groll', ctypes.c_int32),
		('gyaw', ctypes.c_int32),
		('q1', ctypes.c_int32),
		('q2', ctypes.c_int32),
		('q3', ctypes.c_int32),
		('q4', ctypes.c_int32),
	]

InputPtr = ctypes.POINTER(SCByBtControllerInput)


class Driver:
	""" Similar to USB driver, but with hidraw used for backend """
	# TODO: It should be possible to merge this, usb and hiddrv
	
	def __init__(self, daemon, config):
		self._known = {}
		self.config = config
		self.daemon = daemon
		self._lib = find_library('libsc_by_bt')
		read_input = self._lib.read_input
		read_input.restype = ctypes.c_int
		read_input.argtypes = [ ctypes.c_int, ctypes.c_size_t, InputPtr, InputPtr ]
	
	
	def new_device_callback(self, evdevdevices):
		# Evdev is used only to detect that new device is connected,
		# communication goes through hidraw
		for evdevdev in evdevdevices:
			for filename in os.listdir("/dev/"):
				if filename.startswith("hidraw") and filename not in self._known:
					try:
						dev = HIDRaw(open(os.path.join("/dev/", filename), "w+b"))
						i = dev.getInfo()
						if (i.bustype, i.vendor, i.product) == (5, VENDOR_ID, PRODUCT_ID):
							c = SCByBt(self, evdevdev, dev)
							c.configure()
							c.flush()
							self._known[filename] = c
							return c
					except (OSError, IOError):
						# Expected, user usually can't access most of those
						pass
		return None


class SCByBt(SCController):
	flags = 0 | ControllerFlags.SEPARATE_STICK
	
	def __init__(self, driver, evdevdev, hidrawdev):
		self._cmsg = []  # controll messages
		self._rmsg = []  # requests (excepts response)
		self._transfer_list = []
		self.driver = driver
		self.daemon = driver.daemon
		SCController.__init__(self, self, -1, -1)
		self._old_state = SCByBtControllerInput()
		self._state = SCByBtControllerInput()
		self._led_level = 30
		self._evdevdev_fn = evdevdev.fn if evdevdev else "unknown"
		self._device_name = hidrawdev.getName()
		self._hidrawdev = hidrawdev
		self._fileno = hidrawdev._device.fileno()
		poller = self.daemon.get_poller()
		if poller:
			poller.register(self._fileno, poller.POLLIN, self._input)
	
	
	def get_device_filename(self):
		# Method needed by evdev driver
		return self._evdevdev_fn
	
	
	def get_device_name(self):
		# Method needed by evdev driver
		# return self._device_name
		return "Steam Controller over Bluetooth"
	
	
	def get_type(self):
		return "scbt"
	
	
	def __repr__(self):
		return "<SCByBt %s>" % (self.get_id(),)
	
	
	def configure(self, idle_timeout=None, enable_gyros=None, led_level=None):
		"""
		Sets and, if possible, sends configuration to controller.
		See SCController.configure method in sc_dongle.py;
		
		This method is almost the same, with different set of hardcoded constants.
		"""
		# ------
		"""
		packet format:
		 - uint8_t type - SCPacketType.CONFIGURE
		 - uint8_t size - SCPacketLength.CONFIGURE_BT or SCPacketLength.LED
		 - uint8_t config_type - SCConfigType.CONFIGURE_BT or SCConfigType.LED
		 - (variable) data
		
		Format for data when configuring controller:
		 - 12B		unknown1 - (hex 0000310200080700070700300)
		 - uint8	enable gyro sensor - 0x14 enables, 0x00 disables
		 - 2b		unknown2 - (0x00, 0x2e)
		 
		Format for data when configuring led:
		 - uint8	led
		 - 60b		unused
		"""
		
		# idle_timeout is ignored
		if enable_gyros is not None : self._enable_gyros = enable_gyros
		if led_level is not None: self._led_level = led_level
		
		unknown1 = b'\x00\x00\x31\x02\x00\x08\x07\x00\x07\x07\x00\x30'
		unknown2 = b'\x00\x2e'
		
		# Timeout & Gyros
		self.overwrite_control(self._ccidx, struct.pack('>BBB12sB2s',
			SCPacketType.CONFIGURE,
			SCPacketLength.CONFIGURE_BT,
			SCConfigType.CONFIGURE_BT,
			unknown1,
			0x14 if self._enable_gyros else 0,
			unknown2))
		
		# LED
		self.overwrite_control(self._ccidx, struct.pack('>BBBB',
			SCPacketType.CONFIGURE,
			SCPacketLength.LED,
			SCConfigType.LED,
			self._led_level
		))
	
	
	def send_control(self, index, data):
		""" Schedules writing control to device """
		# For BT controller, index is ignored
		zeros = b'\x00' * (PACKET_SIZE - len(data) - 1)
		self._cmsg.insert(0, b'\xc0' + data + zeros)
	
	
	def overwrite_control(self, index, data):
		"""
		Similar to send_control, but this one checks and overwrites
		already scheduled controll for same device/index.
		"""
		# For BT controller, index is ignored
		for x in self._cmsg:
			# First byte is reserved, following 3 are for PacketType, size and ConfigType
			if x[0:4] == data[0:4]:
				self._cmsg.remove(x)
				break
		self.send_control(index, data)
	
	
	def make_request(self, index, callback, data, size=PACKET_SIZE):
		"""
		Schedules synchronous request that requires response.
		Request is done ASAP and provided callback is called with recieved data.
		"""
		# Still BT, index still ignored
		assert False
		self._rmsg.append(( data, callback ))
	
	
	def flush(self):
		""" Flushes all prepared control messages to the device """
		while len(self._cmsg):
			msg = self._cmsg.pop()
			self._hidrawdev.sendFeatureReport(msg)
		
		while len(self._rmsg):
			msg, callback = self._rmsg.pop()
			# TODO: This
			# callback(data)
	
	
	def input(self, idata):
		raise TypeError("This shouldn't be called, ever")
	
	
	def _input(self, *a):
		r = self.driver._lib.read_input(self._fileno, PACKET_SIZE,
				ctypes.byref(self._state), ctypes.byref(self._old_state))
		
		if r == 1:
			if self.mapper is not None:
				if self._input_rotation_l:
					lx, ly = self._state.lpad_x, self._state.lpad_y
					rx, ry = self._state.rpad_x, self._state.rpad_y
					s, c = sin(self._input_rotation_l), cos(self._input_rotation_l)
					self._state.lpad_x = int(lx * c - ly * s)
					self._state.lpad_y = int(lx * s + ly * c)
					s, c = sin(self._input_rotation_r), cos(self._input_rotation_r)
					self._state.rpad_x = int(rx * c - ry * s)
					self._state.rpad_y = int(rx * s + ry * c)
				
				self.mapper.input(self, self._old_state, self._state)
		elif r > 1:
			raise IOError("Read Failed")


def hidraw_test(filename):
	class FakeDaemon(object):

		def add_error(self, id, error):
			log.error(error)

		def remove_error(*a): pass

		def add_mainloop(*a): pass

		def get_active_ids(*a): return []

		def get_poller(self):
			return None
	
	class TestSC(SCByBt):
		def input(self, tup):
			print tup
	
	dev = HIDRaw(open(filename, "w+b"))
	driver = Driver(FakeDaemon(), {})
	c = TestSC(driver, None, dev)
	c.configure()
	c.flush()
	while True:
		data = dev._device.read(PACKET_SIZE)
		type, = struct.unpack("xxh16x", data)
		print "".join([ hex(ord(i)).strip("0x").zfill(2) for i in data ])


def init(daemon, config):
	""" Registers hotplug callback for controller dongle """

	if not (HAVE_EVDEV and config["drivers"].get("evdevdrv")):
		log.warning("Evdev driver is not enabled, Steam Controller over Bluetooth support cannot be enabled.")
		return False
	drv = Driver(daemon, config)
	register_evdev_device(drv.new_device_callback, 0x5, VENDOR_ID, PRODUCT_ID)
	return True


if __name__ == "__main__":
	""" Called when executed as script """
	from scc.tools import init_logging, set_logging_level
	init_logging()
	set_logging_level(True, True)
	sys.exit(hidraw_test(sys.argv[1]))
