#!/usr/bin/env python2


from scc.lib import usb1
from scc.lib import IntEnum
from scc.drivers.usb import USBDevice, register_hotplug_device
from scc.constants import SCButtons, HapticPos
from scc.controller import Controller
from collections import namedtuple
import struct, time, logging

VENDOR_ID = 0x28de
PRODUCT_ID = 0x1142
FIRST_ENDPOINT = 2
FIRST_CONTROLIDX = 1
INPUT_FORMAT = [
	('b',   'type'),
	('x',   'ukn_01'),
	('B',   'status'),
	('x',   'ukn_02'),
	('H',   'seq'),
	('x',   'ukn_03'),
	('I',   'buttons'),
	('B',   'ltrig'),
	('B',   'rtrig'),
	('x',   'ukn_04'),
	('x',   'ukn_05'),
	('x',   'ukn_06'),
	('h',   'lpad_x'),
	('h',   'lpad_y'),
	('h',   'rpad_x'),
	('h',   'rpad_y'),
	('10x', 'ukn_06'),
	('h',   'gpitch'),
	('h',   'groll'),
	('h',   'gyaw'),
	('h',   'q1'),
	('h',   'q2'),
	('h',   'q3'),
	('h',   'q4'),
	('16x', 'ukn_07')]
FORMATS, NAMES = zip(*INPUT_FORMAT)
ControllerInput = namedtuple('ControllerInput', ' '.join([ x for x in NAMES if not x.startswith('ukn_') ]))
SCI_NULL = ControllerInput._make(struct.unpack('<' + ''.join(FORMATS), b'\x00' * 64))
TUP_FORMAT = '<' + ''.join(FORMATS)


log = logging.getLogger("SCDongle")

def init(daemon):
	""" Registers hotplug callback for controller dongle """
	def cb(device, handle):
		return Dongle(device, handle, daemon)
	
	register_hotplug_device(cb, VENDOR_ID, PRODUCT_ID)


class Dongle(USBDevice):
	MAX_ENDPOINTS = 4
	
	def __init__(self, device, handle, daemon):
		self.daemon = daemon
		USBDevice.__init__(self, device, handle)
		
		self.claim_by(klass=3, subclass=0, protocol=0)
		self._controllers = {}
		for i in xrange(0, Dongle.MAX_ENDPOINTS):
			# Steam dongle apparently can do only 4 controllers at once
			self.set_input_interrupt(FIRST_ENDPOINT + i, 64, self._on_input)
	
	
	def close(self):
		# Called when dongle is removed
		for c in self._controllers.values():
			self.daemon.remove_controller(c)
		self._controllers = []
	
	
	def _add_controller(self, endpoint):
		"""
		Called when new controller is detected either by HOTPLUG message or
		by recieving first input event.
		"""
		ccidx = FIRST_CONTROLIDX + endpoint - FIRST_ENDPOINT
		c = SCController(self, ccidx, endpoint)
		c._configure()
		self._controllers[endpoint] = c
		self.daemon.add_controller(c)
	
	
	def _on_input(self, endpoint, data):
		tup = ControllerInput._make(struct.unpack(TUP_FORMAT, data))
		if tup.status == SCStatus.HOTPLUG:
			# Most of INPUT_FORMAT doesn't apply here
			if ord(data[4]) == 2:
				# Controller connected
				if endpoint not in self._controllers:
					self._add_controller(endpoint)
			else:
				# Controller disconnected
				if endpoint in self._controllers:
					self.daemon.remove_controller(self._controllers[endpoint])
					del self._controllers[endpoint]
		elif tup.status == SCStatus.INPUT:
			if endpoint not in self._controllers:
				self._add_controller(endpoint)
			self._controllers[endpoint].input(tup)


class SCStatus(IntEnum):
	IDLE = 0x04
	INPUT = 0x01
	HOTPLUG = 0x03


class SCPacketType(IntEnum):
	OFF = 0x9f
	AUDIO = 0xb6
	CONFIGURE = 0x87
	CALIBRATE_JOYSTICK = 0xbf
	CALIBRATE_TRACKPAD = 0xa7
	SET_AUDIO_INDICES = 0xc1
	FEEDBACK = 0x8f
	RESET = 0x95


class SCConfigType(IntEnum):
	LED = 0x2d
	TIMEOUT_N_GYROS = 0x32


class SCController(Controller):
	def __init__(self, driver, ccidx, endpoint):
		Controller.__init__(self)
		self._driver = driver
		self._endpoint = endpoint
		self._idle_timeout = 600
		self._enable_gyros = False
		self._led_level = 10
		self._old_state = SCI_NULL
		self._ccidx = ccidx
	
	
	def input(self, idata):
		old_state, self._old_state = self._old_state, idata
		self.mapper.input(self, time.time(), old_state, idata)
	
	
	def _send_control(self, data, timeout=0):
		""" Synchronoussly writes controll for controller """
		
		zeros = b'\x00' * (64 - len(data))
		self._driver.send_control(self._ccidx, data)
	
	
	def _configure(self, idle_timeout=None, enable_gyros=None, led_level=None):
		"""
		Sets and, if possible, sends configuration to controller.
		Only value that is provided is changed.
		'idle_timeout' is in seconds.
		'led_level' is precent (0-100)
		"""
		# ------
		"""
		packet format:
		 - uint8_t type - SCPacketType.CONFIGURE
		 - uint8_t size - 0x03 for led configuration, 0x15 for timeout & gyros
		 - uint8_t config_type - one of SCConfigType
		 - 61b data
		
		Format for data when configuring controller:
		 - uint16	timeout
		 - 13b		unknown1 - (0x18, 0x00, 0x00, 0x31, 0x02, 0x00, 0x08, 0x07, 0x00, 0x07, 0x07, 0x00, 0x30)
		 - uint8	enable gyro sensor - 0x14 enables, 0x00 disables
		 - 2b		unknown2 - (0x00, 0x2e)
		 - 43b		unused
		 
		Format for data when configuring led:
		 - uint8	led
		 - 60b		unused
		"""
		
		if idle_timeout is not None : self._idle_timeout = idle_timeout
		if enable_gyros is not None : self._enable_gyros = enable_gyros
		if led_level is not None: self._led_level = led_level
		
		unknown1 = b'\x18\x00\x001\x02\x00\x08\x07\x00\x07\x07\x000'
		unknown2 = b'\x00\x2e'
		timeout1 = self._idle_timeout & 0x00FF
		timeout2 = (self._idle_timeout & 0xFF00) >> 8
		led_lvl  = min(100, int(self._led_level)) & 0xFF
		
		# Timeout & Gyros
		self._send_control(struct.pack('>BBBBB13sB2s43x',
			SCPacketType.CONFIGURE,
			0x15, # size
			SCConfigType.TIMEOUT_N_GYROS,
			timeout1, timeout2,
			unknown1,
			0x14 if self._enable_gyros else 0,
			unknown2))
		
		# LED
		self._send_control(struct.pack('>BBBB59x',
			SCPacketType.CONFIGURE,
			0x03,
			SCConfigType.LED,
			led_lvl))
	
	
	def set_led_level(self, level):
		self._configure(led_level = level)
	
	
	def set_gyro_enabled(self, enabled):	
		self._configure(enable_gyros = enabled)
	
	
	def turnoff(self):
		log.debug("Turning off the controller...")
		
		# Mercilessly stolen from scraw library
		self._send_control(struct.pack('<BBBBBB',
				SCPacketType.OFF, 0x04, 0x6f, 0x66, 0x66, 0x21))
	
	
	def get_gyro_enabled(self):
		""" Returns True if gyroscope input is currently enabled """
		return self._enable_gyros
	
	
	def feedback(self, data):
		self._feedback(*data.data)
	
	
	def _feedback(self, position, amplitude=128, period=0, count=1):
		"""
		Add haptic feedback to be send on next usb tick

		@param int position	 haptic to use 1 for left 0 for right
		@param int amplitude	signal amplitude from 0 to 65535
		@param int period	   signal period from 0 to 65535
		@param int count		number of period to play
		"""
		self._send_control(struct.pack('<BBBHHH',
				SCPacketType.FEEDBACK, 0x07, position,
				amplitude, period, count))	
