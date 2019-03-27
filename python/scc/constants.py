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

from scc.lib import IntEnum

"""
If SC-Controller is updated while daemon is running, DAEMON_VERSION send by
daemon will differ one one expected by UI and daemon will be forcefully restarted.
"""
DAEMON_VERSION = "0.4.5"

HPERIOD  = 0.02
LPERIOD  = 0.5
DURATION = 1.0

# Constants used when forcing gamepad to read some type of event is needed
FE_STICK	= 1
FE_TRIGGER	= 2
FE_PAD		= 3
FE_GYRO		= 4

# Trigger names, pads, etc. These constants are used on multiple places
LEFT	= "LEFT"
RIGHT	= "RIGHT"
CPAD	= "CPAD"
WHOLE	= "WHOLE"
STICK	= "STICK"
GYRO	= "GYRO"
PITCH	= "PITCH"
YAW		= "YAW"
ROLL	= "ROLL"

# Special constants currently used only by menus
SAME = "SAME"		# Menu is canceled by releasing same button that intiated it
DEFAULT = "DEFAULT"	# Default confirm/cancel button. A/B for menus initiated by
					# button, pad clicking / releasing for menus on pads

# Deadzone modes
CUT		= "CUT"
ROUND	= "ROUND"
LINEAR	= "LINEAR"
MINIMUM	= "MINIMUM"

PARSER_CONSTANTS = ( LEFT, RIGHT, WHOLE, STICK, GYRO, PITCH,
	YAW, ROLL, DEFAULT, SAME, CUT, ROUND, LINEAR, MINIMUM )



class SCButtons(IntEnum):
	RPADTOUCH	= 0b10000000000000000000000000000
	LPADTOUCH	= 0b01000000000000000000000000000
	RPAD		= 0b00100000000000000000000000000
	LPAD		= 0b00010000000000000000000000000 # Same for stick but without LPadTouch
	STICKPRESS	= 0b00000000000000000000000000001 # generated internally, not sent by controller
	RGRIP	 	= 0b00001000000000000000000000000
	LGRIP	 	= 0b00000100000000000000000000000
	START	 	= 0b00000010000000000000000000000
	C		 	= 0b00000001000000000000000000000
	BACK		= 0b00000000100000000000000000000
	A			= 0b00000000000001000000000000000
	X			= 0b00000000000000100000000000000
	B			= 0b00000000000000010000000000000
	Y			= 0b00000000000000001000000000000
	LB			= 0b00000000000000000100000000000
	RB			= 0b00000000000000000010000000000
	LT			= 0b00000000000000000001000000000
	RT			= 0b00000000000000000000100000000
	CPADTOUCH	= 0b00000000000000000000000000100 # Available on DS4 pad
	CPADPRESS	= 0b00000000000000000000000000010 # Available on DS4 pad


# If lpad and stick is used at once, this is sent as
# button with every other packet to signalize that
# value of lpad_x and lpad_y belongs to stick
STICKTILT		= 0b10000000000000000000000000000000


class HapticPos(IntEnum):
	"""Specify witch pad or trig is used"""
	RIGHT = 0
	LEFT = 1
	BOTH = 2	# emulated


class ControllerFlags(IntEnum):
	"""
	Used by mapper to workaround some physical differences between
	Steam Controller and other pads.
	"""
	NONE =				0		# No flags, default SC.
	HAS_RSTICK =		1 << 0	# Controller has right stick instead of touchpad
	SEPARATE_STICK =	1 << 1	# Left stick and left pad are using separate axes
	EUREL_GYROS =		1 << 2	# Gyro sensor values are provided as pitch, yaw
								# and roll instead of quaterion. 'q4' is unused
								# in such case.
	HAS_CPAD =			1 << 3	# Controller has DS4-like touchpad in center
	HAS_DPAD =			1 << 4	# Controller has normal d-pad instead of touchpad
	NO_GRIPS =			1 << 5	# Controller has no grips


STICK_PAD_MIN = -32768
STICK_PAD_MAX = 32768
STICK_PAD_MIN_HALF = STICK_PAD_MIN / 3
STICK_PAD_MAX_HALF = STICK_PAD_MAX / 3

TRIGGER_MIN = 0
TRIGGER_HALF = 50
TRIGGER_CLICK = 254 # Values under this are generated until trigger clicks
TRIGGER_MAX = 255
