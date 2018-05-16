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
from scc.constants import SCButtons
from sc_dongle import SCStatus, SCPacketType, SCPacketLength, SCConfigType
from sc_dongle import SCController, ControllerInput, SCI_NULL, TUP_FORMAT
import os, sys, time, struct, logging

VENDOR_ID = 0x28de
PRODUCT_ID = 0x1106
PACKET_SIZE = 20

log = logging.getLogger("SCBT")


class BtInPacketType(IntEnum):
	BUTTON = 0x14
	TRIGGERS = 0x24
	AXIS = 0x84


BT_BUTTONS_BITS = tuple(xrange(22))
BT_BUTTONS = (
	# Bit to SCButton
	SCButtons.RT,			# 00
	SCButtons.LT,			# 01
	SCButtons.LB,			# 02
	SCButtons.RB,			# 03
	SCButtons.Y,			# 04
	SCButtons.B,			# 05
	SCButtons.X,			# 06
	SCButtons.A,			# 07
	0, 						# 08 - dpad, ignored
	0, 						# 09 - dpad, ignored
	0, 						# 10 - dpad, ignored
	0, 						# 11 - dpad, ignored
	SCButtons.BACK,			# 12
	SCButtons.C,			# 13
	SCButtons.START,		# 14
	SCButtons.LGRIP,		# 15
	SCButtons.RGRIP,		# 16
	SCButtons.LPAD,			# 17
	SCButtons.RPAD,			# 18
	SCButtons.LPADTOUCH,	# 19
	SCButtons.RPADTOUCH,	# 20
	0,						# 21 - nothing
	SCButtons.STICKPRESS,	# 22
)


class Driver:
	""" Similar to USB driver, but with hidraw used for backend """
	# TODO: It should be possible to merge this, usb and hiddrv
	
	def __init__(self, daemon, config):
		self._known = {}
		self.config = config
		self.daemon = daemon
	
	
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
							c = SCByBt(self.daemon, evdevdev, dev)
							c.configure()
							c.flush()
							self._known[filename] = c
							return c
					except (OSError, IOError):
						# Expected, user usually can't access most of those
						pass
		return None


class SCByBt(SCController):
	
	def __init__(self, daemon, evdevdev, hidrawdev):
		self._cmsg = []  # controll messages
		self._rmsg = []  # requests (excepts response)
		self._transfer_list = []
		self.daemon = daemon
		SCController.__init__(self, self, -1, -1)
		self._led_level = 30
		self._evdevdev_fn = evdevdev.fn if evdevdev else "unknown"
		self._device_name = hidrawdev.getName()
		self.hidrawdev = hidrawdev
		daemon.add_mainloop(self._timer)
	
	
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
		self._driver.overwrite_control(self._ccidx, struct.pack('>BBB12sB2s',
			SCPacketType.CONFIGURE,
			SCPacketLength.CONFIGURE_BT,
			SCConfigType.CONFIGURE_BT,
			unknown1,
			0x14 if self._enable_gyros else 0,
			unknown2))
		
		# LED
		self._driver.overwrite_control(self._ccidx, struct.pack('>BBBB',
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
			self.hidrawdev.sendFeatureReport(msg)
		
		while len(self._rmsg):
			msg, callback = self._rmsg.pop()
			# TODO: This
			# callback(data)
	
	
	def _on_input(self, data):
		packet_type = ord(data[2])
		if packet_type == BtInPacketType.BUTTON:
			bt_buttons, = struct.unpack("4xI12x", data)
			sc_buttons = 0
			for bit in BT_BUTTONS_BITS:
				if (bt_buttons & 1) != 0:
					sc_buttons |= BT_BUTTONS[bit]
				bt_buttons >>= 1
			tup = self._old_state._replace(buttons=sc_buttons)
			self.input(tup)
	
	
	def _timer(self):
		data = self.hidrawdev.read(PACKET_SIZE)
		self._on_input(data)


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
	print dev.getInfo()
	c = TestSC(FakeDaemon(), None, dev)
	c.configure()
	c.flush()
	while True:
		c._timer()


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
