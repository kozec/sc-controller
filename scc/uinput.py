#!/usr/bin/env python3

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
#
# all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os, ctypes, time
from ctypes import Structure, POINTER, c_bool, c_int16, c_uint16, c_int32, byref
from math import pi, copysign, sqrt
from scc.lib.libusb1 import timeval
from scc.tools import find_library
from scc.cheader import defines
from scc.lib import IntEnum

UNPUT_MODULE_VERSION = 9

# Get All defines from linux headers
if os.path.exists('/usr/include/linux/input-event-codes.h'):
	CHEAD = defines('/usr/include', 'linux/input-event-codes.h')
elif os.path.exists(os.path.split(__file__)[0] + '/input-event-codes.h'):
	CHEAD = defines(os.path.split(__file__)[0], 'input-event-codes.h')
else:
	CHEAD = defines('/usr/include', 'linux/input.h')

MAX_FEEDBACK_EFFECTS = 4

# Keys enum contains all keys and button from linux/uinput.h (KEY_* BTN_*)
Keys = IntEnum('Keys', {i: CHEAD[i] for i in list(CHEAD.keys()) if (i.startswith('KEY_') or
															i.startswith('BTN_'))})
# Keys enum contains all keys and button from linux/uinput.h (KEY_* BTN_*)
KeysOnly = IntEnum('KeysOnly', {i: CHEAD[i] for i in list(CHEAD.keys()) if i.startswith('KEY_')})

# Axes enum contains all axes from linux/uinput.h (ABS_*)
Axes = IntEnum('Axes', {i: CHEAD[i] for i in list(CHEAD.keys()) if i.startswith('ABS_')})

# Rels enum contains all rels from linux/uinput.h (REL_*)
Rels = IntEnum('Rels', {i: CHEAD[i] for i in list(CHEAD.keys()) if i.startswith('REL_')})

# Scan codes for each keys (taken from a logitech keyboard)
Scans = {
	Keys.KEY_ESC: 0x70029,
	Keys.KEY_F1: 0x7003a,
	Keys.KEY_F2: 0x7003b,
	Keys.KEY_F3: 0x7003c,
	Keys.KEY_F4: 0x7003d,
	Keys.KEY_F5: 0x7003e,
	Keys.KEY_F6: 0x7003f,
	Keys.KEY_F7: 0x70040,
	Keys.KEY_F8: 0x70041,
	Keys.KEY_F9: 0x70042,
	Keys.KEY_F10: 0x70043,
	Keys.KEY_F11: 0x70044,
	Keys.KEY_F12: 0x70045,
	Keys.KEY_SYSRQ: 0x70046,
	Keys.KEY_SCROLLLOCK: 0x70047,
	Keys.KEY_PAUSE: 0x70048,
	Keys.KEY_GRAVE: 0x70035,
	Keys.KEY_1: 0x7001e,
	Keys.KEY_2: 0x7001f,
	Keys.KEY_3: 0x70020,
	Keys.KEY_4: 0x70021,
	Keys.KEY_5: 0x70022,
	Keys.KEY_6: 0x70023,
	Keys.KEY_7: 0x70024,
	Keys.KEY_8: 0x70025,
	Keys.KEY_9: 0x70026,
	Keys.KEY_0: 0x70027,
	Keys.KEY_MINUS: 0x7002d,
	Keys.KEY_EQUAL: 0x7002e,
	Keys.KEY_BACKSPACE: 0x7002a,
	Keys.KEY_TAB: 0x7002b,
	Keys.KEY_Q: 0x70014,
	Keys.KEY_W: 0x7001a,
	Keys.KEY_E: 0x70008,
	Keys.KEY_R: 0x70015,
	Keys.KEY_T: 0x70017,
	Keys.KEY_Y: 0x7001c,
	Keys.KEY_U: 0x70018,
	Keys.KEY_I: 0x7000c,
	Keys.KEY_O: 0x70012,
	Keys.KEY_P: 0x70013,
	Keys.KEY_LEFTBRACE: 0x7002f,
	Keys.KEY_RIGHTBRACE: 0x70030,
	Keys.KEY_ENTER: 0x70028,
	Keys.KEY_CAPSLOCK: 0x70039,
	Keys.KEY_A: 0x70004,
	Keys.KEY_S: 0x70016,
	Keys.KEY_D: 0x70007,
	Keys.KEY_F: 0x70009,
	Keys.KEY_G: 0x7000a,
	Keys.KEY_H: 0x7000b,
	Keys.KEY_J: 0x7000d,
	Keys.KEY_K: 0x7000e,
	Keys.KEY_L: 0x7000f,
	Keys.KEY_SEMICOLON: 0x70033,
	Keys.KEY_APOSTROPHE: 0x70034,
	Keys.KEY_BACKSLASH: 0x70032,
	Keys.KEY_LEFTSHIFT: 0x700e1,
	Keys.KEY_102ND: 0x70064,
	Keys.KEY_Z: 0x7001d,
	Keys.KEY_X: 0x7001b,
	Keys.KEY_C: 0x70006,
	Keys.KEY_V: 0x70019,
	Keys.KEY_B: 0x70005,
	Keys.KEY_N: 0x70011,
	Keys.KEY_M: 0x70010,
	Keys.KEY_COMMA: 0x70036,
	Keys.KEY_DOT: 0x70037,
	Keys.KEY_SLASH: 0x70038,
	Keys.KEY_RIGHTSHIFT: 0x700e5,
	Keys.KEY_LEFTCTRL: 0x700e0,
	Keys.KEY_LEFTMETA: 0x700e3,
	Keys.KEY_LEFTALT: 0x700e2,
	Keys.KEY_SPACE: 0x7002c,
	Keys.KEY_RIGHTALT: 0x700e6,
	Keys.KEY_RIGHTMETA: 0x700e7,
	Keys.KEY_COMPOSE: 0x70065,
	Keys.KEY_RIGHTCTRL: 0x700e4,
	Keys.KEY_INSERT: 0x70049,
	Keys.KEY_HOME: 0x7004a,
	Keys.KEY_PAGEUP: 0x7004b,
	Keys.KEY_DELETE: 0x7004c,
	Keys.KEY_END: 0x7004d,
	Keys.KEY_PAGEDOWN: 0x7004e,
	Keys.KEY_UP: 0x70052,
	Keys.KEY_LEFT: 0x70050,
	Keys.KEY_DOWN: 0x70051,
	Keys.KEY_RIGHT: 0x7004f,
	Keys.KEY_NUMLOCK: 0x70053,
	Keys.KEY_KPSLASH: 0x70054,
	Keys.KEY_KPASTERISK: 0x70055,
	Keys.KEY_KPMINUS: 0x70056,
	Keys.KEY_KP7: 0x7005f,
	Keys.KEY_KP8: 0x70060,
	Keys.KEY_KP9: 0x70061,
	Keys.KEY_KPPLUS: 0x70057,
	Keys.KEY_KP4: 0x7005c,
	Keys.KEY_KP5: 0x7005d,
	Keys.KEY_KP6: 0x7005e,
	Keys.KEY_KP1: 0x70059,
	Keys.KEY_KP2: 0x7005a,
	Keys.KEY_KP3: 0x7005b,
	Keys.KEY_KPENTER: 0x70058,
	Keys.KEY_KP0: 0x70062,
	Keys.KEY_KPDOT: 0x70063,
	Keys.KEY_CONFIG: 0xc0183,
	Keys.KEY_PLAYPAUSE: 0xc00cd,
	Keys.KEY_MUTE: 0xc00e2,
	Keys.KEY_VOLUMEDOWN: 0xc00ea,
	Keys.KEY_VOLUMEUP: 0xc00e9,
	Keys.KEY_HOMEPAGE: 0xc0223,

	Keys.KEY_PREVIOUSSONG: 0xc00f0,
	Keys.KEY_NEXTSONG: 0xc00f1,

	Keys.KEY_BACK: 0xc00f2,
	Keys.KEY_FORWARD: 0xc00f3,
}

class InputEvent(ctypes.Structure):
	_fields_ = [
		('time', timeval),
		('type', c_uint16),
		('code', c_uint16),
		('value', c_int32)
	]

class FeedbackEvent(ctypes.Structure):
	_fields_ = [
		('in_use', c_bool),
		('continuous_rumble', c_bool),
		('duration', c_int32),
		('delay', c_int32),
		('repetitions', c_int32),
		('type', c_uint16),
		('level', c_int16),
	]

	def __init__(self):
		self.in_use = False


class UInput(object):
	"""
	UInput class permits to create a uinput device.

	See Gamepad, Mouse, Keyboard for examples
	"""


	def __init__(self, vendor, product, version, name, keys, axes, rels, keyboard=False, rumble=False):
		self._lib = None
		self._k = keys
		self.name = name
		if not axes or len(axes) == 0:
			self._a, self._amin, self._amax, self._afuzz, self._aflat = [[]] * 5
		else:
			self._a, self._amin, self._amax, self._afuzz, self._aflat = list(zip(*axes))

		self._r = rels
		
		self._lib = find_library("libuinput")
		self._ff_events = None
		if rumble:
			self._ff_events = (POINTER(FeedbackEvent) * MAX_FEEDBACK_EFFECTS)()
			for i in range(MAX_FEEDBACK_EFFECTS):
				self._ff_events[i].contents = FeedbackEvent()
		
		try:
			if self._lib.uinput_module_version() != UNPUT_MODULE_VERSION:
				raise Exception()
		except:
			import sys
			print("Invalid native module version. Please, recompile 'libuinput.so'", file=sys.stderr)
			print("If you are running sc-controller from source, you can do this by removing 'build' directory", file=sys.stderr)
			print("and runinng 'python setup.py build' or 'run.sh' script", file=sys.stderr)
			raise Exception("Invalid native module version")
		
		c_k		= (ctypes.c_uint16 * len(self._k))(*self._k)
		c_a		= (ctypes.c_uint16 * len(self._a))(*self._a)
		c_amin	 = (ctypes.c_int32  * len(self._amin ))(*self._amin )
		c_amax	 = (ctypes.c_int32  * len(self._amax ))(*self._amax )
		c_afuzz	= (ctypes.c_int32  * len(self._afuzz))(*self._afuzz)
		c_aflat	= (ctypes.c_int32  * len(self._aflat))(*self._aflat)
		c_r		= (ctypes.c_uint16 * len(self._r))(*self._r)
		c_vendor   = ctypes.c_uint16(vendor)
		c_product  = ctypes.c_uint16(product)
		c_version  = ctypes.c_uint16(version)
		c_keyboard = ctypes.c_int(keyboard)
		c_rumble = ctypes.c_int(MAX_FEEDBACK_EFFECTS if rumble else 0)
		c_name = ctypes.c_char_p(name.encode("utf-8"))
		
		self._fd = self._lib.uinput_init(ctypes.c_int(len(self._k)),
										 c_k,
										 ctypes.c_int(len(self._a)),
										 c_a,
										 c_amin,
										 c_amax,
										 c_afuzz,
										 c_aflat,
										 ctypes.c_int(len(self._r)),
										 c_r,
										 c_keyboard,
										 c_vendor,
										 c_product,
										 c_version,
										 c_rumble,
										 c_name)
		if self._fd < 0:
			raise CannotCreateUInputException("Failed to create uinput device. Error code: %s" % (self._fd,))


	def getDescriptor(self):
		return self._fd


	def keyEvent(self, key, val):
		"""
		Generate a key or btn event

		@param int axis		 key or btn event (KEY_* or BTN_*)
		@param int val		  event value
		"""
		self._lib.uinput_key(self._fd,
							 ctypes.c_uint16(key),
							 ctypes.c_int32(val))


	def axisEvent(self, axis, val):
		"""
		Generate a abs event (joystick/pad axes)

		@param int axis		 abs event (ABS_*)
		@param int val		  event value
		"""
		self._lib.uinput_abs(self._fd,
							 ctypes.c_uint16(axis),
							 ctypes.c_int32(val))

	def relEvent(self, rel, val):
		"""
		Generate a rel event (move move)

		@param int rel		  rel event (REL_*)
		@param int val		  event value
		"""
		self._lib.uinput_rel(self._fd,
							 ctypes.c_uint16(rel),
							 ctypes.c_int32(val))

	def scanEvent(self, val):
		"""
		Generate a scan event (MSC_SCAN)

		@param int val		  scan event value (scancode)
		"""
		self._lib.uinput_scan(self._fd,
							  ctypes.c_int32(val))

	def synEvent(self):
		"""
		Generate a syn event
		"""
		self._lib.uinput_syn(self._fd)


	def setDelayPeriod(self, delay, period):
		"""
		Update delay period values for keyboard

		@param int delay		delay in ms
		@param int period	   period is ms
		"""

		self._lib.uinput_set_delay_period(self._fd,
										  ctypes.c_int32(delay),
										  ctypes.c_int32(period))

	def keyManaged(self, ev):
		return ev in self._k

	def axisManaged(self, ev):
		return ev in self._a

	def relManaged(self, ev):
		return ev in self._r

	def ff_read(self):
		"""
		Returns effect that should be played or None if there were no such request.
		"""
		if self._ff_events:
			id = self._lib.uinput_ff_read(self._fd, MAX_FEEDBACK_EFFECTS, byref(self._ff_events))
			if id >= 0:
				return self._ff_events[id].contents
		return None

	def __del__(self):
		if self._lib:
			self._lib.uinput_destroy(self._fd)


class Gamepad(UInput):
	"""
	Gamepad uinput class, create a Xbox360 gamepad device
	"""

	def __init__(self, name):
		super(Gamepad, self).__init__(vendor=0x045e,
									  product=0x028e,
									  version=1,
									  name=name,
									  keys=[Keys.BTN_START,
											Keys.BTN_MODE,
											Keys.BTN_SELECT,
											Keys.BTN_A,
											Keys.BTN_B,
											Keys.BTN_X,
											Keys.BTN_Y,
											Keys.BTN_TL,
											Keys.BTN_TR,
											Keys.BTN_THUMBL,
											Keys.BTN_THUMBR],
									  axes=[(Axes.ABS_X, -32768, 32767, 16, 128),
											(Axes.ABS_Y, -32768, 32767, 16, 128),
											(Axes.ABS_RX, -32768, 32767, 16, 128),
											(Axes.ABS_RY, -32768, 32767, 16, 128),
											(Axes.ABS_Z, 0, 255, 0, 0),
											(Axes.ABS_RZ, 0, 255, 0, 0),
											(Axes.ABS_HAT0X, -1, 1, 0, 0),
											(Axes.ABS_HAT0Y, -1, 1, 0, 0)],
									  rels=[])


class Mouse(UInput):

	"""
	Mouse uinput class, create a mouse device

	moveEvent can emulate free ball rotation of a track ball
	updateParams permit to upgrade ball model and move scale
	"""

	DEFAULT_XSCALE = 0.006
	DEFAULT_YSCALE = 0.006

	DEFAULT_SCR_XSCALE = 0.0005
	DEFAULT_SCR_YSCALE = 0.0005

	def __init__(self, name):
		super(Mouse, self).__init__(vendor=0x28de,
									product=0x1142,
									version=1,
									name=name,
									keys=[Keys.BTN_LEFT,
										  Keys.BTN_RIGHT,
										  Keys.BTN_MIDDLE,
										  Keys.BTN_SIDE,
										  Keys.BTN_EXTRA],
									axes=[],
									rels=[Rels.REL_X,
										  Rels.REL_Y,
										  Rels.REL_WHEEL,
										  Rels.REL_HWHEEL])
		self.updateParams()
		self.updateScrollParams()
		self.reset()

	def reset(self):
		"""
		Resets internal counters, especially one used for wheel.
		Fixes scroll wheel feedback desynchronisation, as reported
		in https://github.com/kozec/sc-controller/issues/222
		"""
		self._scr_dx = 0.0
		self._scr_dy = 0.0
		self._dx = 0.0
		self._dy = 0.0

	def updateParams(self,
					 xscale=DEFAULT_XSCALE,
					 yscale=DEFAULT_YSCALE):
		"""
		Update Movement parameters

		@param float mass	   mass in g of the ball
		@param float r		  radius in m of the ball
		@param int ampli		integer amplitude for move from border to border
		@param float degree	 degree of rotation of the ball for move from border to border
		@param float xscale	 scale applied on move param to input event on x axis
		@param float yscale	 scale applied on move param to input event on y axis
		"""
		self._xscale = xscale
		self._yscale = yscale

	def updateScrollParams(self,
						   xscale=DEFAULT_SCR_XSCALE,
						   yscale=DEFAULT_SCR_YSCALE):
		"""
		Update Scroll parameters

		@param float mass	   mass in g of the ball
		@param float r		  radius in m of the ball
		@param float friction   constat friction force applied to the ball
		@param int ampli		integer amplitude for move from border to border
		@param float degree	 degree of rotation of the ball for move from border to border
		@param float xscale	 scale applied on move param to input event on x axis
		@param float yscale	 scale applied on move param to input event on y axis
		"""
		self._scr_xscale = xscale
		self._scr_yscale = yscale

	def moveEvent(self, dx=0, dy=0):
		"""
		Generate move events from parametters and displacement

		@param int dx		   delta movement from last call on x axis
		@param int dy		   delta movement from last call on y axis

		"""
		self._dx += dx * self._xscale
		self._dy += dy * self._yscale
		_syn = False
		if int(self._dx):
			self.relEvent(rel=Rels.REL_X, val=int(self._dx))
			self._dx -= int(self._dx)
			_syn = True
		if int(self._dy):
			self.relEvent(rel=Rels.REL_Y, val=int(self._dy))
			self._dy -= int(self._dy)
			_syn = True
		if _syn:
			self.synEvent()

	def scrollEvent(self, dx=0, dy=0):
		"""
		Generate scroll events from parametters and displacement

		@param int dx		   delta movement from last call on x axis
		@param int dy		   delta movement from last call on y axis

		@return float		   absolute distance moved this tick

		"""
		# Compute mouse mouvement from interger part of d * scale
		self._scr_dx += dx * self._scr_xscale
		self._scr_dy += dy * self._scr_yscale
		_syn = False
		if int(self._scr_dx):
			self.relEvent(rel=Rels.REL_HWHEEL, val=int(copysign(1, self._scr_dx)))
			self._scr_dx -= int(self._scr_dx)
			_syn = True
		if int(self._scr_dy):
			self.relEvent(rel=Rels.REL_WHEEL,  val=int(copysign(1, self._scr_dy)))
			self._scr_dy -= int(self._scr_dy)
			_syn = True
		if _syn:
			self.synEvent()


class Keyboard(UInput):
	"""
	Keyboard uinput class, create a keyboard device.

	pressEvent permit to generate a key pressed and with scan events
	releaseEvent permit to generate a key released and with scan events

	autorepead delay and period are preset respectively to 250ms and 33ms
	setDelayPeriod permits to update these values
	"""

	def __init__(self, name):
		super(Keyboard, self).__init__(vendor=0x28de,
									   product=0x1142,
									   version=1,
									   name=name,
									   keys=list(Scans.keys()),
									   axes=[],
									   rels=[],
									   keyboard=True)
		self.setDelayPeriod(250, 33)
		self._dx = 0.0
		self._pressed = set()

	def pressEvent(self, keys):
		"""
		Generate key press event with corresponding scan codes.
		Events are generated only for new keys.

		@param list of Keys keys		keys to press
		"""

		new = [k for k in keys if k not in self._pressed]
		for i in new:
			self.scanEvent(Scans[i])
			self.keyEvent(i, 1)
		if len(new):
			self.synEvent()
			self._pressed |= set(new)

	def releaseEvent(self, keys=None):
		"""
		Generate key release event with corresponding scan codes.
		Events are generated only for keys that was pressed


		@param list of Keys keys		keys to release, give None or empty list
										to release all
		"""
		if keys and len(keys):
			rem = [k for k in keys if k in self._pressed]
		else:
			rem = list(self._pressed)
		for i in rem:
			self.scanEvent(Scans[i])
			self.keyEvent(i, 0)
		if len(rem):
			self.synEvent()
			self._pressed -= set(rem)


class Dummy(object):
	""" Fake uinput device that does nothing, but has all required methods """
	def __init__(self, *a, **b):
		pass
	
	def keyEvent(self, *a, **b):
		pass
	
	axisEvent = keyEvent
	relEvent = keyEvent
	scanEvent = keyEvent
	synEvent = keyEvent
	setDelayPeriod = keyEvent
	updateParams = keyEvent
	updateScrollParams = keyEvent
	moveEvent = keyEvent
	scrollEvent = keyEvent
	pressEvent = keyEvent
	releaseEvent = keyEvent
	reset = keyEvent
	
	def keyManaged(self, ev):
		return False
	
	axisManaged = keyManaged
	relManaged = keyManaged


class CannotCreateUInputException(Exception):
	# Special case when message should be displayed in UI
	pass
