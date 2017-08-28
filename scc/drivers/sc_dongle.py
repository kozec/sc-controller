#!/usr/bin/env python2
"""
SC Controller - Steam Controller Wireless Receiver (aka Dongle) Driver

Called and used when Dongle is detected on USB bus.
Handles one or multiple controllers connected to dongle.
"""

from scc.lib import usb1
from scc.lib import IntEnum
from scc.drivers.usb import USBDevice, register_hotplug_device
from scc.constants import SCButtons, HapticPos, ControllerFlags
from scc.controller import Controller
from scc.config import Config
from collections import namedtuple
from math import pi as PI, sin, cos
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
TUP_FORMAT = '<' + ''.join(FORMATS)
ControllerInput = namedtuple('ControllerInput', ' '.join([ x for x in NAMES if not x.startswith('ukn_') ]))
SCI_NULL = ControllerInput._make(struct.unpack('<' + ''.join(FORMATS), b'\x00' * 64))


log = logging.getLogger("SCDongle")

def init(daemon):
	""" Registers hotplug callback for controller dongle """
	def cb(device, handle):
		return Dongle(device, handle, daemon)
	
	register_hotplug_device(cb, VENDOR_ID, PRODUCT_ID)


class Dongle(USBDevice):
	MAX_ENDPOINTS = 4
	_available_serials = set()		# used only is ignore_serials option is enabled
	
	def __init__(self, device, handle, daemon):
		self.daemon = daemon
		USBDevice.__init__(self, device, handle)
		
		self.claim_by(klass=3, subclass=0, protocol=0)
		self._controllers = {}
		self._no_serial = []
		for i in xrange(0, Dongle.MAX_ENDPOINTS):
			# Steam dongle apparently can do only 4 controllers at once
			self.set_input_interrupt(FIRST_ENDPOINT + i, 64, self._on_input)
	
	
	def close(self):
		# Called when dongle is removed
		for c in self._controllers.values():
			self.daemon.remove_controller(c)
		self._controllers = {}
		USBDevice.close(self)
	
	
	def _add_controller(self, endpoint):
		"""
		Called when new controller is detected either by HOTPLUG message or
		by recieving first input event.
		"""
		ccidx = FIRST_CONTROLIDX + endpoint - FIRST_ENDPOINT
		c = SCController(self, ccidx, endpoint)
		c.configure()
		c.read_serial()
		self._controllers[endpoint] = c
	
	
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
					self._controllers[endpoint].disconnected()
					del self._controllers[endpoint]
		elif tup.status == SCStatus.INPUT:
			if endpoint not in self._controllers:
				self._add_controller(endpoint)
			elif len(self._no_serial):
				for x in self._no_serial:
					x.read_serial()
				self._no_serial = []
			else:
				self._controllers[endpoint].input(tup)


class SCStatus(IntEnum):
	IDLE = 0x04
	INPUT = 0x01
	HOTPLUG = 0x03


class SCPacketType(IntEnum):
	OFF = 0x9f
	AUDIO = 0xb6
	CONFIGURE = 0x87
	LED = 0x87
	CALIBRATE_JOYSTICK = 0xbf
	CALIBRATE_TRACKPAD = 0xa7
	SET_AUDIO_INDICES = 0xc1
	FEEDBACK = 0x8f
	RESET = 0x95
	GET_SERIAL = 0xAE


class SCPacketLength(IntEnum):
	LED = 0x03
	OFF = 0x04
	FEEDBACK = 0x07
	CONFIGURE = 0x15
	GET_SERIAL = 0x15


class SCConfigType(IntEnum):
	LED = 0x2d
	CONFIGURE = 0x32


class SCController(Controller):
	def __init__(self, driver, ccidx, endpoint):
		Controller.__init__(self)
		self._driver = driver
		self._endpoint = endpoint
		self._idle_timeout = 600
		self._enable_gyros = False
		self._input_rotation_l = 0
		self._input_rotation_r = 0
		self._led_level = 10
		self._serial = "0000000000"
		self._old_state = SCI_NULL
		self._ccidx = ccidx
	
	
	def get_type(self):
		return "sc"
	
	
	def __repr__(self):
		return "<SCWireless %s>" % (self.get_id(),)
	
	
	def input(self, idata):
		old_state, self._old_state = self._old_state, idata
		if self.mapper:
			if self._input_rotation_l:
				lx, ly = idata.lpad_x, idata.lpad_y
				rx, ry = idata.rpad_x, idata.rpad_y
				if idata.buttons & SCButtons.LPADTOUCH:
					s, c = sin(self._input_rotation_l), cos(self._input_rotation_l)
					lx = int(idata.lpad_x * c - idata.lpad_y * s)
					ly = int(idata.lpad_x * s + idata.lpad_y * c)
				s, c = sin(self._input_rotation_r), cos(self._input_rotation_r)
				rx = int(idata.rpad_x * c - idata.rpad_y * s)
				ry = int(idata.rpad_x * s + idata.rpad_y * c)
				
				# TODO: This is awfull :(
				idata = ControllerInput(
						idata.type, idata.status, idata.seq, idata.buttons,
						idata.ltrig, idata.rtrig,
						lx, ly, rx, ry,
						idata.gpitch, idata.groll, idata.gyaw,
						idata.q1, idata.q2, idata.q3, idata.q4
				)
			
			self.mapper.input(self, old_state, idata)
	
	
	def read_serial(self):
		""" Requests and reads serial number from controller """
		if Config()["ignore_serials"]:
			# Special exception for cases when controller drops instead of
			# sending serial number. See issue #103
			self.generate_serial()
			self.on_serial_got()
			return
		
		def cb(rawserial):
			size, serial = struct.unpack(">xBx12s49x", rawserial)
			if size > 1:
				serial = serial.strip(" \x00")
				self._serial = serial
				self.on_serial_got()
			else:
				self._driver._no_serial.append(self)
		
		self._driver.make_request(
			self._ccidx, cb,
			struct.pack('>BBB61x',
				SCPacketType.GET_SERIAL, SCPacketLength.GET_SERIAL, 0x01))
	
	
	def generate_serial(self):
		""" Called only if ignore_serials is enabled """
		if len(self._driver._available_serials) > 0:
			self._serial = self._driver._available_serials.pop()
		else:
			self._serial = self.get_id()
		log.debug("Not requesting serial number for SC %s", self._serial)
	
	
	def on_serial_got(self):
		log.debug("Got wireless SC with serial %s", self._serial)
		self.set_id(str(self._serial), True)
		self._driver.daemon.add_controller(self)
	
	
	def apply_config(self, config):
		self.set_led_level(float(config['led_level']))
		self._input_rotation_l = float(config['input_rotation_l']) * PI / -180.0
		self._input_rotation_r = float(config['input_rotation_r']) * PI / -180.0
	
	
	def disconnected(self):
		# If ignore_serials config option is enabled, fake serial used by this
		# controller is stored away and reused when next controller is connected
		if Config()["ignore_serials"]:
			self._driver._available_serials.add(self._serial)
	
	
	def configure(self, idle_timeout=None, enable_gyros=None, led_level=None):
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
		 - uint8_t size - SCPacketLength.CONFIGURE or SCPacketLength.LED
		 - uint8_t config_type - SCConfigType.CONFIGURE or SCConfigType.LED
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
		
		# Timeout & Gyros
		self._driver.overwrite_control(self._ccidx, struct.pack('>BBBBB13sB2s43x',
			SCPacketType.CONFIGURE,
			SCPacketLength.CONFIGURE,
			SCConfigType.CONFIGURE,
			timeout1, timeout2,
			unknown1,
			0x14 if self._enable_gyros else 0,
			unknown2))
		
		# LED
		self._driver.overwrite_control(self._ccidx, struct.pack('>BBBB59x',
			SCPacketType.CONFIGURE,
			0x03,
			SCConfigType.LED,
			self._led_level
		))
	
	
	def set_led_level(self, level):
		level = min(100, int(level)) & 0xFF
		if self._led_level != level:
			self._led_level = level
			self._driver.overwrite_control(self._ccidx, struct.pack('>BBBB59x',
				SCPacketType.CONFIGURE,
				0x03,
				SCConfigType.LED,
				self._led_level
			))
	
	
	def set_gyro_enabled(self, enabled):	
		self.configure(enable_gyros = enabled)
	
	
	def turnoff(self):
		log.debug("Turning off the controller...")
		
		# Mercilessly stolen from scraw library
		self._driver.send_control(self._ccidx, struct.pack('<BBBBBB',
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
		self._driver.send_control(self._ccidx, struct.pack('<BBBHHH',
				SCPacketType.FEEDBACK, 0x07, position,
				amplitude, period, count))	
