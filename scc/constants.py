#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2015 Stany MARCEL <stanypub@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from collections import namedtuple
from scc.lib import IntEnum
import struct

VENDOR_ID = 0x28de
PRODUCT_ID = [0x1102, 0x1142]
ENDPOINT = [3, 2]
CONTROLIDX = [2, 1]

HPERIOD  = 0.02
LPERIOD  = 0.5
DURATION = 1.0

CONTROLER_FORMAT = [
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
	('16x', 'ukn_07'),
]

FE_STICK	= 1
FE_TRIGGER	= 2
FE_PAD		= 3

LEFT	= "LEFT"
RIGHT	= "RIGHT"
WHOLE	= "WHOLE"
STICK	= "STICK"

FORMATS, NAMES = zip(*CONTROLER_FORMAT)
CI_NAMES = [ x for x in NAMES if not x.startswith('ukn_') ]

ControllerInput = namedtuple('ControllerInput', ' '.join(CI_NAMES))

SCI_NULL = ControllerInput._make(struct.unpack('<' + ''.join(FORMATS), b'\x00' * 64))

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


class SCButtons(IntEnum):
	RPADTOUCH = 0b00010000000000000000000000000000
	LPADTOUCH = 0b00001000000000000000000000000000
	RPAD	  = 0b00000100000000000000000000000000
	LPAD	  = 0b00000010000000000000000000000000 # Same for stick but without LPadTouch
	STICK     = 0b00000000000000000000000000000001 # generated internally, not sent by controller
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
