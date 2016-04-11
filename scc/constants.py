#!/usr/bin/env python2
from collections import namedtuple
from enum import IntEnum
import struct

VENDOR_ID = 0x28de
PRODUCT_ID = [0x1102, 0x1142]
ENDPOINT = [3, 2]
CONTROLIDX = [2, 1]

HPERIOD  = 0.02
LPERIOD  = 0.5
DURATION = 1.0

CONTROLER_FORMAT = [
	('x',   'ukn_00'),
	('x',   'ukn_01'),
	('H',   'status'),
	('H',   'seq'),
	('x',   'ukn_02'),
	('I',   'buttons'),
	('B',   'ltrig'),
	('B',   'rtrig'),
	('x',   'ukn_03'),
	('x',   'ukn_04'),
	('x',   'ukn_05'),
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
	('16x', 'ukn_07'),
]

FORMATS, NAMES = zip(*CONTROLER_FORMAT)
CI_NAMES = [ x for x in NAMES if not x.startswith('ukn_') ]

ControllerInput = namedtuple('ControllerInput', ' '.join(CI_NAMES))

SCI_NULL = ControllerInput._make(struct.unpack('<' + ''.join(FORMATS), b'\x00' * 64))

class SCStatus(IntEnum):
	IDLE  = 2820
	INPUT = 15361
	EXIT  = 259

class SCButtons(IntEnum):
	RPADTOUCH = 0b00010000000000000000000000000000
	LPADTOUCH = 0b00001000000000000000000000000000
	RPAD	  = 0b00000100000000000000000000000000
	LPAD	  = 0b00000010000000000000000000000000 # Same for stick but without LPadTouch
	RGRIP	 = 0b00000001000000000000000000000000
	LGRIP	 = 0b00000000100000000000000000000000
	START	 = 0b00000000010000000000000000000000
	C		 = 0b00000000001000000000000000000000
	BACK	  = 0b00000000000100000000000000000000
	A		 = 0b00000000000000001000000000000000
	X		 = 0b00000000000000000100000000000000
	B		 = 0b00000000000000000010000000000000
	Y		 = 0b00000000000000000001000000000000
	LB		= 0b00000000000000000000100000000000
	RB		= 0b00000000000000000000010000000000
	LT		= 0b00000000000000000000001000000000
	RT		= 0b00000000000000000000000100000000

class HapticPos(IntEnum):
	"""Specify witch pad or trig is used"""
	RIGHT = 0
	LEFT = 1
