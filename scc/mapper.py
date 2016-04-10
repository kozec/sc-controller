#!/usr/bin/python2
from __future__ import unicode_literals

import traceback
from collections import deque
from scc.uinput import Gamepad, Keyboard, Mouse
from scc.uinput import Keys, Axes, Rels
from scc.profile import Profile
from scc.constants import SCStatus, SCButtons, SCI_NULL
from scc.constants import CI_NAMES, ControllerInput

STICK_PAD_MIN = -32767
STICK_PAD_MAX = 32767
STICK_PAD_MIN_HALF = STICK_PAD_MIN / 2
STICK_PAD_MAX_HALF = STICK_PAD_MAX / 2

TRIGGERS_MIN = 0
TRIGGERS_HALF = 50
TRIGGERS_CLICK = 254 # Values under this are generated until trigger clicks
TRIGGERS_MAX = 255

FE_STICK = 1
FE_TRIGGER = 2
FE_PAD = 3

class ControllerEventHanlder(object):
	""" Used as locals when evaluating command for controller event """
	GLOBS = {
		'Keys' : Keys,
		'Axes' : Axes,
		'Rels' : Rels
	}
	
	def __init__(self, mapper):
		self.mapper = mapper
		self.locs = {
			# Actions
			'mapper' : mapper,
			'key' : self.key,
			'pad' : self.pad,
			'axis' : self.axis,
			'dpad' : self.dpad,
			'mouse' : self.mouse,
			'trackpad' : self.trackpad,
			'trackball' : self.trackball,
			'wheel' : self.wheel,
			'button' : self.button,
			'click' : self.click,
			# Shortcuts
			'raxis' : self.raxis,
			'hatup' : self.hatup,
			'hatdown' : self.hatdown,
			'hatleft' : self.hatup,
			'hatright' : self.hatdown,
		}
	
	def trackpad(self, *a):
		pass
	
	
	def trackball(self, *a):
		pass
	
	
	def wheel(self, *a):
		pass
	
	
	def dpad(self, *a):
		pass
	
	
	def raxis(self, id):
		return self.axis(id, 32767, -32767)
	
	
	def hatup(self, id):
		return self.axis(id, 0, 32767)
	
	
	def hatdown(self, id):
		return self.axis(id, 0, -32767)


class ButtonPressEvent(ControllerEventHanlder):
	def key(self, key1, *a):
		self.mapper.keypress_list.append(key1)
		return True
	
	
	def button(self, button1, *a):
		self.mapper.mouse.keyEvent(button1, 1)
		self.mapper.syn_list.add(self.mapper.mouse)
		return True

	
	def pad(self, button1, *a):
		self.mapper.gamepad.keyEvent(button1, 1)
		self.mapper.syn_list.add(self.mapper.gamepad)
		return True
	
	
	def mouse(self, axis, speed=1):
		# This is generaly bad idea...
		if axis == Rels.REL_X:
			self.mapper.mouse.moveEvent(1000 * speed, 0, False)
			self.mapper.syn_list.add(self.mapper.mouse)
		elif axis == Rels.REL_Y:
			self.mapper.mouse.moveEvent(0, 1000 * speed, False)
			self.mapper.syn_list.add(self.mapper.mouse)
		elif axis == Rels.REL_WHEEL:
			self.mapper.mouse.scrollEvent(0, 2000 * speed, False)
			self.mapper.syn_list.add(self.mapper.mouse)	
		return True
	
	
	def axis(self, id, min = STICK_PAD_MIN, max = STICK_PAD_MAX):
		self.mapper.gamepad.axisEvent(id, max)
		self.mapper.syn_list.add(self.mapper.gamepad)
		return True
	
	
	def click(self, *a):
		return True


class ButtonReleaseEvent(ControllerEventHanlder):
	def key(self, key1, *a):
		self.mapper.keyrelease_list.append(key1)
		return False
	
	def button(self, button1, *a):
		self.mapper.mouse.keyEvent(button1, 0)
		self.mapper.syn_list.add(self.mapper.mouse)
		return False
	
	
	def pad(self, button1, *a):
		self.mapper.gamepad.keyEvent(button1, 0)
		self.mapper.syn_list.add(self.mapper.gamepad)
		return False
	
	
	def mouse(self, axis, speed=10):
		# Does nothing
		return False
	
	
	def axis(self, id, min = STICK_PAD_MIN, max = STICK_PAD_MAX):
		self.mapper.gamepad.axisEvent(id, min)
		self.mapper.syn_list.add(self.mapper.gamepad)
		return False
	
	
	def click(self, *a):
		return True


class StickEvent(ControllerEventHanlder):
	def __init__(self, mapper, axis_attr, axis2_attr, click_button):
		ControllerEventHanlder.__init__(self, mapper)
		self.axis_attr = axis_attr
		self.axis2_attr = axis2_attr
		self.click_button = click_button
		self.dpad_state = [ None, None ]
	
	
	def _by_trigger(self, option1, option2, minustrigger, plustrigger):
		"""
		Choses which key or button should be pressed or released based on
		current stick position.
		
		Returns list of actions represented by tuples of (pressed, option)
		where 'pressed' is True if chosen button should be pressed.
		"""
		old_p = getattr(self.mapper.old_state, self.axis_attr)
		p = getattr(self.mapper.state, self.axis_attr)
		rv = []
		
		if p <= minustrigger and old_p > minustrigger:
			rv.append( (True, option1) )
		elif p > minustrigger and old_p <= minustrigger:
			rv.append( (False, option1) )
		if option2 is not None:
			if p >= plustrigger and old_p < plustrigger:
				rv.append( (True, option2) )
			elif p < plustrigger and old_p >= plustrigger:
				rv.append( (False, option2) )
		return rv
	
	
	def key(self, key1, key2 = None, minustrigger = STICK_PAD_MIN_HALF, plustrigger = STICK_PAD_MAX_HALF):
		rv = False
		for (pressed, key) in self._by_trigger(key1, key2, minustrigger, plustrigger):
			if pressed:
				self.mapper.keypress_list.append(key)
				rv = True
			else:
				self.mapper.keyrelease_list.append(key)
		return rv
	
	
	def button(self, button1, button2 = None, minustrigger = STICK_PAD_MIN_HALF, plustrigger = STICK_PAD_MAX_HALF):
		rv = False
		for (pressed, button) in self._by_trigger(button1, button2, minustrigger, plustrigger):
			if pressed:
				self.mapper.mouse.keyEvent(button, 1)
				rv = True
			else:
				self.mapper.mouse.keyEvent(button, 0)
			self.mapper.syn_list.add(self.mapper.mouse)
		return rv
	
	
	def pad(self, button1, button2 = None, minustrigger = STICK_PAD_MIN_HALF, plustrigger = STICK_PAD_MAX_HALF):
		rv = False
		for (pressed, button) in self._by_trigger(button1, button2, minustrigger, plustrigger):
			if pressed:
				self.mapper.gamepad.keyEvent(button, 1)
				rv = True
			else:
				self.mapper.gamepad.keyEvent(button, 0)
			self.mapper.syn_list.add(self.mapper.gamepad)
		return rv
	
	
	def mouse(self, axis, speed=1):
		p = getattr(self.mapper.state, self.axis_attr) * speed / 100

		# This is generaly bad idea...
		if axis == Rels.REL_X:
			self.mapper.mouse.moveEvent(p, 0, False)
			self.mapper.syn_list.add(self.mapper.mouse)
		elif axis == Rels.REL_Y:
			self.mapper.mouse.moveEvent(0, -p, False)
			self.mapper.syn_list.add(self.mapper.mouse)
		elif axis == Rels.REL_WHEEL:
			self.mapper.mouse.scrollEvent(0, p, False)
			self.mapper.syn_list.add(self.mapper.mouse)
		self.mapper.force_event.add(FE_STICK)
		return False	# TODO: Some magic for feedback here
	
	
	def axis(self, id, min = STICK_PAD_MIN, max = STICK_PAD_MAX):
		p = float(getattr(self.mapper.state, self.axis_attr) - STICK_PAD_MIN) / (STICK_PAD_MAX - STICK_PAD_MIN)
		p = int((p * (max - min)) + min)
		self.mapper.gamepad.axisEvent(id, p)
		self.mapper.syn_list.add(self.mapper.gamepad)
		return True
	
	
	def dpad(self, up, down = None, left = None, right = None):
		rv = False
		old_x = getattr(self.mapper.old_state, self.axis_attr)
		old_y = getattr(self.mapper.old_state, self.axis2_attr)
		x = getattr(self.mapper.state, self.axis_attr)
		y = getattr(self.mapper.state, self.axis2_attr)
		
		side = [ None, None ]
		if x <= STICK_PAD_MIN_HALF:
			side[0] = "left"
		elif x >= STICK_PAD_MAX_HALF:
			side[0] = "right"
		if y <= STICK_PAD_MIN_HALF:
			side[1] = "down"
		elif y >= STICK_PAD_MAX_HALF:
			side[1] = "up"
		
		for i in (0, 1):
			if side[i] != self.dpad_state[i] and self.dpad_state[i] is not None:
				if locals()[self.dpad_state[i]] is not None:
					rv = self.mapper.eeval(locals()[self.dpad_state[i]], self.mapper.bre.GLOBS, self.mapper.bre.locs) or rv
				self.dpad_state[i] = None
			if side[i] is not None and side[i] != self.dpad_state[i]:
				if locals()[side[i]] is not None:
					rv = self.mapper.eeval(locals()[side[i]], self.mapper.bpe.GLOBS, self.mapper.bpe.locs) or rv
				self.dpad_state[i] = side[i]
		return rv
	
	
	def click(self, *a):
		# Pad is still pressed
		if self.mapper.state.buttons & self.click_button : return True
		# Check if pad was just released
		if self.mapper.old_state.buttons & self.click_button :
			# Set axis position to 0,0
			data = { x : getattr(self.mapper.state, x) for x in CI_NAMES }
			data[self.axis_attr] = 0
			if self.axis2_attr is not None:
				data[self.axis2_attr] = 0
			self.mapper.state = ControllerInput(**data)
			return True
		
		# Not pressed
		return False


class PadEvent(StickEvent):
	def __init__(self, mapper, axis_attr, axis2_attr, click_button, touch_button):
		StickEvent.__init__(self, mapper, axis_attr, axis2_attr, click_button)
		self.touch_button = touch_button
		self.dq = [ deque(maxlen=8), deque(maxlen=8), deque(maxlen=8), deque(maxlen=8) ]
		self.trackpadmode = False
	
	
	def _dq_add(self, axis, current_position):
		try:
			prev = int(sum(self.dq[axis]) / len(self.dq[axis]))
		except ZeroDivisionError:
			prev = 0
		self.dq[axis].append(current_position)

		try:
			m = int(sum(self.dq[axis]) / len(self.dq[axis]))
		except ZeroDivisionError:
			m = 0
		if not self.mapper.old_state.buttons & self.touch_button:
			# Pad was just pressed
			prev = m
		return prev, m
	
	def trackball(self, speed=1, trackpadmode=False):
		px, mx = self._dq_add(0, getattr(self.mapper.state, self.axis_attr))
		py, my = self._dq_add(1, getattr(self.mapper.state, self.axis2_attr))
		
		if not self.mapper.state.buttons & self.touch_button:
			# Pad was just released
			if not trackpadmode:
				dist = self.mapper.mouse.moveEvent(0, 0, True)
				if dist:
					self.mapper.force_event.add(FE_PAD)
			self.dq[0].clear()
			self.dq[1].clear()
			return False
			
		dx = mx - px
		dy = my - py
		self.mapper.mouse.moveEvent(dx * speed, dy * speed * -1, False)
		self.mapper.force_event.add(FE_PAD)
		
		return False	# TODO: Some magic for feedback here
	
	def wheel(self, trackball=False, speed=1):
		py, y = self._dq_add(2, getattr(self.mapper.state, self.axis_attr))
		px, x = 0, 0
		if self.axis2_attr is not None:
			px, x = py, y
			py, y = self._dq_add(3, getattr(self.mapper.state, self.axis2_attr))
		
		if not self.mapper.state.buttons & self.touch_button:
			# Pad was just released
			if trackball:
				dist = self.mapper.mouse.scrollEvent(0, 0, True)
				if dist:
					self.mapper.force_event.add(FE_PAD)
			self.dq[2].clear()
			self.dq[3].clear()
			return False
			
		dx = x - px
		dy = y - py
		self.mapper.mouse.scrollEvent(dx * speed, dy * speed, False)
		self.mapper.force_event.add(FE_PAD)
	
	
	def trackpad(self, speed=1):
		return self.trackball(speed, trackpadmode=True)


class TriggerEvent(ControllerEventHanlder):
	def __init__(self, mapper, axis_attr):
		ControllerEventHanlder.__init__(self, mapper)
		self.axis_attr = axis_attr
		self.pressed_key = None
		self.released = True
	
	
	def _by_trigger(self, option1, option2, first_trigger, full_trigger):
		"""
		Choses which key or button should be pressed or released based on
		current trigger position.
		
		Returns list of actions represented by tuples of (pressed, option)
		where 'pressed' is True if chosen button should be pressed.
		"""
		old_p = getattr(self.mapper.old_state, self.axis_attr)
		p = getattr(self.mapper.state, self.axis_attr)
		rv = []
		
		if option2 is None:
			if p >= first_trigger and old_p < first_trigger:
				rv.append([ True, option1 ])
			elif p < first_trigger and old_p >= first_trigger:
				rv.append([ False, option1 ])
		else:
			if p >= first_trigger and p < full_trigger:
				if self.pressed_key != option1 and self.released:
					rv.append([ True, option1 ])
					self.pressed_key = option1
					self.released = False
			else:
				if self.pressed_key == option1:
					rv.append([ False, option1 ])
					self.pressed_key = None
			if p > full_trigger and old_p < full_trigger:
				if self.pressed_key != option2:
					if self.pressed_key is not None:
						rv.append([ False, self.pressed_key ])
					rv.append([ True, option2 ])
					self.pressed_key = option2
					self.released = False
			else:
				if self.pressed_key == option2:
					rv.append([ False, option2 ])
					self.pressed_key = None
		
		if p <= TRIGGERS_MIN:
			self.released = True
		return rv
	
	
	def key(self, key1, key2 = None, first_trigger = TRIGGERS_HALF, full_trigger = TRIGGERS_CLICK):
		rv = False
		for (pressed, key) in self._by_trigger(key1, key2, first_trigger, full_trigger):
			if pressed:
				self.mapper.keypress_list.append(key)
				rv = True
			else:
				self.mapper.keyrelease_list.append(key)
		return rv


	def button(self, button1, button2 = None, first_trigger = TRIGGERS_HALF, full_trigger = TRIGGERS_CLICK):
		rv = False
		for (pressed, button) in self._by_trigger(button1, button2, first_trigger, full_trigger):
			if pressed:
				self.mapper.mouse.keyEvent(button, 1)
				rv = True
			else:
				self.mapper.mouse.keyEvent(button, 0)
			self.mapper.syn_list.add(self.mapper.mouse)
		return rv
	
	
	def pad(self, button1, button2 = None, first_trigger = TRIGGERS_HALF, full_trigger = TRIGGERS_CLICK):
		rv = False
		for (pressed, button) in self._by_trigger(button1, button2, first_trigger, full_trigger):
			if pressed:
				self.mapper.gamepad.keyEvent(button, 1)
				rv = True
			else:
				self.mapper.gamepad.keyEvent(button, 0)
			self.mapper.syn_list.add(self.mapper.gamepad)
		return rv
	
	
	def mouse(self, axis, speed=1):
		p = getattr(self.mapper.state, self.axis_attr) * speed * 1

		# This is generaly bad idea...
		if axis == Rels.REL_X:
			self.mapper.mouse.moveEvent(p, 0, False)
			self.mapper.syn_list.add(self.mapper.mouse)
		elif axis == Rels.REL_Y:
			self.mapper.mouse.moveEvent(0, -p, False)
			self.mapper.syn_list.add(self.mapper.mouse)
		elif axis == Rels.REL_WHEEL:
			self.mapper.mouse.scrollEvent(0, p, False)
			self.mapper.syn_list.add(self.mapper.mouse)
		self.mapper.force_event.add(FE_TRIGGER)
		return False
		
	
	def axis(self, id, min = TRIGGERS_MIN, max = TRIGGERS_MAX):
		p = float(getattr(self.mapper.state, self.axis_attr) - TRIGGERS_MIN) / (TRIGGERS_MAX - TRIGGERS_MIN)
		p = int((p * (max - min)) + min)
		self.mapper.gamepad.axisEvent(id, p)
		self.mapper.syn_list.add(self.mapper.gamepad)
		return True
		
	
	def click(self, *a):
		p = getattr(self.mapper.state, self.axis_attr)
		if p > TRIGGERS_CLICK : return True
		p = getattr(self.mapper.old_state, self.axis_attr)
		# Check if trigger was just released
		if p > TRIGGERS_CLICK:
			# Set trigger position to 0
			data = { x : getattr(self.mapper.state, x) for x in CI_NAMES }
			data[self.axis_attr] = 0
			self.mapper.state = ControllerInput(**data)
			return True
		
		# Not pressed
		return False
		



class Mapper(object):
	DEBUG = False
	
	def __init__(self, profile):
		self.profile = profile
		
		# Create virtual devices
		self.gamepad = Gamepad()
		self.keyboard = Keyboard()
		self.mouse = Mouse()
		self.mouse.updateParams(
			friction=Mouse.DEFAULT_FRICTION,
			xscale=Mouse.DEFAULT_XSCALE,
			yscale=Mouse.DEFAULT_YSCALE)
		self.mouse.updateScrollParams(
			friction=Mouse.DEFAULT_SCR_FRICTION,
			xscale=Mouse.DEFAULT_SCR_XSCALE,
			yscale=Mouse.DEFAULT_SCR_XSCALE
		)
		
		# Set emulation
		self.keypress_list = []
		self.keyrelease_list = []
		self.syn_list = set()
		self.old_state = SCI_NULL
		self.state = SCI_NULL
		self.force_event = set()
		self.bpe =					ButtonPressEvent(self)
		self.bre =					ButtonReleaseEvent(self)
		self.se  = { x :			StickEvent(self, Profile.STICK_AXES[x], None, SCButtons.LPAD) for x in Profile.STICK_AXES }
		self.lpe = { x :			PadEvent(self, Profile.LPAD_AXES[x], None, SCButtons.LPAD, SCButtons.LPADTOUCH) for x in Profile.LPAD_AXES }
		self.rpe = { x :			PadEvent(self, Profile.RPAD_AXES[x], None, SCButtons.RPAD, SCButtons.RPADTOUCH) for x in Profile.RPAD_AXES }
		self.se[Profile.WHOLE]  =	StickEvent(self, "lpad_x", "lpad_y", SCButtons.LPAD)
		self.lpe[Profile.WHOLE] =	PadEvent(self, "lpad_x", "lpad_y", SCButtons.LPAD, SCButtons.LPADTOUCH)
		self.rpe[Profile.WHOLE] =	PadEvent(self, "rpad_x", "rpad_y", SCButtons.RPAD, SCButtons.RPADTOUCH)
		self.lte = 					TriggerEvent(self, "ltrig")
		self.rte = 					TriggerEvent(self, "rtrig")
	
	
	def eeval(self, code, globs, locs):
		""" eval in try... except with optional logging """
		try:
			if Mapper.DEBUG:
				print "Executing", code
			eval(code, globs, locs)
		except:
			traceback.print_exc()
	
	
	def callback(self, controller, sci):
		# Store state
		#print sci
		if sci.status != SCStatus.INPUT:
			return
		self.old_state = self.state
		self.state = sci
		fe = self.force_event
		self.force_event = set()
		
		# Check buttons
		xor = self.old_state.buttons ^ sci.buttons
		btn_rem = xor & self.old_state.buttons
		btn_add = xor & sci.buttons
		
		if btn_add or btn_rem:
			# At least one button was pressed
			for x in self.profile.buttons:
				if x & btn_add:
					self.eeval(self.profile.buttons[x], self.bpe.GLOBS, self.bpe.locs)
				elif x & btn_rem:
					self.eeval(self.profile.buttons[x], self.bre.GLOBS, self.bre.locs)
		
		# Check stick
		if not sci.buttons & SCButtons.LPADTOUCH:
			if FE_STICK in fe or self.old_state.lpad_x != sci.lpad_x or self.old_state.lpad_y != sci.lpad_y:
				# STICK
				if Profile.WHOLE in self.profile.stick:
					self.eeval(self.profile.stick[Profile.WHOLE], self.se[Profile.WHOLE].GLOBS, self.se[Profile.WHOLE].locs)
				else:
					for x in Profile.STICK_AXES:
						if x in self.profile.stick:
							self.eeval(self.profile.stick[x], self.se[x].GLOBS, self.se[x].locs)
		
		# Check triggers
		if FE_TRIGGER in fe or sci.ltrig != self.old_state.ltrig:
			if Profile.LEFT in self.profile.triggers:
				self.eeval(self.profile.triggers[Profile.LEFT], self.lte.GLOBS, self.lte.locs)
		if FE_TRIGGER in fe or sci.rtrig != self.old_state.rtrig:
			if Profile.RIGHT in self.profile.triggers:
				self.eeval(self.profile.triggers[Profile.RIGHT], self.rte.GLOBS, self.rte.locs)
		
		# Check pads
		if FE_PAD in fe or sci.buttons & SCButtons.RPADTOUCH or SCButtons.RPADTOUCH & btn_rem:
			# RPAD
			if Profile.WHOLE in self.profile.pads[Profile.RIGHT]:
				self.eeval(self.profile.pads[Profile.RIGHT][Profile.WHOLE], self.rpe[Profile.WHOLE].GLOBS, self.rpe[Profile.WHOLE].locs)
			else:
				for x in Profile.RPAD_AXES:
					if x in self.profile.pads[Profile.RIGHT]:
						self.eeval(self.profile.pads[Profile.RIGHT][x], self.rpe[x].GLOBS, self.rpe[x].locs)
		
		if FE_PAD in fe or sci.buttons & SCButtons.LPADTOUCH or SCButtons.LPADTOUCH & btn_rem:
			# LPAD
			if Profile.WHOLE in self.profile.pads[Profile.LEFT]:
				self.eeval(self.profile.pads[Profile.LEFT][Profile.WHOLE], self.lpe[Profile.WHOLE].GLOBS, self.lpe[Profile.WHOLE].locs)
			else:
				for x in Profile.LPAD_AXES:
					if x in self.profile.pads[Profile.LEFT]:
						self.eeval(self.profile.pads[Profile.LEFT][x], self.lpe[x].GLOBS, self.lpe[x].locs)
		
		
		# Generate events
		if len(self.keypress_list):
			self.keyboard.pressEvent(self.keypress_list)
			self.keypress_list = []
		if len(self.keyrelease_list):
			self.keyboard.releaseEvent(self.keyrelease_list)
			self.keyrelease_list = []
		if len(self.syn_list):
			for dev in self.syn_list:
				dev.synEvent()
			self.syn_list = set()
