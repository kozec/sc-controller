#!/usr/bin/env python2
"""
SC Controller - Actions

Action describes what should be done when event from physical controller button,
stick, pad or trigger is generated - typicaly what emulated button, stick or
trigger should be pressed.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.tools import strip_none, ensure_size, quat2euler
from scc.tools import anglediff, circle_to_square, clamp
from scc.uinput import Keys, Axes, Rels
from scc.lib import xwrappers as X
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX, STICK_PAD_MIN_HALF
from scc.constants import STICK_PAD_MAX_HALF, TRIGGER_MIN, TRIGGER_HALF
from scc.constants import LEFT, RIGHT, STICK, PITCH, YAW, ROLL
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import TRIGGER_CLICK, TRIGGER_MAX
from math import sqrt, atan2

import time, logging
log = logging.getLogger("Actions")

# Default delay after action, if used in macro. May be overriden using sleep() action.
DEFAULT_DELAY = 0.01
MOUSE_BUTTONS = ( Keys.BTN_LEFT, Keys.BTN_MIDDLE, Keys.BTN_RIGHT, Keys.BTN_SIDE, Keys.BTN_EXTRA )
GAMEPAD_BUTTONS = ( Keys.BTN_A, Keys.BTN_B, Keys.BTN_X, Keys.BTN_Y, Keys.BTN_TL, Keys.BTN_TR,
		Keys.BTN_SELECT, Keys.BTN_START, Keys.BTN_MODE, Keys.BTN_THUMBL, Keys.BTN_THUMBR )
TRIGGERS = ( Axes.ABS_Z, Axes.ABS_RZ )


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
	AC_OSD		= 1 << 8
	AC_OSK		= 1 << 9	# On screen keyboard
	AC_MENU		= 1 << 10	# Menu Item
	#		bit 	09876543210
	AC_ALL		= 0b10111111111	# ALL means everything but OSK
	
	def __init__(self, *parameters):
		self.parameters = parameters
		self.name = None
		self.delay_after = DEFAULT_DELAY
		# internal, insignificant and never saved value used only by editor.
		# Has to be set to iterable of callbacks to do something usefull;
		# Callbacks in lilst are called with cb(app, action) after action is
		# set while editting the profile.
		self.on_action_set = None
	
	def encode(self):
		""" Called from json encoder """
		rv = { 'action' : self.to_string() }
		if self.name: rv['name'] = self.name
		return rv
	
	def __str__(self):
		return "<Action '%s', %s>" % (self.COMMAND, self.parameters)
	
	__repr__ = __str__
	
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
	
	
	def set_name(self, name):
		""" Sets display name of action. Returns self. """
		self.name = name
		return self
	
	
	def strip(self):
		"""
		For modifier, returns first child action that actually
		does something (first non-modifier).
		For everything else, returns itself.
		
		Used only to determine effective action type in editor.
		"""
		return self
	
	
	def compress(self):
		"""
		For most of actions, returns itself.
		
		For few special cases, like FeedbackModifier and SensitivityModifier,
		returns child action.
		
		Called after profile is loaded and feedback/sensitivity settings are
		applied, when original modifier doesn't do anything anymore.
		"""
		return self
	
	
	def set_haptic(self, hapticdata):
		"""
		Set haptic feedback settings for this action, if supported.
		Returns True if action supports haptic feedback.
		
		'hapticdata' has to be HapticData instance.
		Called by HapticModifier.
		"""
		return False
	
	
	def set_speed(self, x, y, z):
		"""
		Set speed multiplier (sensitivity) for this action, if supported.
		Returns True if action supports setting this.
		
		Called by SensitivityModifier
		"""
		return False
	
	
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
		return self.axis(mapper, position, what)
	
	
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


class HapticEnabledAction(object):
	""" Action that can generate haptic feedback """
	def __init__(self):
		self.haptic = None
	
	
	def set_haptic(self, hd):
		self.haptic = hd
		return True


class OSDEnabledAction(object):
	""" Action that displays some sort of OSD when executed """
	def __init__(self):
		self.osd_enabled = False
	
	
	def enable_osd(self, timeout):
		# timeout not used by anything so far
		self.osd_enabled = True


class SpecialAction(object):
	"""
	Action that needs to call special_actions_handler (aka sccdaemon instance)
	to actually do something.
	"""
	SA = ""
	def execute_named(self, name, mapper, *a):
		sa = mapper.get_special_actions_handler()
		h_name = "on_sa_%s" % (name,)
		if sa is None:
			log.warning("Mapper can't handle special actions (set_special_actions_handler never called)")
		elif hasattr(sa, h_name):
			return getattr(sa, h_name)(mapper, self, *a)
		else:
			log.warning("Mapper can't handle '%s' action" % (name,))
	
	def execute(self, mapper, *a):
		self.execute_named(self.SA, mapper, *a)
	
	# Prevent warnings when special action is bound to button
	def button_press(self, mapper): pass
	def button_release(self, mapper): pass


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
		self.speed = 1.0
		self._old_pos = 0
		if self.id in TRIGGERS:
			self.min = TRIGGER_MIN if min is None else min
			self.max = TRIGGER_MAX if max is None else max
		else:
			self.min = STICK_PAD_MIN if min is None else min
			self.max = STICK_PAD_MAX if max is None else max
	
	
	def set_speed(self, x, y, z):
		self.speed = x
		return True	
	
	
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
		p = float(position * self.speed - STICK_PAD_MIN) / (STICK_PAD_MAX - STICK_PAD_MIN)
		p = int((p * (self.max - self.min)) + self.min)
		mapper.gamepad.axisEvent(self.id, clamp_axis(self.id, p))
		mapper.syn_list.add(mapper.gamepad)
	
	
	def change(self, mapper, dx, dy):
		""" Called from BallModifier """
		self.axis(mapper, clamp(STICK_PAD_MIN, dx, STICK_PAD_MAX), None)
	
	
	def trigger(self, mapper, position, old_position):
		p = float(position * self.speed - TRIGGER_MIN) / (TRIGGER_MAX - TRIGGER_MIN)
		p = int((p * (self.max - self.min)) + self.min)
		mapper.gamepad.axisEvent(self.id, clamp_axis(self.id, p))
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
		HatAction.__init__(self, id, 0, STICK_PAD_MAX - 1)
	
class HatDownAction(HatAction):
	COMMAND = "hatdown"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MIN + 1)

class HatLeftAction(HatAction):
	COMMAND = "hatleft"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MAX - 1)
	
class HatRightAction(HatAction):
	COMMAND = "hatright"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MIN + 1)


class MouseAction(HapticEnabledAction, Action):
	COMMAND = "mouse"
	
	def __init__(self, axis=None, speed=None):
		Action.__init__(self, *strip_none(axis, speed))
		HapticEnabledAction.__init__(self)
		self._mouse_axis = axis
		self._old_pos = None
		self._travelled = 0
		if speed:
			self.speed = (speed, speed)
		else:
			self.speed = (1.0, 1.0)
	
	
	def set_speed(self, x, y, z):
		self.speed = (x, y)
		return True
	
	
	def describe(self, context):
		if self.name: return self.name
		if self._mouse_axis == Rels.REL_WHEEL:
			return _("Wheel")
		elif self._mouse_axis == Rels.REL_HWHEEL:
			return _("Horizontal Wheel")
		elif self._mouse_axis in (PITCH, YAW, ROLL, None):
			return _("Mouse")
		else:
			return _("Mouse %s") % (self._mouse_axis.name.split("_", 1)[-1],)
	
	
	def button_press(self, mapper):
		# This is generaly bad idea...
		self.change(mapper, 1, 0)
	
	
	def button_release(self, mapper):
		# Nothing
		pass
	
	
	def axis(self, mapper, position, what):
		self.change(mapper, position, 0)
		mapper.force_event.add(FE_STICK)
	
	
	def pad(self, mapper, position, what):
		if mapper.is_touched(what):
			if self._old_pos and mapper.was_touched(what):
				d = position - self._old_pos[0]
				self.change(mapper, d, 0)
			self._old_pos = position, 0
		else:
			# Pad just released
			self._old_pos = None
	
	
	def change(self, mapper, dx, dy):
		""" Called from BallModifier """
		if self.haptic:
			distance = sqrt(dx * dx + dy * dy)
			if distance > self.haptic.frequency / 10.0:
				self._travelled += distance
				if self._travelled > self.haptic.frequency:
					self._travelled = 0
					mapper.send_feedback(self.haptic)
		dx, dy = dx * self.speed[0], dy * self.speed[1]
		if self._mouse_axis is None:
			mapper.mouse.moveEvent(dx, dy)
		elif self._mouse_axis == Rels.REL_X:
			mapper.mouse_move(dx, 0)
		elif self._mouse_axis == Rels.REL_Y:
			mapper.mouse_move(0, dx)
		elif self._mouse_axis == Rels.REL_WHEEL:
			mapper.mouse_wheel(0, dx)
		elif self._mouse_axis == Rels.REL_HWHEEL:
			mapper.mouse_wheel(dx, 0)
	
	
	def whole(self, mapper, x, y, what):
		if what == STICK:
			mapper.mouse_move(x * self.speed[0] * 0.01, y * self.speed[1] * 0.01)
			mapper.force_event.add(FE_STICK)
		else:	# left or right pad
			if mapper.is_touched(what):
				if self._old_pos and mapper.was_touched(what):
					dx, dy = x - self._old_pos[0], self._old_pos[1] - y
					self.change(mapper, dx, dy)
				self._old_pos = x, y
			else:
				# Pad just released
				self._old_pos = None
	
	
	def gyro(self, mapper, pitch, yaw, roll, *a):
		if self._mouse_axis == YAW:
			mapper.mouse_move(yaw * -self.speed[0], pitch * -self.speed[1])
		else:
			mapper.mouse_move(roll * -self.speed[0], pitch * -self.speed[1])


class CircularAction(HapticEnabledAction, Action):
	COMMAND = "circular"
	
	def __init__(self, axis):
		Action.__init__(self, axis)
		HapticEnabledAction.__init__(self)
		self.mouse_axis = axis
		self.speed = 1.0
		self.angle = None		# Last known finger position
		self.travelled = 0
	
	
	def set_speed(self, x, y, z):
		self.speed = x
		return True
	
	
	def describe(self, context):
		if self.name: return self.name
		if self.mouse_axis == Rels.REL_WHEEL:
			return _("Circular Wheel")
		elif self.mouse_axis == Rels.REL_HWHEEL:
			return _("Circular Horizontal Wheel")
		return _("Circular Mouse %s") % (self.mouse_axis.name.split("_", 1)[-1],)
	
	
	def whole(self, mapper, x, y, what):
		distance = sqrt(x*x + y*y)
		if distance < STICK_PAD_MAX_HALF:
			# Finger lifted or too close to middle
			self.angle = None
			self.travelled = 0
		else:
			# Compute current angle
			angle = atan2(x, y)
			# Compute movement
			if self.angle is None:
				# Finger just touched the pad
				self.angle, angle = angle, 0
			else:
				self.angle, angle = angle, self.angle - angle
				# Ensure we don't wrap from pi to -pi creating a large delta
				if angle > PI:
					# Subtract a full rotation to counter the wrapping
					angle -= 2 * PI
				# And same from -pi to pi
				elif angle < -PI:
					# Add a full rotation to counter the wrapping
					angle += 2 * PI
			# Apply bulgarian constant
			self.travelled += angle * 5000
			if self.haptic:
				if abs(self.travelled) > self.haptic.frequency:
					mapper.send_feedback(self.haptic)
					self.travelled = 0
			angle *= 10000.0
			# Apply movement on axis
			if self.mouse_axis == Rels.REL_X:
				mapper.mouse.moveEvent(0, angle * self.speed)
			elif self.mouse_axis == Rels.REL_Y:
				mapper.mouse.moveEvent(1, angle * self.speed)
			elif self.mouse_axis == Rels.REL_HWHEEL:
				mapper.mouse.scrollEvent(0, angle * self.speed)
			elif self.mouse_axis == Rels.REL_WHEEL:
				mapper.mouse.scrollEvent(1, angle * self.speed)
			else:
				log.warning("Invalid axis for circular: %s", self.mouse_axis)
			mapper.force_event.add(FE_PAD)


class AreaAction(HapticEnabledAction, Action, SpecialAction, OSDEnabledAction):
	SA = COMMAND = "area"
	
	def __init__(self, x1, y1, x2, y2):
		Action.__init__(self, x1, y1, x2, y2)
		HapticEnabledAction.__init__(self)
		OSDEnabledAction.__init__(self)
		# Make sure that lower number is first - movement gets inverted otherwise
		if x2 < x1 : x1, x2 = x2, x1
		if y2 < y1 : y1, y2 = y2, y1
		# orig_position will store mouse position to return to when finger leaves pad
		self.orig_position = None
		self.coords = x1, y1, x2, y2
		# needs_query_screen is True if any coordinate has to be computed
		self.needs_query_screen = x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Mouse Region")
	
	
	def transform_coords(self, mapper):
		"""
		Transform coordinates specified as action arguments in whatever current
		class represents into rectangle in pixels.
		
		Overrided by subclasses.
		"""
		if self.needs_query_screen:
			screen = X.get_screen_size(mapper.get_xdisplay())
			x1, y1, x2, y2 = self.coords
			if x1 < 0 : x1 = screen[0] + x1
			if y1 < 0 : y1 = screen[1] + y1
			if x2 < 0 : x2 = screen[0] + x2
			if y2 < 0 : y2 = screen[1] + y2
			return x1, y1, x2, y2
		return self.coords
	
	
	def transform_osd_coords(self, mapper):
		"""
		Same as transform_coords, but returns coordinates in screen space even
		if action sets mouse position relative to window.
		
		Overrided by subclasses.
		"""
		return self.transform_coords(mapper)
	
	
	def set_mouse(self, mapper, x, y):
		"""
		Performs final mouse position setting.
		Overrided by subclasses.
		"""
		X.set_mouse_pos(mapper.get_xdisplay(), x, y)
	
	
	def update_osd_area(self, area, mapper):
		"""
		Updates area instance directly instead of calling daemon and letting
		it talking through socket.
		"""
		x1, y1, x2, y2 = self.transform_osd_coords(mapper)
		area.update(int(x1), int(y1), int(x2-x1), int(y2-y1))
	
	
	def whole(self, mapper, x, y, what):
		if mapper.is_touched(what):
			# Store mouse position if pad was just touched
			if self.orig_position is None:
				if self.osd_enabled:
					x1, y1, x2, y2 = self.transform_osd_coords(mapper)
					self.execute(mapper, int(x1), int(y1), int(x2), int(y2))
				self.orig_position = X.get_mouse_pos(mapper.get_xdisplay())
			# Compute coordinates specified from other side of screen if needed
			x1, y1, x2, y2 = self.transform_coords(mapper)
			# Transform position on circne to position on rectangle
			x = x / float(STICK_PAD_MAX)
			y = y / float(STICK_PAD_MAX)
			x, y = circle_to_square(x, y)
			# Perform magic
			x = max(0, (x + 1.0) * 0.5)
			y = max(0, (1.0 - y) * 0.5)
			w = float(x2 - x1)
			h = float(y2 - y1)
			x = int(x1 + w * x)
			y = int(y1 + h * y)
			# Set position
			self.set_mouse(mapper, x, y)
		elif mapper.was_touched(what):
			# Pad just released
			X.set_mouse_pos(mapper.get_xdisplay(), *self.orig_position)
			if self.osd_enabled:
				self.execute_named("clear_osd", mapper)
			self.orig_position = None


class RelAreaAction(AreaAction):
	COMMAND = "relarea"
	
	def transform_coords(self, mapper):
		screen = X.get_screen_size(mapper.get_xdisplay())
		x1, y1, x2, y2 = self.coords
		x1 = screen[0] * x1
		y1 = screen[1] * y1
		x2 = screen[0] * x2
		y2 = screen[1] * y2
		return x1, y1, x2, y2


class WinAreaAction(AreaAction):
	COMMAND = "winarea"
	
	def transform_coords(self, mapper):
		if self.needs_query_screen:
			w_size = X.get_window_size(mapper.get_xdisplay(), mapper.get_current_window())
			x1, y1, x2, y2 = self.coords
			if x1 < 0 : x1 = w_size[0] + x1
			if y1 < 0 : y1 = w_size[1] + y1
			if x2 < 0 : x2 = w_size[0] + x2
			if y2 < 0 : y2 = w_size[1] + y2
			return x1, y1, x2, y2
		return self.coords
	
	
	def transform_osd_coords(self, mapper):
		wx, wy, ww, wh = X.get_window_geometry(mapper.get_xdisplay(), mapper.get_current_window())
		x1, y1, x2, y2 = self.coords
		x1 = wx + x1 if x1 >= 0 else wx + ww + x1
		y1 = wy + y1 if y1 >= 0 else wy + wh + y1
		x2 = wx + x2 if x2 >= 0 else wx + ww + x2
		y2 = wy + y2 if y2 >= 0 else wy + wh + y2
		return x1, y1, x2, y2
	
	
	def set_mouse(self, mapper, x, y):
		X.set_mouse_pos(mapper.get_xdisplay(), x, y, mapper.get_current_window())


class RelWinAreaAction(WinAreaAction):
	COMMAND = "relwinarea"
	
	def transform_coords(self, mapper):
		w_size = X.get_window_size(mapper.get_xdisplay(), mapper.get_current_window())
		x1, y1, x2, y2 = self.coords
		x1 = w_size[0] * x1
		y1 = w_size[1] * y1
		x2 = w_size[0] * x2
		y2 = w_size[1] * y2
		return x1, y1, x2, y2
	
	
	def transform_osd_coords(self, mapper):
		wx, wy, ww, wh = X.get_window_geometry(mapper.get_xdisplay(), mapper.get_current_window())
		x1, y1, x2, y2 = self.coords
		x1 = wx + float(ww) * x1
		y1 = wy + float(wh) * y1
		x2 = wx + float(ww) * x2
		y2 = wy + float(wh) * y2
		return x1, y1, x2, y2


class GyroAction(Action):
	COMMAND = "gyro"
	
	def __init__(self, axis1, axis2=None, axis3=None):
		Action.__init__(self, axis1, *strip_none(axis2, axis3))
		self.axes = [ axis1, axis2, axis3 ]
		self.speed = (1.0, 1.0, 1.0)
	
	
	def set_speed(self, x, y, z):
		self.speed = (x, y, z)
		return True
	
	
	def gyro(self, mapper, *pyr):
		# p,y,r = quat2euler(sci.q1 / 32768.0, sci.q2 / 32768.0, sci.q3 / 32768.0, sci.q4 / 32768.0)
		# print "% 7.2f, % 7.2f, % 7.2f" % (p,y,r)
		# print sci.q1, sci.q2, sci.q3, sci.q4
		for i in (0, 1, 2):
			axis = self.axes[i]
			# 'gyro' cannot map to mouse, but 'mouse' does that.
			if axis in Axes:
				mapper.gamepad.axisEvent(axis, clamp_axis(axis, pyr[i] * self.speed[i] * -10))
				mapper.syn_list.add(mapper.gamepad)
	
	
	def describe(self, context):
		if self.name : return self.name
		rv = []
		
		for x in self.axes:
			if x:
				s = _(AxisAction.AXIS_NAMES[x][0])
				if s not in rv:
					rv.append(s)
		return "\n".join(rv)
	
	
	def _get_axis_description(self):
		axis, neg, pos = "%s %s" % (self.id.name, _("Axis")), _("Negative"), _("Positive")
		if self.id in AxisAction.AXIS_NAMES:
			axis, neg, pos = [ _(x) for x in AxisAction.AXIS_NAMES[self.id] ]
		return axis, neg, pos


class GyroAbsAction(HapticEnabledAction, GyroAction):
	COMMAND = "gyroabs"
	def __init__(self, *blah):
		GyroAction.__init__(self, *blah)
		HapticEnabledAction.__init__(self)
		self.haptic = None	# Can't call HapticEnabledAction, it'll create diamond
		self.ir = None
		self._was_oor = False
	
	
	def gyro(self, mapper, pitch, yaw, roll, q1, q2, q3, q4):
		pyr = list(quat2euler(q1 / 32768.0, q2 / 32768.0, q3 / 32768.0, q4 / 32768.0))
		if self.ir is None:
			# TODO: Move this to controller and allow some way to reset it
			self.ir = pyr[2]
		# Covert what quat2euler returns to what controller can use
		for i in (0, 1):
			pyr[i] = pyr[i] * (2**15) * self.speed[i] * 2 / PI
		pyr[2] = anglediff(self.ir, pyr[2]) * (2**15) * self.speed[2] * 2 / PI
		# Restrict to acceptablle range
		if self.haptic:
			oor = False # oor - Out Of Range
			for i in (0, 1, 2):
				pyr[i] = int(pyr[i])
				if pyr[i] > STICK_PAD_MAX:
					pyr[i] = STICK_PAD_MAX
					oor = True
				elif pyr[i] < STICK_PAD_MIN:
					pyr[i] = STICK_PAD_MIN
					oor = True
			if oor:
				if not self._was_oor:
					mapper.send_feedback(self.haptic)
					self._was_oor = True
			else:
				self._was_oor = False
		else:
			for i in (0, 1, 2):
				pyr[i] = int(clamp(STICK_PAD_MIN, pyr[i], STICK_PAD_MAX))
		# print "% 12.0f, % 12.0f, % 12.5f" % (p,y,r)
		for i in (0, 1, 2):
			axis = self.axes[i]
			if axis in Axes:
				mapper.gamepad.axisEvent(axis, clamp_axis(axis, pyr[i] * self.speed[i]))
				mapper.syn_list.add(mapper.gamepad)


class TrackballAction(Action):
	"""
	ball(trackpad); Never actually instantiated - Exists only to provide
	backwards compatibility
	"""
	COMMAND = "trackball"
	
	def __new__(cls, speed=None):
		from modifiers import BallModifier
		return BallModifier(MouseAction(speed=speed))


class ButtonAction(HapticEnabledAction, Action):
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
		Action.__init__(self, button1, *strip_none(button2, minustrigger, plustrigger))
		HapticEnabledAction.__init__(self)
		self.button = button1 or None
		self.button2 = button2 or None
		self.minustrigger = minustrigger
		self.plustrigger = plustrigger
		self._pressed_key = None
		self._released = True
	
	
	def describe(self, context):
		if self.name: return self.name
		elif self.button == Rels.REL_WHEEL:
			if len(self.parameters) < 2 or self.parameters[1] > 0:
				return _("Wheel UP")
			else:
				return _("Wheel DOWN")
		else:
			rv = [ ]
			for x in (self.button, self.button2):
				if x:
					rv.append(ButtonAction.describe_button(x))
			return ", ".join(rv)
	
	
	@staticmethod
	def describe_button(button):
		if button in ButtonAction.SPECIAL_NAMES:
			return _(ButtonAction.SPECIAL_NAMES[button])
		elif button in MOUSE_BUTTONS:
			return _("Mouse %s") % (button,)
		elif button is None: # or isinstance(button, NoAction):
			return "None"
		return button.name.split("_", 1)[-1]
	
	
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
		if button in mapper.pressed and mapper.pressed[button] > 0:
			# Virtual button is already pressed - generate release event first
			pc = mapper.pressed[button]
			ButtonAction._button_release(mapper, button, immediate)
			# ... then inrease 'press counter' and generate press event as usual
			mapper.pressed[button] = pc + 1
		else:
			mapper.pressed[button] = 1
		
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
		if button in mapper.pressed:
			if mapper.pressed[button] > 1:
				# More than one action pressed this virtual button - decrease
				# counter, but don't release button yet
				mapper.pressed[button] -= 1
				return
			else:
				# This is last action that kept virtual button held
				del mapper.pressed[button]
		
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
		if self.haptic:
			mapper.send_feedback(self.haptic)
	
	
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
			elif x:
				self._add(x)
	
	
	def _add(self, action):
		if action.__class__ == self.__class__:	# I don't want subclasses here
			self._add_all(action.actions)
		else:
			self.actions.append(action)
	
	
	def compress(self):
		nw = [ x.compress() for x in self.actions ]
		self.actions = nw
		return self
	
	
	def set_haptic(self, hapticdata):
		supports = False
		for a in self.actions:
			if a:
				# Only first feedback-supporting action should do feedback
				supports = supports or a.set_haptic(hapticdata)
		return supports
	
	
	def set_speed(self, x, y, z):
		supports = False
		for a in self.actions:
			supports = a.set_speed(x, y, z) or supports
		return supports
	
	
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
	
	def pad(self, *p):
		for a in self.actions: a.pad(*p)
	
	def gyro(self, *p):
		for a in self.actions: a.gyro(*p)
	
	def whole(self, *p):
		for a in self.actions: a.whole(*p)
	
	def trigger(self, *p):
		for a in self.actions: a.trigger(*p)
	
	
	def to_string(self, multiline=False, pad=0):
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
	
	
	def compress(self):
		nw = [ x.compress() for x in self.actions ]
		self.actions = nw
		return self
	
	
	def encode(self):
		""" Called from json encoder """
		rv = { 'dpad' : [ x.encode() for x in self.actions ]}
		if self.name: rv['name'] = self.name
		return rv
	
	
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


class XYAction(HapticEnabledAction, Action):
	"""
	Used for sticks and pads when actions for X and Y axis are different.
	"""
	COMMAND = "XY"
	
	def __init__(self, x=None, y=None):
		Action.__init__(self, *strip_none(x, y))
		HapticEnabledAction.__init__(self)
		self.x = x or NoAction()
		self.y = y or NoAction()
		self.actions = (self.x, self.y)
		self._old_distance = 0
		self._travelled = 0
		if hasattr(self.x, "change") or hasattr(self.y, "change"):
			self.change = self._change
	
	
	def compress(self):
		self.x = self.x.compress()
		self.y = self.y.compress()
		return self
	
	
	def set_haptic(self, hapticdata):
		supports = False
		supports = self.x.set_haptic(hapticdata) or supports
		supports = self.y.set_haptic(hapticdata) or supports
		if not supports:
			# Child action has no feedback support, do feedback here
			self.haptic = hapticdata
			self.big_click = hapticdata * 4
			return True
		return supports
	
	
	def set_speed(self, x, y, z):
		supports = False
		supports = self.x.set_speed(x, 1, 1) or supports
		supports = self.y.set_speed(y, 1, 1) or supports
		return supports
	
	
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
	
	
	def _haptic(self, mapper, x, y):
		"""
		Common part of _change and whole - sends haptic output, if enabled
		"""
		# Compute travelled distance and send 'small clicks' when user moves
		# finger around the pad.
		# Also, if user moves finger over circle around 2/3 area of pad,
		# send one 'big click'.
		distance = sqrt(x*x + y*y)
		self._travelled += abs(self._old_distance - distance)
		is_close = distance > STICK_PAD_MAX * 2 / 3
		was_close = self._old_distance > STICK_PAD_MAX * 2 / 3
		if is_close != was_close:
			mapper.send_feedback(self.big_click)
		elif self._travelled > self.haptic.frequency:
			self._travelled = 0
			mapper.send_feedback(self.haptic)
		self._old_distance = distance
	
	
	def _change(self, mapper, x, y):
		""" Not always available """
		if hasattr(self.x, "change"):
			self.x.change(mapper, x, 0)
		if hasattr(self.y, "change"):
			self.y.change(mapper, -y, 0)
		if self.haptic:
			self._haptic(mapper, x, y)
	
	
	def whole(self, mapper, x, y, what):
		if self.haptic:
			self._haptic(mapper, x, y)
		if what in (LEFT, RIGHT):
			self.x.pad(mapper, x, what)
			self.y.pad(mapper, y, what)
		else:
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
			rv = [ (" " * pad) + "XY(" ]
			rv += self.x.to_string(True, pad + 2).split("\n")
			rv += [ (" " * pad) + "," ]
			rv += self.y.to_string(True, pad + 2).split("\n")
			rv += [ (" " * pad) + ")" ]
			return "\n".join(rv)
		elif self.y:
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


def clamp_axis(id, value):
	""" Returns value clamped between min/max allowed for axis """
	if id in (Axes.ABS_Z, Axes.ABS_RZ):
		# Triggers
		return int(max(TRIGGER_MIN, min(TRIGGER_MAX, value)))
	if id in (Axes.ABS_HAT0X, Axes.ABS_HAT0Y):
		# DPAD
		return int(max(-1, min(1, value)))
	# Everything else
	return int(max(STICK_PAD_MIN, min(STICK_PAD_MAX, value)))


# Generate dict of { 'actionname' : ActionClass } for later use
ACTIONS = {
	globals()[x].COMMAND : globals()[x]
	for x in dir()
	if hasattr(globals()[x], 'COMMAND')
	and globals()[x].COMMAND is not None
}
ACTIONS["None"] = NoAction
ACTIONS["trackpad"] = MouseAction

import scc.macros
import scc.modifiers
import scc.special_actions
