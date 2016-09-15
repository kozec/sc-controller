#!/usr/bin/env python2
from scc.lib import usb1
from scc.lib import IntEnum
from scc.constants import HPERIOD, LPERIOD, DURATION
from scc.constants import SCButtons, HapticPos
from scc.drivers.usb import USBDevice, register_hotplug_device
from scc.drivers import Controller
from collections import namedtuple
import struct, time, logging

VENDOR_ID = 0x28de
PRODUCT_ID = 0x1142 # [0x1102, 0x1142]
FIRST_ENDPOINT = 2 # [3, 2]
FIRST_CONTROLIDX = 1 #	[2, 1]
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


log = logging.getLogger("SCDriver")

def init(daemon):
	""" Registers hotplug callback for controller dongle """
	def cb(device, handle):
		return Dongle(device, handle, daemon)
	
	register_hotplug_device(cb, VENDOR_ID, PRODUCT_ID)


class Dongle(USBDevice):
	def __init__(self, device, handle, daemon):
		self.daemon = daemon
		USBDevice.__init__(self, device, handle)
		
		self.claim_by(klass=3, subclass=0, protocol=0)
		self.set_input_interrupt(FIRST_ENDPOINT, 64, self._on_input)
		self._controllers = {}
		self._lastusb = time.time()
	
	
	def _on_input(self, endpoint, data):
		tup = ControllerInput._make(struct.unpack(TUP_FORMAT, data))
		if tup.status == SCStatus.INPUT:
			print tup


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


class Controller(object):
	def __init__(self, ccidx, endpoint):
		pass
