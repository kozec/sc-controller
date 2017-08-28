#!/usr/bin/env python2
"""
SC Controller - Dualshock 3 Driver

Derived from HID driver as DS3 _amost_ is one.
"""

from scc.lib import IntEnum
from scc.drivers.usb import USBDevice, register_hotplug_device
from scc.drivers.hiddrv import HIDDrv, DEV_CLASS_HID
from collections import namedtuple
import struct, time, logging

VENDOR_ID = 0x054c
PRODUCT_ID = 0x0268
ENDPOINT = 0x81
INPUT_SIZE = 49
INPUT_FORMAT = [
	('x',	'ukn_01'),
	('I',	'buttons'),
	('x',	'ukn_02'),
	('B',	'lpad_x'),
	('B',	'lpad_y'),
	('B',	'rpad_x'),
	('B',	'rpad_y'),
	('8x',	'ukn_03'),
	('B',   'ltrig'),
	('B',   'rtrig'),
	('2x',  'ukn_98'),	# actually bumpers, but not used
	('27x', 'ukn_99'),	# Lot's of nonimportant stuff inlcluding gyros
	# PS3 gyros are ignored as they basically sucks hard and mapping them to
	# SCC profile would be next to impossible.
]
FORMATS, NAMES = zip(*INPUT_FORMAT)
TUP_FORMAT = '<' + ''.join(FORMATS)
DS3Input = namedtuple('DS3Input', ' '.join([ x for x in NAMES if not x.startswith('ukn_') ]))
DS3_NULL = DS3Input._make(struct.unpack('<' + ''.join(FORMATS), b'\x00' * 49))

log = logging.getLogger("DS3")

def init(daemon):
	""" Registers hotplug callback for ds3 device """
	def cb(device, handle):
		return DS3Drv(device, handle, daemon)
	
	register_hotplug_device(cb, VENDOR_ID, PRODUCT_ID)


class DS3Drv(HIDDrv):
	
	#def __init__(self, device, handle, daemon):
	#	self.daemon = daemon
	#	USBDevice.__init__(self, device, handle)
	#	self.claim_by(klass=DEV_CLASS_HID, subclass=0, protocol=0)
	#	self.set_input_interrupt(ENDPOINT, INPUT_SIZE, self._on_input)

	#def _on_input(self, endpoint, data):
	#	#tup = DS3Input._make(struct.unpack(TUP_FORMAT, data))
	#	#print tup
	pass
