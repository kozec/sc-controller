#!/usr/bin/env python2
"""
Quick and dirty ViGEm wrapper.

Supplies controller emulation part of uinput on Windows
"""


import os, sys, imp, ctypes, time
from ctypes import Structure, POINTER, c_bool, c_int16, c_uint16, c_int32
from ctypes import byref, sizeof, wintypes
from math import copysign
from uinput_constants import *	# Moved to separate module just to keep this clean

timeval = c_int32
user32 = ctypes.WinDLL('user32')


INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_UNICODE     = 0x0004
KEYEVENTF_SCANCODE    = 0x0008
MOUSEEVENTF_ABSOLUTE  = 0x8000
MOUSEEVENTF_MOVE      = 0x0001
MOUSEEVENTF_WHEEL     = 0x0800
MOUSEEVENTF_HWHEEL    = 0x1000
MOUSEEVENTF_ABSOLUTE    = 0x8000
MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_WHEEL       = 0x0800
MOUSEEVENTF_HWHEEL      = 0x1000
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_RIGHTDOWN   = 0x0008
MOUSEEVENTF_RIGHTUP     = 0x0010
MOUSEEVENTF_MIDDLEDOWN  = 0x0020
MOUSEEVENTF_MIDDLEUP    = 0x0040

MAPVK_VK_TO_VSC = 0
wintypes.ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
	_fields_ = (("wVk",         wintypes.WORD),
				("wScan",       wintypes.WORD),
				("dwFlags",     wintypes.DWORD),
				("time",        wintypes.DWORD),
				("dwExtraInfo", wintypes.ULONG_PTR))
	
	#def __init__(self, *args, **kwds):
	#	super(KEYBDINPUT, self).__init__(*args, **kwds)
	#	# some programs use the scan code even if KEYEVENTF_SCANCODE
	#	# isn't set in dwFflags, so attempt to map the correct code.
	#	if not self.dwFlags & KEYEVENTF_UNICODE:
	#		self.wScan = user32.MapVirtualKeyExW(self.wVk, MAPVK_VK_TO_VSC, 0)


class MOUSEINPUT(ctypes.Structure):
	_fields_ = (("dx",          wintypes.LONG),
				("dy",          wintypes.LONG),
				("mouseData",   wintypes.DWORD),
				("dwFlags",     wintypes.DWORD),
				("time",        wintypes.DWORD),
				("dwExtraInfo", wintypes.ULONG_PTR))


class HARDWAREINPUT(ctypes.Structure):
	_fields_ = (("uMsg",    wintypes.DWORD),
				("wParamL", wintypes.WORD),
				("wParamH", wintypes.WORD))


class INPUT(ctypes.Structure):
	class _INPUT(ctypes.Union):
		_fields_ = (("ki", KEYBDINPUT),
					("mi", MOUSEINPUT),
					("hi", HARDWAREINPUT))
	_anonymous_ = ("_input",)
	_fields_ = (("type",   wintypes.DWORD),
				("_input", _INPUT))

LPINPUT = POINTER(INPUT)


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
		self._k = keys
		self.name = name
		if not axes or len(axes) == 0:
			self._a, self._amin, self._amax, self._afuzz, self._aflat = [[]] * 5
		else:
			self._a, self._amin, self._amax, self._afuzz, self._aflat = zip(*axes)
		
		self._r = rels
		self._ff_events = None
		if rumble:
			self._ff_events = (POINTER(FeedbackEvent) * MAX_FEEDBACK_EFFECTS)()
			for i in xrange(MAX_FEEDBACK_EFFECTS):
				self._ff_events[i].contents = FeedbackEvent()
	
	
	def register_poll(self, poller, cb):
		""" Not available on Windows """
		pass
	
	
	def keyEvent(self, key, val):
		"""
		Generate a key or btn event
		
		@param int axis		 key or btn event (KEY_* or BTN_*)
		@param int val		  event value
		"""
		if key.value in SCAN_TO_VK:
			ki = KEYBDINPUT(wVk = SCAN_TO_VK[key.value])
		else:
			ki = KEYBDINPUT(wScan = key.value, dwFlags = KEYEVENTF_SCANCODE)
		if not val:
			ki.dwFlags |= KEYEVENTF_KEYUP
		
		x = INPUT(type=INPUT_KEYBOARD, ki=ki)
		user32.SendInput(1, byref(x), sizeof(x))
	# TODO: This
		pass
	
	def axisEvent(self, axis, val):
		"""
		Generate a abs event (joystick/pad axes)
		
		@param int axis		 abs event (ABS_*)
		@param int val		  event value
		"""
		# TODO: This
		pass
	
	
	def relEvent(self, rel, val):
		"""
		Generate a rel event (move move)

		@param int rel		  rel event (REL_*)
		@param int val		  event value
		"""
		if rel == Rels.REL_X:
			mi = MOUSEINPUT(dx = val, dwFlags=MOUSEEVENTF_MOVE)
		elif rel == Rels.REL_Y:
			mi = MOUSEINPUT(dy = val, dwFlags=MOUSEEVENTF_MOVE)
		elif rel == Rels.REL_WHEEL:
			mi = MOUSEINPUT(mouseData = val, dwFlags=MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_WHEEL)
		elif rel == Rels.REL_HWHEEL:
			mi = MOUSEINPUT(mouseData = val, dwFlags=MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_HWHEEL)
		else:
			# Unknown axis, ignore
			return
		x = INPUT(type=INPUT_MOUSE, mi=mi)
		user32.SendInput(1, byref(x), sizeof(x))
	
	
	def scanEvent(self, val):
		"""
		Generate a scan event (MSC_SCAN)

		@param int val		  scan event value (scancode)
		"""
		# TODO: This
		pass
	
	
	def synEvent(self):
		"""
		Generate a syn event
		"""
		# TODO: This
		pass
	
	
	def setDelayPeriod(self, delay, period):
		"""
		Update delay period values for keyboard

		@param int delay		delay in ms
		@param int period	   period is ms
		"""
		# TODO: This
		pass
	
	
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
		# TODO: This
		return None



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
		self._dx = 0.0
		self._dy = 0.0
		self.updateParams()

		self._scr_dx = 0.0
		self._scr_dy = 0.0
		self.updateScrollParams()
	
	
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
	
	
	def keyEvent(self, key, val):
		"""
		Generate a rel event (move move)

		@param int rel		  rel event (REL_*)
		@param int val		  event value
		"""
		if val:
			if key == Keys.BTN_LEFT:
				mi = MOUSEINPUT(dwFlags=MOUSEEVENTF_LEFTDOWN)
			elif key == Keys.Keys.BTN_MIDDLE:
				mi = MOUSEINPUT(dwFlags=MOUSEEVENTF_MIDDLEDOWN)
			elif key == Keys.BTN_RIGHT:
				mi = MOUSEINPUT(dwFlags=MOUSEEVENTF_RIGHTDOWN)
			else:
				# unknown button, ignored
				return
		else:
			if key == Keys.BTN_LEFT:
				mi = MOUSEINPUT(dwFlags=MOUSEEVENTF_LEFTUP)
			elif key == Keys.Keys.BTN_MIDDLE:
				mi = MOUSEINPUT(dwFlags=MOUSEEVENTF_MIDDLEUP)
			elif key == Keys.BTN_RIGHT:
				mi = MOUSEINPUT(dwFlags=MOUSEEVENTF_RIGHTUP)
			else:
				# unknown button, ignored
				return
		x = INPUT(type=INPUT_MOUSE, mi=mi)
		user32.SendInput(1, byref(x), sizeof(x))
	
	
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
		@param bool free		set to true for free ball move

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
									   keys=Scans.keys(),
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
	
	def keyManaged(self, ev):
		return False
	
	axisManaged = keyManaged
	relManaged = keyManaged


class CannotCreateUInputException(Exception):
	# Special case when message should be displayed in UI
	pass