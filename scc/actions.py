#!/usr/bin/env python2
"""
SC Controller - Actions

Action describes what should be done when event from physical controller button,
stick, pad or trigger is generated - typicaly what emulated button, stick or
trigger should be pressed.
"""
from __future__ import unicode_literals

from scc.tools import strip_none, ensure_size, quat2euler, anglediff, _
from scc.uinput import Keys, Axes, Rels
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import LEFT, RIGHT, STICK, PITCH, YAW, ROLL
from math import pi as PI

import time, logging
log = logging.getLogger("Actions")

MOUSE_BUTTONS = ( Keys.BTN_LEFT, Keys.BTN_MIDDLE, Keys.BTN_RIGHT, Keys.BTN_SIDE, Keys.BTN_EXTRA )
GAMEPAD_BUTTONS = ( Keys.BTN_A, Keys.BTN_B, Keys.BTN_X, Keys.BTN_Y, Keys.BTN_TL, Keys.BTN_TR,
		Keys.BTN_SELECT, Keys.BTN_START, Keys.BTN_MODE, Keys.BTN_THUMBL, Keys.BTN_THUMBR )
TRIGGERS = ( Axes.ABS_Z, Axes.ABS_RZ )
STICK_PAD_MIN = -32767
STICK_PAD_MAX = 32767
STICK_PAD_MIN_HALF = STICK_PAD_MIN / 3
STICK_PAD_MAX_HALF = STICK_PAD_MAX / 3

TRIGGER_MIN = 0
TRIGGER_HALF = 50
TRIGGER_CLICK = 254 # Values under this are generated until trigger clicks
TRIGGER_MAX = 255

# Default delay after action, if used in macro. May be overriden using sleep() action.
DEFAULT_DELAY = 0.01

class Action(object):
	"""
	Simple action that executes one of predefined methods.
	See ACTIONS for list of them.
	"""
	# Used everywhere to convert strings to Action classes and back
	COMMAND = None
	
	# "Action Context" constants
	AC_BUTTON	= 1 << 0
	AC_STICK	= 1 << 2
	AC_TRIGGER	= 1 << 3
	AC_GYRO		= 1 << 4
	AC_PAD		= 1 << 5
	AC_ALL		= 0b11111111
	
	def __init__(self, *parameters):
		self.parameters = parameters
		self.name = None
		self.delay_after = DEFAULT_DELAY
	
	
	def describe(self, context):
		"""
		Returns string that describes what action does in human-readable form.
		Used in GUI.
		"""
		if self.name: return self.name
		return str(self)
	
	
	def to_string(self, multiline=False, pad=0):
		""" Converts action back to string """
		return (" " * pad) + "%s(%s)" % (self.COMMAND, ", ".join([
			x.to_string() if isinstance(x, Action) else str(x)
			for x in self.parameters
		]))
	
	
	def button_press(self, mapper):
		"""
		Called when action is executed by pressing physical gamepad button.
		'button_release' will be called later.
		"""
		log.warn("Action %s can't handle button press event", self.__class__.__name__)
	
	
	def button_release(self, mapper):
		"""
		Called when action executed by pressing physical gamepad button is
		expected to stop.
		"""
		log.warn("Action %s can't handle button release event", self.__class__.__name__)
	
	
	def axis(self, mapper, position, what):
		"""
		Called when action is executed by moving physical stickm when
		stick has different actions for different axes defined.
		
		'position' contains current stick position on updated axis.
		'what' is one of LEFT, RIGHT or STICK (from scc.constants),
		describing what is being updated
		"""
		log.warn("Action %s can't handle axis event", self.__class__.__name__)
	
	
	def pad(self, mapper, position, what):
		"""
		Called when action is executed by touching physical pad,
		when pad has different actions for different axes defined.
		
		'position' contains current finger position on updated axis.
		'what' is either LEFT or RIGHT (from scc.constants), describing which pad is updated
		
		'pad' calls 'axis' by default
		"""
		pass
	pad = axis
	
	
	def gyro(self, mapper, pitch, yaw, roll, q1, q2, q3, q4):
		"""
		Called when action is set by rotating gyroscope.
		'pitch', 'yaw' and 'roll' represents change in gyroscope rotations.
		'q1' to 'q4' represents current rotations expressed as quaterion.
		"""
		pass
	
	
	def whole(self, mapper, x, y, what):
		"""
		Called when action is executed by moving physical stick or touching
		physical pad, when one action is defined for whole pad or stick.
		
		'x' and 'y' contains current stick or finger position.
		'what' is one of LEFT, RIGHT, STICK (from scc.constants), describing what is
		being updated
		"""
		log.warn("Action %s can't handle whole stick event", self.__class__.__name__)
	
	
	def trigger(self, mapper, position, old_position):
		"""
		Called when action is executed by pressing (or releasing) physical
		trigger.
		
		'position' contains current trigger position.
		'old_position' contains last known trigger position.
		"""
		log.warn("Action %s can't handle trigger event", self.__class__.__name__)
	
	
	def encode(self):
		""" Called from json encoder """
		rv = { 'action' : self.to_string() }
		if self.name: rv['name'] = self.name
		return rv
	
	
	def __str__(self):
		return "<Action '%s', %s>" % (self.COMMAND, self.parameters)
	
	__repr__ = __str__


class AxisAction(Action):
	COMMAND = "axis"
	
	AXIS_NAMES = {
		Axes.ABS_X : ("LStick", "Left", "Right"),
		Axes.ABS_Y : ("LStick", "Up", "Down"),
		Axes.ABS_RX : ("RStick", "Left", "Right"),
		Axes.ABS_RY : ("RStick", "Up", "Down"),
		Axes.ABS_HAT0X : ("DPAD", "Left", "Right"),
		Axes.ABS_HAT0Y : ("DPAD", "Up", "Down"),
		Axes.ABS_Z  : ("Left Trigger", "Press", "Press"),
		Axes.ABS_RZ : ("Right Trigger", "Press", "Press"),
	}
	X = [ Axes.ABS_X, Axes.ABS_RX, Axes.ABS_HAT0X ]
	Z = [ Axes.ABS_Z, Axes.ABS_RZ ]
	
	def __init__(self, id, min = None, max = None):
		Action.__init__(self, id, *strip_none(min, max))
		self.id = id
		if self.id in TRIGGERS:
			self.min = TRIGGER_MIN if min is None else min
			self.max = TRIGGER_MAX if max is None else max
		else:
			self.min = STICK_PAD_MIN if min is None else min
			self.max = STICK_PAD_MAX if max is None else max
	
	
	def _get_axis_description(self):
		axis, neg, pos = "%s %s" % (self.id.name, _("Axis")), _("Negative"), _("Positive")
		if self.id in AxisAction.AXIS_NAMES:
			axis, neg, pos = [ _(x) for x in AxisAction.AXIS_NAMES[self.id] ]
		return axis, neg, pos
	
	def describe(self, context):
		if self.name: return self.name
		axis, neg, pos = self._get_axis_description()
		if context == Action.AC_BUTTON:
			for x in self.parameters:
				if type(x) in (int, float):
					if x > 0:
						return "%s %s" % (axis, pos)
					if x < 0:
						return "%s %s" % (axis, neg)
		if context in (Action.AC_TRIGGER, Action.AC_STICK, Action.AC_PAD):
			if self.id in AxisAction.Z: # Trigger
				return axis
			else:
				xy = "X" if self.id in AxisAction.X else "Y"
				return "%s %s" % (axis, xy)
		return axis
	
	
	def button_press(self, mapper):
		mapper.gamepad.axisEvent(self.id, self.max)
		mapper.syn_list.add(mapper.gamepad)
	
	
	def button_release(self, mapper):
		mapper.gamepad.axisEvent(self.id, self.min)
		mapper.syn_list.add(mapper.gamepad)
	
	
	def axis(self, mapper, position, what):
		p = float(position - STICK_PAD_MIN) / (STICK_PAD_MAX - STICK_PAD_MIN)
		p = int((p * (self.max - self.min)) + self.min)
		mapper.gamepad.axisEvent(self.id, p)
		mapper.syn_list.add(mapper.gamepad)
	
	
	def trigger(self, mapper, position, old_position):
		p = float(position - TRIGGER_MIN) / (TRIGGER_MAX - TRIGGER_MIN)
		p = int((p * (self.max - self.min)) + self.min)
		mapper.gamepad.axisEvent(self.id, p)
		mapper.syn_list.add(mapper.gamepad)


class RAxisAction(AxisAction):
	COMMAND = "raxis"
	
	def __init__(self, id, min = None, max = None):
		AxisAction.__init__(self, id, min, max)
		self.min, self.max = self.max, self.min
	
	
	def describe(self, context):
		if self.name: return self.name
		axis, neg, pos = self._get_axis_description()
		if context in (Action.AC_STICK, Action.AC_PAD):
			xy = "X" if self.parameters[0] in AxisAction.X else "Y"
			return _("%s %s (reversed)") % (axis, xy)
		return _("Reverse %s Axis") % (axis,)


class HatAction(AxisAction):
	COMMAND = None
	def describe(self, context):
		if self.name: return self.name
		axis, neg, pos = self._get_axis_description()
		if "up" in self.COMMAND or "left" in self.COMMAND:
			return "%s %s" % (axis, neg)
		else:
			return "%s %s" % (axis, pos)

class HatUpAction(HatAction):
	COMMAND = "hatup"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MAX)
	
class HatDownAction(HatAction):
	COMMAND = "hatdown"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MIN)

class HatLeftAction(HatAction):
	COMMAND = "hatleft"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MAX)
	
class HatRightAction(HatAction):
	COMMAND = "hatright"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MIN)


class MouseAction(Action):
	COMMAND = "mouse"
	
	def __init__(self, axis, speed=None):
		Action.__init__(self, axis, *strip_none(speed))
		self.mouse_axis = axis
		self.speed = speed or 1
	
	
	def describe(self, context):
		if self.name: return self.name
		if self.parameters[0] == Rels.REL_WHEEL:
			return _("Wheel")
		elif self.parameters[0] == Rels.REL_HWHEEL:
			return _("Horizontal Wheel")
		elif self.parameters[0] in (PITCH, YAW, ROLL):
			return _("Mouse")
		else:
			return _("Mouse %s") % (self.parameters[0].name.split("_", 1)[-1],)
	
	
	def button_press(self, mapper):
		# This is generaly bad idea...
		if self.mouse_axis == Rels.REL_X:
			mapper.mouse.moveEvent(1000 * self.speed, 0, False)
			mapper.syn_list.add(mapper.mouse)
		elif self.mouse_axis == Rels.REL_Y:
			mapper.mouse.moveEvent(0, 1000 * self.speed, False)
			mapper.syn_list.add(mapper.mouse)
		elif self.mouse_axis == Rels.REL_WHEEL:
			mapper.mouse.scrollEvent(0, 2000 * self.speed, False)
			mapper.syn_list.add(mapper.mouse)
	
	
	def button_release(self, mapper):
		# Nothing
		pass
	
	
	def axis(self, mapper, position, what):
		p = position * self.speed / 100
		
		if self.mouse_axis == Rels.REL_X:
			# This is generaly bad idea for stick...
			mapper.mouse.moveEvent(p, 0, False)
			mapper.syn_list.add(mapper.mouse)
		elif self.mouse_axis == Rels.REL_Y:
			# ... this as well...
			mapper.mouse.moveEvent(0, -p, False)
			mapper.syn_list.add(mapper.mouse)
		elif self.mouse_axis == Rels.REL_WHEEL:
			# ... but this should kinda work
			mapper.mouse.scrollEvent(0, p * self.speed * 2.0, False)
			mapper.syn_list.add(mapper.mouse)
		elif self.mouse_axis == Rels.REL_HWHEEL:
			# and this as well
			mapper.mouse.scrollEvent(p * self.speed * 2.0, 0, False)
			mapper.syn_list.add(mapper.mouse)
		mapper.force_event.add(FE_STICK)
	
	
	def pad(self, mapper, position, what):
		if mapper.is_touched(what):
			if not mapper.was_touched(what):
				# Pad was just pressed
				if self.mouse_axis in (Rels.REL_X, Rels.REL_Y):
					mapper.do_trackball(0, True)
				elif self.mouse_axis in (Rels.REL_WHEEL, Rels.REL_HWHEEL):
					mapper.do_trackball(1, True)
			if self.mouse_axis == Rels.REL_X:
				mapper.mouse_dq_add(0, position, -self.speed)
			elif self.mouse_axis == Rels.REL_Y:
				mapper.mouse_dq_add(1, position, -self.speed)
			elif self.mouse_axis == Rels.REL_HWHEEL:
				mapper.mouse_dq_add(2, position, -self.speed)
			elif self.mouse_axis == Rels.REL_WHEEL:
				mapper.mouse_dq_add(3, position, -self.speed)
			mapper.force_event.add(FE_PAD)
				
		elif mapper.was_touched(what):
			# Pad was just released
			if self.mouse_axis in (Rels.REL_X, Rels.REL_Y):
				mapper.do_trackball(0, False)
			elif self.mouse_axis in (Rels.REL_WHEEL, Rels.REL_HWHEEL):
				mapper.do_trackball(1, False)
			if self.mouse_axis == Rels.REL_X:
				mapper.mouse_dq_clear(0)
			elif self.mouse_axis == Rels.REL_Y:
				mapper.mouse_dq_clear(1)
			elif self.mouse_axis == Rels.REL_WHEEL:
				mapper.mouse_dq_clear(3)
			elif self.mouse_axis == Rels.REL_HWHEEL:
				mapper.mouse_dq_clear(2)
	
	
	def whole(self, mapper, x, y, what):
		mapper.mouse.moveEvent(x * self.speed * 0.01, y * self.speed * -0.01, False)
		mapper.syn_list.add(mapper.mouse)
		if what == STICK:
			mapper.force_event.add(FE_STICK)
	
	
	def gyro(self, mapper, pitch, yaw, roll, *a):
		if self.mouse_axis == YAW:
			mapper.mouse.moveEvent(yaw * self.speed * -1, pitch * self.speed * -1, False)
		else:
			mapper.mouse.moveEvent(roll * self.speed * -1, pitch * self.speed * -1, False)
		mapper.syn_list.add(mapper.mouse)


class GyroAction(Action):
	COMMAND = "gyro"
	
	def __init__(self, axis1, axis2=None, axis3=None, speed=None):
		Action.__init__(self, axis1, *strip_none(axis2, axis3, speed))
		self.axes = [ axis1, axis2, axis3 ]
		self.speed = speed or 1
	
	
	def gyro(self, mapper, *pyr):
		# p,y,r = quat2euler(sci.q1 / 32768.0, sci.q2 / 32768.0, sci.q3 / 32768.0, sci.q4 / 32768.0)
		# print "% 7.2f, % 7.2f, % 7.2f" % (p,y,r)
		# print sci.q1, sci.q2, sci.q3, sci.q4
		for i in (0, 1, 2):
			axis = self.axes[i]
			# 'gyro' cannot map to mouse, but 'mouse' does that.
			if axis in Axes:
				mapper.gamepad.axisEvent(axis, pyr[i] * self.speed * -10)
				mapper.syn_list.add(mapper.gamepad)


class GyroAbsAction(GyroAction):
	COMMAND = "gyroabs"
	def __init__(self, *blah):
		GyroAction.__init__(self, *blah)
		self.ir = None
	
	def gyro(self, mapper, pitch, yaw, roll, q1, q2, q3, q4):
		pyr = list(quat2euler(q1 / 32768.0, q2 / 32768.0, q3 / 32768.0, q4 / 32768.0))
		if self.ir is None:
			# TODO: Move this to controller and allow some way to reset it
			self.ir = pyr[2]
		# Covert what quat2euler returns to what controller can use
		for i in (0, 1):
			pyr[i] = pyr[i] * (2**15) * 2 * self.speed / PI
		pyr[2] = anglediff(self.ir, pyr[2]) * (2**15) * 2 * self.speed / PI
		# Restrict to acceptablle range
		for i in (0, 1, 2):
			pyr[i] = int(max(min(pyr[i], 2**15), -(2**15)))
		# print "% 12.0f, % 12.0f, % 12.5f" % (p,y,r)
		for i in (0, 1, 2):
			axis = self.axes[i]
			if axis in Axes:
				mapper.gamepad.axisEvent(axis, pyr[i] * self.speed)
				mapper.syn_list.add(mapper.gamepad)


class TrackballAction(Action):
	COMMAND = "trackball"
	def __init__(self, speed=None):
		Action.__init__(self, speed)
		self.speed = speed or 1
		self.trackpadmode = False

	def describe(self, context):
		if self.name: return self.name
		return "Trackball"
	
	def whole(self, mapper, x, y, what):
		if mapper.is_touched(what):
			if not mapper.was_touched(what):
				# Pad was just pressed
				mapper.do_trackball(0, True)
			if x != 0.0 or y != 0.0:
				mapper.mouse_dq_add(0, x, self.speed)
				mapper.mouse_dq_add(1, y, self.speed)
			mapper.force_event.add(FE_PAD)
		elif mapper.was_touched(what):
			# Pad was just released
			mapper.mouse_dq_clear(0, 1)
			mapper.do_trackball(0, self.trackpadmode)


class TrackpadAction(TrackballAction):
	COMMAND = "trackpad"
	
	def __init__(self, speed=None):
		TrackballAction.__init__(self, speed)
		self.trackpadmode = True
	
	def describe(self, context):
		if self.name: return self.name
		return "Trackpad"


class ButtonAction(Action):
	COMMAND = "button"
	SPECIAL_NAMES = {
		Keys.BTN_LEFT	: "Mouse Left",
		Keys.BTN_MIDDLE	: "Mouse Middle",
		Keys.BTN_RIGHT	: "Mouse Right",
		Keys.BTN_SIDE	: "Mouse 8",
		Keys.BTN_EXTRA	: "Mouse 9",

		Keys.BTN_TR		: "Right Bumper",
		Keys.BTN_TL		: "Left Bumper",
		Keys.BTN_THUMBL	: "LStick Click",
		Keys.BTN_THUMBR	: "RStick Click",
		Keys.BTN_START	: "Start >",
		Keys.BTN_SELECT	: "< Select",
		Keys.BTN_A		: "A Button",
		Keys.BTN_B		: "B Button",
		Keys.BTN_X		: "X Button",
		Keys.BTN_Y		: "Y Button",
	}
	MODIFIERS_NAMES = {
		Keys.KEY_LEFTSHIFT	: "Shift",
		Keys.KEY_LEFTCTRL	: "Ctrl",
		Keys.KEY_LEFTMETA	: "Meta",
		Keys.KEY_LEFTALT	: "Alt",
		Keys.KEY_RIGHTSHIFT	: "Shift",
		Keys.KEY_RIGHTCTRL	: "Ctrl",
		Keys.KEY_RIGHTMETA	: "Meta",
		Keys.KEY_RIGHTALT	: "Alt"
	}
	
	def __init__(self, button1, button2 = None, minustrigger = None, plustrigger = None):
		if button1 is None:
			button1, button2 = button2, None
		Action.__init__(self, button1, *strip_none(button2, minustrigger, plustrigger))
		self.button = button1
		self.button2 = button2
		self.minustrigger = minustrigger
		self.plustrigger = plustrigger
		self._pressed_key = None
		self._released = True
	
	
	def describe(self, context):
		if self.name: return self.name
		if self.button in ButtonAction.SPECIAL_NAMES:
			return _(ButtonAction.SPECIAL_NAMES[self.button])
		elif self.button == Rels.REL_WHEEL:
			if len(self.parameters) < 2 or self.parameters[1] > 0:
				return _("Wheel UP")
			else:
				return _("Wheel DOWN")
		elif self.button in MOUSE_BUTTONS:
			return _("Mouse %s") % (self.button,)
		return self.button.name.split("_", 1)[-1]
	
	
	def describe_short(self):
		"""
		Used when multiple ButtonActions are chained together, for
		combinations like Alt+TAB
		"""
		if self.button in self.MODIFIERS_NAMES:
			# Modifiers are special case here
			return self.MODIFIERS_NAMES[self.button]
		return self.describe(Action.AC_BUTTON)
	
	
	@staticmethod
	def _button_press(mapper, button, immediate=False):
		if button in MOUSE_BUTTONS:
			mapper.mouse.keyEvent(button, 1)
			mapper.syn_list.add(mapper.mouse)
		elif button in GAMEPAD_BUTTONS:
			mapper.gamepad.keyEvent(button, 1)
			mapper.syn_list.add(mapper.gamepad)
		elif immediate:
			mapper.keyboard.keyEvent(button, 1)
			mapper.syn_list.add(mapper.keyboard)
		else:
			mapper.keypress_list.append(button)
	
	
	@staticmethod
	def _button_release(mapper, button, immediate=False):
		if button in MOUSE_BUTTONS:
			mapper.mouse.keyEvent(button, 0)
			mapper.syn_list.add(mapper.mouse)
		elif button in GAMEPAD_BUTTONS:
			mapper.gamepad.keyEvent(button, 0)
			mapper.syn_list.add(mapper.gamepad)
		elif immediate:
			mapper.keyboard.keyEvent(button, 0)
			mapper.syn_list.add(mapper.keyboard)
		else:
			mapper.keyrelease_list.append(button)
	
	
	def button_press(self, mapper):
		ButtonAction._button_press(mapper, self.button)
	
	
	def button_release(self, mapper):
		ButtonAction._button_release(mapper, self.button)
	
	
	def axis(self, mapper, position, what):
		# Choses which key or button should be pressed or released based on
		# current stick position.
		minustrigger = self.minustrigger or STICK_PAD_MIN_HALF
		
		if self._pressed_key == self.button and position > minustrigger:
			ButtonAction._button_release(mapper, self.button)
			self._pressed_key = None
		elif self._pressed_key != self.button and position <= minustrigger:
			ButtonAction._button_press(mapper, self.button)
			self._pressed_key = self.button
		if self.button2 is not None:
			plustrigger = self.plustrigger or STICK_PAD_MAX_HALF
			if self._pressed_key == self.button2 and position < plustrigger:
				ButtonAction._button_release(mapper, self.button2)
				self._pressed_key = None
			elif self._pressed_key != self.button2 and position >= plustrigger:
				ButtonAction._button_press(mapper, self.button2)
				self._pressed_key = self.button2
	
	
	def trigger(self, mapper, p, old_p):
		# Choses which key or button should be pressed or released based on
		# current trigger position.
		partial = self.minustrigger or TRIGGER_HALF
		full = self.plustrigger or TRIGGER_CLICK
		
		if self.button2 is None:
			if p >= partial and old_p < partial:
				ButtonAction._button_press(mapper, self.button)
			elif p < partial and old_p >= partial:
				ButtonAction._button_release(mapper, self.button)
		else:
			if p >= partial and p < full:
				if self._pressed_key != self.button and self._released:
					ButtonAction._button_press(mapper, self.button)
					self._pressed_key = self.button
					self._released = False
			else:
				if self._pressed_key == self.button:
					ButtonAction._button_release(mapper, self.button)
					self._pressed_key = None
			if p > full and old_p < full:
				if self._pressed_key != self.button2:
					if self._pressed_key is not None:
						ButtonAction._button_release(mapper, self._pressed_key)
					ButtonAction._button_press(mapper, self.button2)
					self._pressed_key = self.button2
					self._released = False
			else:
				if self._pressed_key == self.button2:
					ButtonAction._button_release(mapper, self.button2)
					self._pressed_key = None
		
		if p <= TRIGGER_MIN:
			self._released = True


class MultiAction(Action):
	"""
	Two or more actions executed at once.
	Generated when parsing 'and'
	"""
	COMMAND = None
	
	def __init__(self, *actions):
		self.actions = []
		self.name = None
		self._add_all(actions)
	
	
	def _add_all(self, actions):
		for x in actions:
			if type(x) == list:
				self._add_all(x)
			else:
				self._add(x)
	
	
	def _add(self, action):
		if action.__class__ == self.__class__:	# I don't want subclasses here
			self._add_all(action.actions)
		else:
			self.actions.append(action)
	
	
	def describe(self, context):
		if self.name: return self.name
		if isinstance(self.actions[0], ButtonAction):
			# Special case, key combination
			rv = []
			for a in self.actions:
				if isinstance(a, ButtonAction,):
					rv.append(a.describe_short())
			return "+".join(rv)
		return " and ".join([ x.describe(context) for x in self.actions ])
	
	
	def execute(self, event):
		rv = False
		for a in self.actions:
			rv = a.execute(event)
		return rv
	
	
	def button_press(self, *p):
		for a in self.actions: a.button_press(*p)
	
	def button_release(self, *p):
		for a in self.actions: a.button_release(*p)
	
	def axis(self, *p):
		for a in self.actions: a.axis(*p)
	
	def whole(self, *p):
		for a in self.actions: a.whole(*p)
	
	def trigger(self, *p):
		for a in self.actions: a.trigger(*p)
	
	
	def to_string(self, multiline=False, pad=0):
		if multiline:
			return "\n".join([ a.to_string(True, pad) for a in self.actions ])
		return (" " * pad) + " and ".join([ x.to_string() for x in self.actions ])
	
	
	def __str__(self):
		return "<[ %s ]>" % (" and ".join([ str(x) for x in self.actions ]), )
	
	__repr__ = __str__


class DPadAction(Action):
	COMMAND = "dpad"
	
	def __init__(self, *actions):
		Action.__init__(self, *actions)
		self.actions = ensure_size(4, actions)
		self.eight = False
		self.dpad_state = [ None, None, None ]	# X, Y, 8-Way pad
	
	def describe(self, context):
		if self.name: return self.name
		return "DPad"
	
	def to_string(self, multiline=False, pad=0):
		if multiline:
			rv = [ (" " * pad) + self.COMMAND + "(" ]
			pad += 2
			for a in self.actions:
				rv += [ a.to_string(True, pad) + ","]
			if rv[-1].endswith(","):
				rv[-1] = rv[-1][0:-1]
			pad -= 2
			rv += [ (" " * pad) + ")" ]
			return "\n".join(rv)
		return self.COMMAND + "(" + (", ".join([
			x.to_string() if x is not None else "None"
			for x in self.actions
		])) + ")"
	
	
	def whole(self, mapper, x, y, what):
		## dpad8(up, down, left, right, upleft, upright, downleft, downright)
		side = [ None, None ]
		if x <= STICK_PAD_MIN_HALF:
			side[0] = 2 # left
		elif x >= STICK_PAD_MAX_HALF:
			side[0] = 3 # right
		if y <= STICK_PAD_MIN_HALF:
			side[1] = 1 # down
		elif y >= STICK_PAD_MAX_HALF:
			side[1] = 0 # up
		
		if self.eight:
			if side[0] is None and side[1] is None:
				side = None
			elif side[0] is None:
				side = side[1]
			elif side[1] is None:
				side = side[0]
			else:
				side = 2 + side[1] * 2 + side[0]
			
			if side != self.dpad_state[2] and self.dpad_state[2] is not None:
				if self.actions[self.dpad_state[2]] is not None:
					self.actions[self.dpad_state[2]].button_release(mapper)
				self.dpad_state[2] = None
			if side is not None and side != self.dpad_state[2]:
				if self.actions[side] is not None:
					rv = self.actions[side].button_press(mapper)
				self.dpad_state[2] = side
		else:
			for i in (0, 1):
				if side[i] != self.dpad_state[i] and self.dpad_state[i] is not None:
					if self.actions[self.dpad_state[i]] is not None:
						self.actions[self.dpad_state[i]].button_release(mapper)
					self.dpad_state[i] = None
				if side[i] is not None and side[i] != self.dpad_state[i]:
					if self.actions[side[i]] is not None:
						self.actions[side[i]].button_press(mapper)
					self.dpad_state[i] = side[i]


class DPad8Action(DPadAction):
	COMMAND = "dpad8"

	def __init__(self, *actions):
		DPadAction.__init__(self, *actions)
		self.actions = ensure_size(8, actions)
		self.eight = True
	
	def describe(self, context):
		if self.name: return self.name
		return "8-Way DPad"


class XYAction(Action):
	"""
	Used for sticks and pads when actions for X and Y axis are different.
	"""
	COMMAND = "XY"
	
	def __init__(self, x=None, y=None):
		Action.__init__(self, *strip_none(x, y))
		self.actions = strip_none(x, y)
		self.x = x or NoAction()
		self.y = y or NoAction()
	
	# XYAction no sense with button and trigger-related events
	def button_press(self, *a):
		pass
	
	def button_release(self, *a):
		pass
	
	def trigger(self, *a):
		pass
	
	# XYAction is what calls axis
	def axis(self, *a):
		pass
	
	
	def whole(self, mapper, x, y, what):
		self.x.axis(mapper, x, what)
		self.y.axis(mapper, y, what)
	
	
	def pad(self, mapper, x, y, what):
		self.x.pad(mapper, sci.lpad_x, what)
		self.y.pad(mapper, sci.lpad_y, what)
	
	
	def describe(self, context):
		if self.name: return self.name
		rv = []
		if self.x: rv.append(self.x.describe(context))
		if self.y: rv.append(self.y.describe(context))
		if context in (Action.AC_STICK, Action.AC_PAD):
			return "\n".join(rv)
		return " ".join(rv)
	
	
	def to_string(self, multiline=False, pad=0):
		if multiline:
			rv = []
			i = 0
			for a in (self.x, self.y):
				if a:
					if i == 0:
						rv += [ "X:" ]
					elif i == 1:
						rv += [ "Y:" ]
					i += 1
					rv += [ "  " + x for x in a.to_string(True).split("\n") ]
			return "\n".join(rv)
		
		if self.y:
			return "XY(" + (", ".join([ x.to_string() for x in (self.x, self.y) ])) + ")"
		else:
			return "XY(" + self.x.to_string() + ")"
	
	
	def encode(self):
		""" Called from json encoder """
		rv = { }
		if self.x: rv["X"] = self.x.encode()
		if self.y: rv["Y"] = self.y.encode()
		if self.name: rv['name'] = self.name
		return rv
	
	
	def __str__(self):
		return "<XY %s >" % (", ".join([ str(x) for x in self.actions ]), )

	__repr__ = __str__


class NoAction(Action):
	"""
	Parsed from None.
	Singleton, treated as False in boolean ops.
	"""
	COMMAND = None
	_singleton = None
	
	def __new__(cls):
		if cls._singleton is None:
			cls._singleton = object.__new__(cls)
		return cls._singleton
	
	
	def __nonzero__(self):
		return False
	
	
	def encode(self):
		return { }
	
	
	def button_press(self, *a):
		pass
	
	def button_release(self, *a):
		pass
	
	def axis(self, *a):
		pass
	
	def whole(self, *a):
		pass
	
	def trigger(self, *a):
		pass
	
	
	def describe(self, context):
		return _("(not set)")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "None"
	
	
	def __str__(self):
		return "NoAction"

	__repr__ = __str__


# Generate dict of { 'actionname' : ActionClass } for later use
ACTIONS = {
	globals()[x].COMMAND : globals()[x]
	for x in dir()
	if hasattr(globals()[x], 'COMMAND')
	and globals()[x].COMMAND is not None
}
ACTIONS["None"] = NoAction

import scc.macros
import scc.modifiers
import scc.special_actions
