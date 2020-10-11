#!/usr/bin/env python2
"""
SC-Controller - Controller Registration Constants

Just huge chunk of constants put aside to make impotant code more readable
"""
from __future__ import unicode_literals

from scc.constants import SCButtons, STICK, LEFT, RIGHT
from scc.gui import BUTTON_ORDER

EMULATE_C_TIMEOUT = 100
AXIS_MASK = 0x100000	# Just to offset axis codes from button codes
X = 0
Y = 1

AXIS_ORDER = (
	("stick_x", X), ("stick_y", Y),
	("rpad_x", X),  ("rpad_y", Y),
	("lpad_x", X),  ("lpad_y", Y),
	("ltrig", X),	# index 6
	("rtrig", X),
)

STICK_PAD_AREAS = {
	# Numbers here are indexes to AXIS_ORDER tuple
	"STICK":	(STICK, (0, 1)),
	"RPAD":		(RIGHT, (2, 3)),
	"LPAD":		(LEFT, (4, 5)),
}

TRIGGER_AREAS = {
	# Numbers here are indexes to AXIS_ORDER tuple
	"LT": 6,
	"RT": 7
}

AXIS_TO_BUTTON = {
	# Maps stick and dpad axes to their respective "pressed" button
	"stick_x":	SCButtons.STICKPRESS,
	"stick_y":	SCButtons.STICKPRESS,
	"rpad_x":	SCButtons.RPADPRESS,
	"rpad_y":	SCButtons.RPADPRESS,
	"lpad_x":	SCButtons.LPADPRESS,
	"lpad_y":	SCButtons.LPADPRESS,
}

SDL_TO_SCC_NAMES = {
	'guide':			'C',
	'leftstick':		'STICKPRESS',
	'rightstick':		'RPADPRESS',
	'leftshoulder':		'LB',
	'rightshoulder':	'RB',
	'b0':				'X',
	'b1':				'A',
	'b2':				'B',
	'b3':				'Y',
	'b4':				'LT',
	'b5':				'RT',
	'b6':				'LB',
	'b7':				'RB',
	'b8':				'BACK',
	'b9':				'C',
	'b10':				'STICKPRESS',
	'b11':				'RPADPRESS',
	'b12':				'START',
}

SDL_AXES = (
	# This tuple has to use same order as AXIS_ORDER
	'leftx', 'lefty',
	'rightx', 'righty',
	"dpadx", "dpady",
	'lefttrigger',
	'righttrigger'
)


SDL_DPAD = {
	# Numbers here are indexes to AXIS_ORDER tuple
	# Booleans here are True for positive movements (down/right) and
	# False for negative (up/left)
	'dpdown':	(5, True),
	'dpleft':	(4, False),
	'dpright':	(4, True),
	'dpup':		(5, False),
}
