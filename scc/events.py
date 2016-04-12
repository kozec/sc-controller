#!/usr/bin/env python2
"""
SC Controller - Events.

Event represents event from physical controller button, stick, pad or trigger
and it is used as context in which Action is done.
That means that same action can have different meaning depending on event which
caused it to run.
For example, 'button' action caused by ButtonPressEvent translates directly
to button press while with StickEvent it be configured to press different
buttons for each direction in which stick can be moved.
"""
from scc.uinput import Keys, Axes, Rels
from scc.actions import MOUSE_BUTTONS, ACTIONS
from collections import deque

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


class ControllerEvent(object):
	# Used as globals when executing code from 'python' action
	GLOBS = {
		'Keys' : Keys,
		'Axes' : Axes,
		'Rels' : Rels
	}
	
	
	def __init__(self, mapper):
		self.mapper = mapper
		# Used as locals when executing code from 'python' action
		self.locs = { x : getattr(self, x) for x in ACTIONS }
		self.locs['mapper'] = mapper
	
	
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
	
	hatleft = hatup
	hatright = hatdown


class ButtonPressEvent(ControllerEvent):
	def key(self, key1, *a):
		self.mapper.keypress_list.append(key1)
		return True
	
	
	def button(self, button1, *a):
		if button1 in MOUSE_BUTTONS:
			self.mapper.mouse.keyEvent(button1, 1)
			self.mapper.syn_list.add(self.mapper.mouse)
		else:
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


class ButtonReleaseEvent(ControllerEvent):
	def key(self, key1, *a):
		self.mapper.keyrelease_list.append(key1)
		return False
	
	def button(self, button1, *a):
		if button1 in MOUSE_BUTTONS:
			self.mapper.mouse.keyEvent(button1, 0)
			self.mapper.syn_list.add(self.mapper.mouse)
		else:
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


class StickEvent(ControllerEvent):
	def __init__(self, mapper, axis_attr, axis2_attr, click_button):
		ControllerEvent.__init__(self, mapper)
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
			dev = self.mapper.mouse if button1 in MOUSE_BUTTONS else self.mapper.gamepad
			if pressed:
				dev.keyEvent(button, 1)
				rv = True
			else:
				dev.keyEvent(button, 0)
			self.mapper.syn_list.add(dev)
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
					rv = locals()[self.dpad_state[i]].execute(self.mapper.bre)
				self.dpad_state[i] = None
			if side[i] is not None and side[i] != self.dpad_state[i]:
				if locals()[side[i]] is not None:
					rv = locals()[side[i]].execute(self.mapper.bpe)
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


class TriggerEvent(ControllerEvent):
	def __init__(self, mapper, axis_attr):
		ControllerEvent.__init__(self, mapper)
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
			dev = self.mapper.mouse if button1 in MOUSE_BUTTONS else self.mapper.gamepad
			if pressed:
				dev.keyEvent(button, 1)
				rv = True
			else:
				dev.keyEvent(button, 0)
			self.mapper.syn_list.add(dev)
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
