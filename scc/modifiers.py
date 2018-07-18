#!/usr/bin/env python2
"""
SC Controller - Modifiers

Modifier is Action that just sits between input and actual action, changing
way how resulting action works.
For example, click() modifier executes action only if pad is pressed.
"""
from __future__ import unicode_literals

from scc.actions import Action, MouseAction, XYAction, AxisAction, RangeOP
from scc.actions import NoAction, WholeHapticAction, HapticEnabledAction
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX, STICK_PAD_MAX_HALF
from scc.constants import FE_PAD, SCButtons, HapticPos, ControllerFlags
from scc.constants import CUT, ROUND, LINEAR, MINIMUM, FE_STICK, FE_TRIGGER
from scc.constants import TRIGGER_MAX, LEFT, CPAD, RIGHT, STICK
from scc.controller import HapticData
from scc.tools import nameof, clamp
from scc.uinput import Axes, Rels
from math import pi as PI, sqrt, copysign, atan2, sin, cos
from collections import OrderedDict, deque

import time, logging, inspect
log = logging.getLogger("Modifiers")
_ = lambda x : x

class Modifier(Action):
	def __init__(self, *params):
		Action.__init__(self, *params)
		params = list(params)
		for p in params:
			if isinstance(p, Action):
				self.action = p
				params.remove(p)
				break
		else:
			self.action = NoAction()
		self._mod_init(*params)
	
	
	def get_compatible_modifiers(self):
		return self.action.get_compatible_modifiers()
	
	
	def cancel(self, mapper):
		self.action.cancel(mapper)
	
	
	def get_child_actions(self):
		return (self.action, )
	
	
	def _mod_init(self):
		"""
		Initializes modifier with rest of parameters, after action parameter
		was taken from it and stored in self.action
		"""
		pass # not needed by default
	
	
	def _mod_to_string(self, params, multiline, pad):
		""" Adds action at end of params list and generates string """
		if multiline:
			childstr = self.action.to_string(True, pad + 2)
			if len(params) > 0:
				return "%s%s(%s,%s%s)" % (
					" " * pad,
					self.COMMAND,
					", ".join([ nameof(s) for s in params ]),
					'\n' if '\n' in childstr else ' ',
					childstr
				)
			return "%s%s(%s)" % ( " " * pad, self.COMMAND, childstr.strip() )
		childstr = self.action.to_string(False, pad)
		if len(params) > 0:
			return "%s%s(%s, %s)" % (
				" " * pad,
				self.COMMAND,
				", ".join([ nameof(s) for s in params ]),
				childstr
			)

		return "%s%s(%s)" % (
			" " * pad,
			self.COMMAND,
			childstr
		)
	
	
	def strip_defaults(self):
		"""
		Overrides Action.strip_defaults; Uses defaults from _mod_init instead
		of __init__, but does NOT include last of original parameters - action.
		"""
		argspec = inspect.getargspec(self.__class__._mod_init)
		required_count = len(argspec.args) - len(argspec.defaults) - 1
		l = list(self.parameters[0:-1])
		d = list(argspec.defaults)[0:len(l)]
		while len(d) and len(l) > required_count and d[-1] == l[-1]:
			d, l = d[:-1], l[:-1]
		return l
	
	
	def strip(self):
		return self.action.strip()
	
	
	def compress(self):
		if self.action:
			self.action = self.action.compress()
		return self
	
	
	def __str__(self):
		return "<Modifier '%s', %s>" % (self.COMMAND, self.action)
	
	__repr__ = __str__


class NameModifier(Modifier):
	"""
	Simple modifier that sets name for child action.
	Used internally.
	"""
	COMMAND = "name"
	
	def _mod_init(self, name):
		self.name = name
		if self.action:
			self.action.name = name
	
	
	@staticmethod
	def decode(data, a, *b):
		return a.set_name(data[NameModifier.COMMAND])
	
	
	def strip(self):
		rv = self.action.strip()
		rv.name = self.name
		return rv
	
	
	@staticmethod
	def unstrip(action):
		# Inversion of strip.
		# For action that has name, returns NameModifier wrapping around that
		# action. For everything else returns original action.
		if not isinstance(action, NameModifier):
			if action and action.name:
				return NameModifier(action.name, action)
		return action
	
	
	def compress(self):
		return self.strip()
	
	
	def describe(self, context):
		return self.name or self.to_string()
	
	
	def to_string(self, multiline=False, pad=0):
		return "%s(%s, %s)" % (
			self.COMMAND,
			repr(self.name).strip('u'),
			self.action.to_string(multiline, pad)
		)


class ClickModifier(Modifier):
	# TODO: Rename to 'clicked'
	COMMAND = "click"

	@staticmethod
	def decode(data, a, *b):
		return ClickModifier(a)


	def describe(self, context):
		if context in (Action.AC_STICK, Action.AC_PAD):
			return _("(if pressed)") + "\n" + self.action.describe(context)
		else:
			return _("(if pressed)") + " " + self.action.describe(context)


	def to_string(self, multiline=False, pad=0):
		if multiline:
			childstr = self.action.to_string(True, pad + 2)
			if "\n" in childstr:
				return "%s%s(\n%s\n%s)" % (
					" " * pad,
					self.COMMAND,
					childstr,
					" " * pad
				)
		return "%s(%s)" % (
			self.COMMAND,
			self.action.to_string()
		)


	def strip(self):
		return self.action.strip()


	def compress(self):
		self.action = self.action.compress()
		return self


	# For button press & co it's safe to assume that they are being pressed...
	def button_press(self, mapper):
		return self.action.button_press(mapper)

	def button_release(self, mapper):
		return self.action.button_release(mapper)

	def trigger(self, mapper, position, old_position):
		return self.action.trigger(mapper, position, old_position)


	def axis(self, mapper, position, what):
		if what in (STICK, LEFT) and mapper.is_pressed(SCButtons.LPAD):
			if what == STICK: mapper.force_event.add(FE_STICK)
			return self.action.axis(mapper, position, what)
		elif what in (STICK, LEFT) and mapper.was_pressed(SCButtons.LPAD):
			# Just released
			return self.action.axis(mapper, 0, what)
		elif what == CPAD and mapper.is_pressed(SCButtons.CPAD):
			return self.action.axis(mapper, position, what)
		elif what == CPAD and mapper.was_pressed(SCButtons.CPAD):
			# Just released
			return self.action.axis(mapper, 0, what)
		elif mapper.is_pressed(SCButtons.RPAD):
			# what == RIGHT, last option
			return self.action.axis(mapper, position, what)
		elif mapper.was_pressed(SCButtons.RPAD):
			# what == RIGHT, last option, Just released
			return self.action.axis(mapper, 0, what)


	def pad(self, mapper, position, what):
		if what == LEFT and mapper.is_pressed(SCButtons.LPAD):
			if what == STICK: mapper.force_event.add(FE_STICK)
			return self.action.pad(mapper, position, what)
		elif what == LEFT and mapper.was_pressed(SCButtons.LPAD):
			# Just released
			return self.action.pad(mapper, 0, what)
		elif what == CPAD and mapper.is_pressed(SCButtons.CPAD):
			return self.action.pad(mapper, position, what)
		elif what == CPAD and mapper.was_pressed(SCButtons.CPAD):
			# Just released
			return self.action.pad(mapper, 0, what)
		elif mapper.is_pressed(SCButtons.RPAD):
			# what == RIGHT, there are only two options
			return self.action.pad(mapper, position, what)
		elif mapper.was_pressed(SCButtons.RPAD):
			# what == RIGHT, there are only two options, Just released
			return self.action.pad(mapper, 0, what)


	def whole(self, mapper, x, y, what):
		if what in (STICK, LEFT) and mapper.is_pressed(SCButtons.LPAD):
			if what == STICK: mapper.force_event.add(FE_STICK)
			return self.action.whole(mapper, x, y, what)
		elif what in (STICK, LEFT) and mapper.was_pressed(SCButtons.LPAD):
			# Just released
			return self.action.whole(mapper, 0, 0, what)
		elif what == RIGHT and mapper.is_pressed(SCButtons.RPAD):
			return self.action.whole(mapper, x, y, what)
		elif what == RIGHT and mapper.was_pressed(SCButtons.RPAD):
			# Just released
			return self.action.whole(mapper, 0, 0, what)
		elif what == CPAD and mapper.is_pressed(SCButtons.CPAD):
			return self.action.whole(mapper, x, y, what)
		elif what == CPAD and mapper.was_pressed(SCButtons.CPAD):
			# Just released
			return self.action.whole(mapper, 0, 0, what)
		else:
			# Nothing is pressed, but finger moves over pad
			self.action.whole_blocked(mapper, x, y, what)


class TouchedModifier(Modifier):
	COMMAND = "touched"
	
	
	def describe(self, context):
		if context in (Action.AC_STICK, Action.AC_PAD):
			return _("(when %s)" % (self.COMMAND,)) + "\n" + self.action.describe(context)
		else:
			return _("(when %s)" % (self.COMMAND,)) + " " + self.action.describe(context)
	
	
	def strip(self):
		return self.action.strip()
	
	
	def compress(self):
		self.action = self.action.compress()
		return self
	
	
	def _release(self, mapper):
		return self.action.button_release(mapper)
	
	
	def whole(self, mapper, x, y, what):
		if mapper.is_touched(what) and not mapper.was_touched(what):
			self.action.button_press(mapper)
			mapper.schedule(0, self._release)


class UntouchedModifier(TouchedModifier):
	COMMAND = "untouched"
	
	
	def whole(self, mapper, x, y, what):
		if not mapper.is_touched(what) and mapper.was_touched(what):
			self.action.button_press(mapper)
			mapper.schedule(0, self._release)


class PressedModifier(Modifier):
	COMMAND = "pressed"
	
	
	def describe(self, context):
		if context in (Action.AC_STICK, Action.AC_PAD):
			return _("(when pressed)") + "\n" + self.action.describe(context)
		else:
			return _("(when pressed)") + " " + self.action.describe(context)
	
	
	def strip(self):
		return self.action.strip()
	
	
	def compress(self):
		self.action = self.action.compress()
		return self
	
	
	def button_press(self, mapper):
		self.action.button_press(mapper)
		mapper.schedule(0, self._release)
	
	
	def _release(self, mapper):
		return self.action.button_release(mapper)
	
	
	def button_release(self, mapper):
		pass


class ReleasedModifier(PressedModifier):
	COMMAND = "released"
	
	def describe(self, context):
		if context in (Action.AC_STICK, Action.AC_PAD):
			return _("(when released)") + "\n" + self.action.describe(context)
		else:
			return _("(when released)") + " " + self.action.describe(context)
	
	
	def button_press(self, mapper):
		pass
	
	
	def button_release(self, mapper):
		self.action.button_press(mapper)
		mapper.schedule(0, self._release)


class BallModifier(Modifier, WholeHapticAction):
	"""
	Emulates ball-like movement with inertia and friction.
	
	Reacts only to "whole" or "axis" inputs and sends generated movements as
	"add" input to child action.
	Target action has to have add(x, y) method defined.
	
	"""
	COMMAND = "ball"
	PROFILE_KEY_PRIORITY = -6
	HAPTIC_FACTOR = 60.0	# Just magic number
	
	DEFAULT_FRICTION = 10.0
	DEFAULT_MEAN_LEN = 10
	MIN_LIFT_VELOCITY = 0.2	# If finger is lifter after movement slower than 
							# this, roll doesn't happens
	
	def __init__(self, *params):
		Modifier.__init__(self, *params)
		WholeHapticAction.__init__(self)
	
	
	def _mod_init(self, friction=DEFAULT_FRICTION, mass=80.0,
			mean_len=DEFAULT_MEAN_LEN, r=0.02, ampli=65536, degree=40.0):
		self.speed = (1.0, 1.0)
		self.friction = friction
		self._xvel = 0.0
		self._yvel = 0.0
		self._ampli  = ampli
		self._degree = degree
		self._radscale = (degree * PI / 180) / ampli
		self._mass = mass
		self._roll_task = None
		self._r = r
		self._I = (2 * self._mass * self._r**2) / 5.0
		self._a = self._r * self.friction / self._I
		self._xvel_dq = deque(maxlen=mean_len)
		self._yvel_dq = deque(maxlen=mean_len)
		self._lastTime = time.time()
		self._old_pos = None
	
	
	def set_speed(self, x, y, *a):
		self.speed = (x, y)
	
	
	def get_speed(self):
		return self.speed
	
	
	def get_compatible_modifiers(self):
		return ( Action.MOD_SENSITIVITY | Action.MOD_FEEDBACK
			| Action.MOD_SMOOTH | Action.MOD_DEADZONE
			| Modifier.get_compatible_modifiers(self) )
	
	
	def _stop(self):
		""" Stops rolling of the 'ball' """
		self._xvel_dq.clear()
		self._yvel_dq.clear()
		if self._roll_task:
			self._roll_task.cancel()
			self._roll_task = None
	
	
	def _add(self, dx, dy):
		# Compute instant velocity
		try:
			self._xvel = sum(self._xvel_dq) / len(self._xvel_dq)
			self._yvel = sum(self._yvel_dq) / len(self._yvel_dq)
		except ZeroDivisionError:
			self._xvel = 0.0
			self._yvel = 0.0
		
		self._xvel_dq.append(dx * self._radscale)
		self._yvel_dq.append(dy * self._radscale)
	
	
	def _roll(self, mapper):
		# Compute time step
		t = time.time()
		dt, self._lastTime = t - self._lastTime, t
		
		# Free movement update velocity and compute movement
		self._xvel_dq.clear()
		self._yvel_dq.clear()
		
		_hyp = sqrt((self._xvel**2) + (self._yvel**2))
		if _hyp != 0.0:
			_ax = self._a * (abs(self._xvel) / _hyp)
			_ay = self._a * (abs(self._yvel) / _hyp)
		else:
			_ax = self._a
			_ay = self._a
		
		# Cap friction desceleration
		_dvx = min(abs(self._xvel), _ax * dt)
		_dvy = min(abs(self._yvel), _ay * dt)
		
		# compute new velocity
		_xvel = self._xvel - copysign(_dvx, self._xvel)
		_yvel = self._yvel - copysign(_dvy, self._yvel)
		
		# compute displacement
		dx = (((_xvel + self._xvel) / 2) * dt) / self._radscale
		dy = (((_yvel + self._yvel) / 2) * dt) / self._radscale
		
		self._xvel = _xvel
		self._yvel = _yvel
		
		self.action.add(mapper, dx * self.speed[0], dy * self.speed[1])
		if dx or dy:
			if self.haptic:
				WholeHapticAction.add(self, mapper, dx, dy)
			self._roll_task = mapper.schedule(0.02, self._roll)
	
	
	@staticmethod
	def decode(data, a, *b):
		if data[BallModifier.COMMAND] is True:
			# backwards compatibility
			return BallModifier(a)
		else:
			args = list(data[BallModifier.COMMAND])
			args.append(a)
			return BallModifier(*args)
	
	
	def describe(self, context):
		if self.name: return self.name
		# Special cases just to make GUI look pretty
		if isinstance(self.action, MouseAction):
			return _("Trackball")
		if isinstance(self.action, XYAction):
			if isinstance(self.action.x, AxisAction) and isinstance(self.action.y, AxisAction):
				x, y = self.action.x.parameters[0], self.action.y.parameters[0]
				if x == Axes.ABS_X and y == Axes.ABS_Y:
					return _("Mouse-like LStick")
				else:
					return _("Mouse-like RStick")
			if isinstance(self.action.x, MouseAction) and isinstance(self.action.y, MouseAction):
				x, y = self.action.x.parameters[0], self.action.y.parameters[0]
				if x in (Rels.REL_HWHEEL, Rels.REL_WHEEL) and y in (Rels.REL_HWHEEL, Rels.REL_WHEEL):
					return _("Mouse Wheel")
		
		return _("Ball(%s)") % (self.action.describe(context))
	
	
	def to_string(self, multiline=False, pad=0):
		return self._mod_to_string(self.strip_defaults(), multiline, pad)
	
	
	def cancel(self, mapper):
		Modifier.cancel(self, mapper)
		self._stop()
	
	
	def pad(self, mapper, position, what):
		self.whole(mapper, position, 0, what)
	
	
	def change(self, mapper, dx, dy, what):
		if what in (None, STICK) or (mapper.controller_flags() & ControllerFlags.HAS_RSTICK and what == RIGHT):
			return self.action.change(mapper, x, y, what)
		if mapper.is_touched(what):
			if mapper.was_touched(what):
				t = time.time()
				dt = t - self._lastTime
				if dt < 0.0075: return
				self._lastTime = t
				self._add(dx / dt, dy / dt)
				self.action.add(mapper, dx, dy)
			else:
				self._stop()
		elif mapper.was_touched(what):
			velocity = sqrt(self._xvel * self._xvel + self._yvel * self._yvel)
			if velocity > BallModifier.MIN_LIFT_VELOCITY:
				self._roll(mapper)
	
	
	def whole(self, mapper, x, y, what):
		if mapper.controller_flags() & ControllerFlags.HAS_RSTICK and what == RIGHT:
			return self.action.whole(mapper, x, y, what)
		if mapper.is_touched(what):
			if self._old_pos and mapper.was_touched(what):
				t = time.time()
				dt = t - self._lastTime
				if dt < 0.0075: return
				self._lastTime = t
				dx, dy = x - self._old_pos[0], self._old_pos[1] - y
				self._add(dx / dt, dy / dt)
				self.action.add(mapper, dx * self.speed[0], dy * self.speed[1])
			else:
				self._stop()
			self._old_pos = x, y
		elif mapper.was_touched(what):
			self._old_pos = None
			velocity = sqrt(self._xvel * self._xvel + self._yvel * self._yvel)
			if velocity > BallModifier.MIN_LIFT_VELOCITY:
				self._roll(mapper)
		elif what == STICK:
			return self.action.whole(mapper, x, y, what)
	
	
	def set_haptic(self, hd):
		if self.action and hasattr(self.action, "set_haptic"):
			self.action.set_haptic(hd)
		else:
			WholeHapticAction.set_haptic(self, hd)
	
	
	def get_haptic(self):
		if self.action and hasattr(self.action, "get_haptic"):
			return self.action.get_haptic()
		else:
			return WholeHapticAction.get_haptic(self)


class DeadzoneModifier(Modifier):
	COMMAND = "deadzone"
	JUMP_HARDCODED_LIMIT = 5
	
	def _mod_init(self, *params):
		if len(params) < 1: raise TypeError("Not enough parameters")
		if type(params[0]) in (str, unicode):
			self.mode = params[0]
			if hasattr(self, "mode_" + self.mode):
				self._convert = getattr(self, "mode_" + self.mode)
			else:
				raise ValueError("Invalid deadzone mode")
			params = params[1:]
			if len(params) < 1: raise TypeError("Not enough parameters")
		else:
			# 'cut' mode is default
			self.mode = CUT
			self._convert = self.mode_CUT
		
		self.lower = int(params[0])
		self.upper = int(params[1]) if len(params) == 2 else STICK_PAD_MAX
	
	
	def mode_CUT(self, x, y, range):
		"""
		If input value is out of deadzone range, output value is zero
		"""
		if y == 0:
			# Small optimalization for 1D input, for example trigger
			return (0 if abs(x) < self.lower or abs(x) > self.upper else x), 0
		distance = sqrt(x*x + y*y)
		if distance < self.lower or distance > self.upper:
			return 0, 0
		return x, y
	
	
	def mode_ROUND(self, x, y, range):
		"""
		If input value bellow deadzone range, output value is zero
		If input value is above deadzone range,
		output value is 1 (or maximum allowed)
		"""
		if y == 0:
			# Small optimalization for 1D input, for example trigger
			if abs(x) > self.upper:
				return copysign(range, x)
			return (0 if abs(x) < self.lower else x), 0
		distance = sqrt(x*x + y*y)
		if distance < self.lower:
			return 0, 0
		if distance > self.upper:
			angle = atan2(x, y)
			return range * sin(angle), range * cos(angle)
		return x, y
	
	
	def mode_LINEAR(self, x, y, range):
		"""
		Input value is scaled, so entire output range is covered by
		reduced input range of deadzone.
		"""
		if y == 0:
			# Small optimalization for 1D input, for example trigger
			return copysign(
				clamp(
					0,
					((x - self.lower) / (self.upper - self.lower)) * range,
					range),
				x
			), 0
		distance = clamp(self.lower, sqrt(x*x + y*y), self.upper)
		distance = (distance - self.lower) / (self.upper - self.lower) * range
		
		angle = atan2(x, y)
		return distance * sin(angle), distance * cos(angle)
	
	
	def mode_MINIMUM(self, x, y, range):
		"""
		https://github.com/kozec/sc-controller/issues/356
		Inversion of LINEAR; input value is scaled so entire input range is
		mapped to range of deadzone.
		"""
		if y == 0:
			# Small optimalization for 1D input, for example trigger
			if abs(x) < DeadzoneModifier.JUMP_HARDCODED_LIMIT:
				return 0, 0
			return (copysign(
						(float(abs(x)) / range * (self.upper - self.lower))
						+ self.lower, x), 0)
		distance = sqrt(x*x + y*y)
		if distance < DeadzoneModifier.JUMP_HARDCODED_LIMIT:
			return 0, 0
		distance = (distance / range * (self.upper - self.lower)) + self.lower
		
		angle = atan2(x, y)
		return distance * sin(angle), distance * cos(angle)
	
	
	@staticmethod
	def decode(data, a, *b):
		return DeadzoneModifier(
			data["deadzone"]["mode"] if "mode" in data["deadzone"] else CUT,
			data["deadzone"]["lower"] if "lower" in data["deadzone"] else STICK_PAD_MIN,
			data["deadzone"]["upper"] if "upper" in data["deadzone"] else STICK_PAD_MAX,
			a
		)
	
	
	def compress(self):
		self.action = self.action.compress()
		if isinstance(self.action, BallModifier) and self.mode == MINIMUM:
			# Special case where BallModifier has to be applied before
			# deadzone is computed
			ballmod = self.action
			self.action, ballmod.action = ballmod.action, self
			return ballmod
		return self
	
	
	def strip(self):
		return self.action.strip()
	
	
	def __str__(self):
		return "<Modifier '%s', %s>" % (self.COMMAND, self.action)
	
	__repr__ = __str__
	
	
	def describe(self, context):
		dsc = self.action.describe(context)
		if "\n" in dsc:
			return "%s\n(with deadzone)" % (dsc,)
		else:
			return "%s (with deadzone)" % (dsc,)
	
	
	def to_string(self, multiline=False, pad=0):
		params = []
		if self.mode != CUT:
			params.append(self.mode)
		params.append(str(self.lower))
		if self.upper != STICK_PAD_MAX:
			params.append(str(self.upper))
		params.append(self.action.to_string(multiline))
	
		return "deadzone(%s)" % ( ", ".join(params), )
	
	
	def trigger(self, mapper, position, old_position):
		position = self._convert(position, None, TRIGGER_MAX)
		return self.action.trigger(mapper, position, old_position)
	
	
	def axis(self, mapper, position, what):
		position = self._convert(position, None, STICK_PAD_MAX)
		return self.action.axis(mapper, position, what)
	
	
	def pad(self, mapper, position, what):
		position = self._convert(position, None, STICK_PAD_MAX)
		return self.action.pad(mapper, position, what)
	
	
	def whole(self, mapper, x, y, what):
		x, y = self._convert(x, y, STICK_PAD_MAX)
		return self.action.whole(mapper, x, y, what)
	
	
	def gyro(self, mapper, pitch, yaw, roll, q1, q2, q3, q4):
		q2 = self._convert(q2, STICK_PAD_MAX)
		q3 = self._convert(q3, STICK_PAD_MAX)
		return self.action.gyro(mapper, pitch, yaw, roll, q1, q2, q3, q4)


class ModeModifier(Modifier):
	COMMAND = "mode"
	PROFILE_KEYS = ("modes",)
	MIN_TRIGGER = 2		# When trigger is bellow this position, list of held_triggers is cleared
	MIN_STICK = 2		# When abs(stick) < MIN_STICK, stick is considered released and held_sticks is cleared
	PROFILE_KEY_PRIORITY = 2
	
	def __init__(self, *stuff):
		Modifier.__init__(self)
		self.default = None
		self.mods = OrderedDict()
		self.held_buttons = set()
		self.held_sticks = set()
		self.held_triggers = {}
		self.old_action = None
		self.timeout = DoubleclickModifier.DEAFAULT_TIMEOUT
		
		button = None
		for i in stuff:
			if self.default is not None:
				# Default has to be last parameter
				raise ValueError("Invalid parameters for 'mode'")
			if isinstance(i, Action) and button is None:
				self.default = i
			elif isinstance(i, Action):
				self.mods[button] = i
				button = None
			elif isinstance(i, RangeOP) or i in SCButtons:
				button = i
			else:
				raise ValueError("Invalid parameter for 'mode': %s" % (i,))
		self.make_checks()
		if self.default is None:
			self.default = NoAction()
	
	
	def make_checks(self):
		self.checks = []
		for button, action in self.mods.items():
			if isinstance(button, RangeOP):
				self.checks.append(( button, action ))
			else:
				self.checks.append(( self.make_button_check(button), action ))
	
	
	def get_child_actions(self):
		if self.default is None:
			return self.mods.values()
		else:
			return [ self.default ] + self.mods.values()
	
	
	@staticmethod
	def decode(data, a, parser, *b):
		args = []
		for button in data[ModeModifier.PROFILE_KEYS[0]]:
			if hasattr(SCButtons, button):
				args += [ getattr(SCButtons, button), parser.from_json_data(data[ModeModifier.PROFILE_KEYS[0]][button]) ]
		if a:
			args += [ a ]
		mm = ModeModifier(*args)
		if "name" in data:
			mm.name = data["name"]
		return mm
	
	
	def get_compatible_modifiers(self):
		rv = 0
		for action in self.mods.values():
			rv |= action.get_compatible_modifiers()
		if self.default:
			rv |= self.default.get_compatible_modifiers()
		return rv
	
	
	def strip(self):
		# Returns default action or action assigned to first modifier
		if self.default:
			return self.default.strip()
		if len(self.mods):
			return self.mods.values()[0].strip()
		# Empty ModeModifier
		return NoAction()
	
	
	def compress(self):
		if self.default:
			self.default = self.default.compress()
		for check in self.mods:
			self.mods[check] = self.mods[check].compress()
		self.make_checks()
		return self
	
	
	def __str__(self):
		rv = [ ]
		for check in self.mods:
			rv += [ nameof(check), self.mods[check] ]
		if self.default is not None:
			rv += [ self.default ]
		return "<Modifier '%s', %s>" % (self.COMMAND, rv)
	
	__repr__ = __str__
	
	
	def describe(self, context):
		if self.name: return self.name
		l = []
		if self.default : l.append(self.default)
		for check in self.mods:
			l.append(self.mods[check])
		return "\n".join([ x.describe(context) for x in l ])
	
	
	def to_string(self, multiline=False, pad=0):
		if multiline:
			rv = [ (" " * pad) + "mode(" ]
			for check in self.mods:
				a_str = NameModifier.unstrip(self.mods[check]).to_string(True).split("\n")
				a_str[0] = (" " * pad) + "  " + (nameof(check) + ",").ljust(11) + a_str[0]	# Key has to be one of SCButtons
				for i in xrange(1, len(a_str)):
					a_str[i] = (" " * pad) + "  " + a_str[i]
				a_str[-1] = a_str[-1] + ","
				rv += a_str
			if self.default is not None:
				a_str = [
					(" " * pad) + "  " + x
					for x in NameModifier.unstrip(self.default).to_string(True).split("\n")
				]
				rv += a_str
			if rv[-1][-1] == ",":
				rv[-1] = rv[-1][0:-1]
			rv += [ (" " * pad) + ")" ]
			return "\n".join(rv)
		else:
			rv = [ ]
			for check in self.mods:
				rv += [ nameof(check), NameModifier.unstrip(self.mods[check]).to_string(False) ]
			if self.default is not None:
				rv += [ NameModifier.unstrip(self.default).to_string(False) ]
			return "mode(" + ", ".join(rv) + ")"
	
	
	def cancel(self, mapper):
		for action in self.mods.values():
			action.cancel(mapper)
		self.default.cancel(mapper)
	
	
	def select(self, mapper):
		"""
		Selects action by pressed button.
		"""
		for check, action in self.checks:
			if check(mapper):
				return action
		return self.default
	
	
	def select_w_check(self, mapper):
		"""
		As select, but returns matched check as well.
		"""
		for check, action in self.checks:
			if check(mapper):
				return check, action
		return lambda *a:True, self.default
	
	
	@staticmethod
	def make_button_check(button):
		def cb(mapper):
			return mapper.is_pressed(button)
		
		cb.name = button.name	# So nameof() still works on keys in self.mods
		return cb
	
	
	def button_press(self, mapper):
		sel = self.select(mapper)
		self.held_buttons.add(sel)
		return sel.button_press(mapper)
	
	
	def button_release(self, mapper):
		# Releases all held buttons, not just button that matches
		# currently pressed modifier
		for b in self.held_buttons:
			b.button_release(mapper)
	
	
	def trigger(self, mapper, position, old_position):
		if position < ModeModifier.MIN_TRIGGER:
			for b in self.held_triggers:
				b.trigger(mapper, 0, self.held_triggers[b])
			self.held_triggers = {}
			return False
		else:
			sel = self.select(mapper)
			self.held_triggers[sel] = position
			return sel.trigger(mapper, position, old_position)
	
	
	def axis(self, mapper, position, what):
		return self.select(mapper).axis(mapper, position, what)
	
	
	def gyro(self, mapper, pitch, yaw, roll, *q):
		sel = self.select(mapper)
		if sel is not self.old_action:
			if self.old_action:
				self.old_action.gyro(mapper, 0, 0, 0, *q)
			self.old_action = sel
		return sel.gyro(mapper, pitch, yaw, roll, *q)
	
	
	def pad(self, mapper, position, what):
		return self.select(mapper).pad(mapper, position, what)
	
	
	def whole(self, mapper, x, y, what):
		if what == STICK:
			if abs(x) < ModeModifier.MIN_STICK and abs(y) < ModeModifier.MIN_STICK:
				for check, action in self.held_sticks:
					action.whole(mapper, 0, 0, what)
				self.held_sticks.clear()
			else:
				ac, active = self.select_w_check(mapper)
				self.held_sticks.add(( ac, active ))
				for check, action in list(self.held_sticks):
					if check == ac or check(mapper):
						action.whole(mapper, x, y, what)
					else:
						action.whole(mapper, 0, 0, what)
						self.held_sticks.remove(( check, action ))
			mapper.force_event.add(FE_STICK)
		else:
			sel = self.select(mapper)
			if sel is not self.old_action:
				mapper.set_button(what, False)
				if self.old_action:
					self.old_action.whole(mapper, 0, 0, what)
				self.old_action = sel
				rv = sel.whole(mapper, x, y, what)
				mapper.set_button(what, True)
				return rv
			else:
				return sel.whole(mapper, x, y, what)


class DoubleclickModifier(Modifier, HapticEnabledAction):
	COMMAND = "doubleclick"
	DEAFAULT_TIMEOUT = 0.2
	TIMEOUT_KEY = "time"
	PROFILE_KEY_PRIORITY = 3
	
	def __init__(self, doubleclickaction, normalaction=None, time=None):
		Modifier.__init__(self)
		HapticEnabledAction.__init__(self)
		self.action = doubleclickaction
		self.normalaction = normalaction or NoAction()
		self.holdaction = NoAction()
		self.actions = ( self.action, self.normalaction, self.holdaction )
		self.timeout = time or DoubleclickModifier.DEAFAULT_TIMEOUT
		self.waiting_task = None
		self.pressed = False
		self.active = None
	
	
	def get_child_actions(self):
		return self.action, self.normalaction, self.holdaction
	
	
	@staticmethod
	def decode(data, a, parser, *b):
		args = [ parser.from_json_data(data[DoubleclickModifier.COMMAND]), a ]
		a = DoubleclickModifier(*args)
		if DoubleclickModifier.TIMEOUT_KEY in data:
			a.timeout = data[DoubleclickModifier.TIMEOUT_KEY]
		return a
	
	
	def strip(self):
		if self.holdaction:
			return self.holdaction.strip()
		return self.action.strip()
	
	
	def compress(self):
		self.action = self.action.compress()
		self.holdaction = self.holdaction.compress()
		self.normalaction = self.normalaction.compress()
		
		for a in (self.holdaction, self.normalaction):
			if isinstance(a, HoldModifier):
				self.holdaction = a.holdaction or self.holdaction
				self.normalaction = a.normalaction or self.normalaction
		
		if isinstance(self.action, HoldModifier):
			self.holdaction = self.action.holdaction
			self.action = self.action.normalaction
		return self
	
	
	def __str__(self):
		l = [ self.action ]
		if self.normalaction:
			l += [ self.normalaction ]
		return "<Modifier %s dbl='%s' hold='%s' normal='%s'>" % (
			self.COMMAND, self.action, self.holdaction, self.normalaction )
	
	__repr__ = __str__
	
	
	def describe(self, context):
		l = [ ]
		if self.action:
			l += [ self.action ]
		if self.holdaction:
			l += [ self.holdaction ]
		if self.normalaction:
			l += [ self.normalaction ]
		return "\n".join([ x.describe(context) for x in l ])
	
	
	def to_string(self, multiline=False, pad=0):
		timeout = ""
		if DoubleclickModifier.DEAFAULT_TIMEOUT != self.timeout:
			timeout = ", %s" % (self.timeout)
		if self.action and self.normalaction and self.holdaction:
			return "doubleclick(%s, hold(%s, %s)%s)" % (
				NameModifier.unstrip(self.action).to_string(multiline, pad),
				NameModifier.unstrip(self.holdaction).to_string(multiline, pad),
				NameModifier.unstrip(self.normalaction).to_string(multiline, pad),
				timeout
			)
		elif self.action and self.normalaction and not self.holdaction:
			return "doubleclick(%s, %s%s)" % (
				NameModifier.unstrip(self.action).to_string(multiline, pad),
				NameModifier.unstrip(self.normalaction).to_string(multiline, pad),
				timeout
			)
		elif not self.action and self.normalaction and self.holdaction:
			return "hold(%s, %s%s)" % (
				NameModifier.unstrip(self.holdaction).to_string(multiline, pad),
				NameModifier.unstrip(self.normalaction).to_string(multiline, pad),
				timeout
			)
		elif not self.action and not self.normalaction and self.holdaction:
			return "hold(None, %s%s)" % (
				NameModifier.unstrip(self.holdaction).to_string(multiline, pad),
				timeout
			)
		elif self.action and not self.normalaction and not self.holdaction:
			return "doubleclick(None, %s%s)" % (
				NameModifier.unstrip(self.action).to_string(multiline, pad),
				timeout
			)
		return NameModifier.unstrip(
				self.action or self.normalaction or self.holdaction
			).to_string(multiline, pad)
	
	
	def button_press(self, mapper):
		self.pressed = True
		if self.waiting_task:
			# Double-click happened
			mapper.cancel_task(self.waiting_task)
			self.waiting_task = None
			self.active = self.action
			self.active.button_press(mapper)
		else:
			# First click, start the timer
			self.waiting_task = mapper.schedule(self.timeout, self.on_timeout)
	
	
	def button_release(self, mapper):
		self.pressed = False
		if self.waiting_task and self.active is None and not self.action:
			# In HoldModifier, button released before timeout
			mapper.cancel_task(self.waiting_task)
			self.waiting_task = None
			if self.normalaction:
				self.normalaction.button_press(mapper)
				self.normalaction.button_release(mapper)
		elif self.active:
			# Released held button
			self.active.button_release(mapper)
			self.active = None
	
	
	def on_timeout(self, mapper, *a):
		if self.waiting_task:
			self.waiting_task = None
			if self.pressed:
				# Timeouted while button is still pressed
				self.active = self.holdaction if self.holdaction else self.normalaction
				if self.haptic:
					mapper.send_feedback(self.haptic)
				self.active.button_press(mapper)
			elif self.normalaction:
				# User did short click and nothing else
				self.normalaction.button_press(mapper)
				self.normalaction.button_release(mapper)


class HoldModifier(DoubleclickModifier):
	# Hold modifier is implemented as part of DoubleclickModifier, because
	# situation when both are assigned to same button needs to be treated
	# specially.
	COMMAND = "hold"
	PROFILE_KEY_PRIORITY = 4

	def __init__(self, holdaction, normalaction=None, time=None):
		DoubleclickModifier.__init__(self, NoAction(), normalaction, time)
		self.holdaction = holdaction
	
	
	@staticmethod
	def decode(data, a, parser, *b):
		if isinstance(a, DoubleclickModifier):
			a.holdaction = parser.from_json_data(data[HoldModifier.COMMAND])
		else:
			args = [ parser.from_json_data(data[HoldModifier.COMMAND]), a ]
			a = HoldModifier(*args)
		if DoubleclickModifier.TIMEOUT_KEY in data:
			a.timeout = data[DoubleclickModifier.TIMEOUT_KEY]
		if isinstance(a.normalaction, FeedbackModifier):
			# Ugly hack until profile file is redone
			mod = a.normalaction
			a.normalaction = mod.action
			if hasattr(a.normalaction, "set_haptic"):
				a.normalaction.set_haptic(None)
			mod.action = a
			mod.action.set_haptic(mod.haptic)
			a = mod
		return a
	
	
	def compress(self):
		self.action = self.action.compress()
		self.holdaction = self.holdaction.compress()
		self.normalaction = self.normalaction.compress()
		
		for a in (self.action, self.normalaction):
			if isinstance(a, DoubleclickModifier):
				self.action = a.action or self.action
				self.normalaction = a.normalaction or self.normalaction
		
		if isinstance(self.holdaction, DoubleclickModifier):
			self.action = self.holdaction.action
			self.holdaction = self.holdaction.normalaction
		return self


class SensitivityModifier(Modifier):
	"""
	Sets action sensitivity, if action supports it.
	Action that supports such setting has set_speed(x, y, z)
	and get_speed() methods defined.
	
	Does nothing otherwise.
	"""
	COMMAND = "sens"
	PROFILE_KEYS = ("sensitivity",)
	PROFILE_KEY_PRIORITY = -5
	
	def _mod_init(self, *speeds):
		self.speeds = []
		for s in speeds:
			if type(s) in (int, float):
				self.speeds.append(float(s))
		while len(self.speeds) < 3:
			self.speeds.append(1.0)
		if self.action:
			a = self.action
			while a:
				if hasattr(a, "set_speed"):
					a.set_speed(*self.speeds)
					break
				if hasattr(a, "action"):
					a = a.action
				else:
					break
	
	
	@staticmethod
	def decode(data, a, *b):
		if a:
			args = list(data["sensitivity"])
			args.append(a)
			return SensitivityModifier(*args)
		# Adding sensitivity to NoAction makes no sense
		return a
	
	
	def strip(self):
		return self.action.strip()
	
	
	def compress(self):
		return self.action.compress()
	
	
	def describe(self, context):
		if self.name: return self.name
		return self.action.describe(context)
	
	
	def to_string(self, multiline=False, pad=0):
		speeds = [] + self.speeds
		while len(speeds) > 1 and speeds[-1] == 1.0:
			speeds = speeds[0:-1]
		return self._mod_to_string(speeds, multiline, pad)
	
	
	def __str__(self):
		return "<Sensitivity=%s, %s>" % (self.speeds, self.action)


class FeedbackModifier(Modifier):
	"""
	Enables feedback for action, action supports it.
	Action that supports feedback has to have set_haptic(hapticdata)
	method defined.

	Does nothing otherwise.
	"""
	COMMAND = "feedback"
	PROFILE_KEY_PRIORITY = -4
	
	def _mod_init(self, position, amplitude=512, frequency=4, period=1024, count=1):
		self.haptic = HapticData(position, amplitude, frequency, period, count)
		if self.action:
			a = self.action
			while a:
				if hasattr(a, "set_haptic"):
					a.set_haptic(self.haptic)
					break
				if hasattr(a, "action"):
					a = a.action
				else:
					break
	
	
	@staticmethod
	def decode(data, a, *b):
		args = list(data[FeedbackModifier.COMMAND])
		if hasattr(HapticPos, args[0]):
			args[0] = getattr(HapticPos, args[0])
		args.append(a)
		return FeedbackModifier(*args)
	
	
	def describe(self, context):
		if self.name: return self.name
		return self.action.describe(context)
	
	
	def to_string(self, multiline=False, pad=0):
		return self._mod_to_string(self.strip_defaults(), multiline, pad)
	
	
	def __str__(self):
		return "<with Feedback %s>" % (self.action,)
	
	
	def strip(self):
		return self.action.strip()
	
	
	def compress(self):
		return self.action.compress()


class RotateInputModifier(Modifier):
	""" Rotates ball or stick input along axis """
	COMMAND = "rotate"
	
	def _mod_init(self, angle):
		self.angle = angle
	
	
	@staticmethod
	def decode(data, a, *b):
		return RotateInputModifier(float(data['rotate']), a)
	
	
	def describe(self, context):
		if self.name: return self.name
		return self.action.describe(context)
	
	
	def to_string(self, multiline=False, pad=0):
		return self._mod_to_string((self.angle,), multiline, pad)
	
	
	def strip(self):
		return self.action.strip()
	
	
	def compress(self):
		if hasattr(self.action, "set_rotation"):
			self.action.set_rotation(self.angle * PI / -180.0)
			return self.action
		self.action = self.action.compress()
		return self
	
	
	# This doesn't make sense with anything but 'whole' as input.
	def whole(self, mapper, x, y, what):
		angle = self.angle * PI / -180.0
		rx = x * cos(angle) - y * sin(angle)
		ry = x * sin(angle) + y * cos(angle)
		return self.action.whole(mapper, rx, ry, what)


class SmoothModifier(Modifier):
	"""
	Smooths pad movements
	"""
	COMMAND = "smooth"
	PROFILE_KEY_PRIORITY = 11	# Before sensitivity
	
	def _mod_init(self, level=8, multiplier=0.75, filter=2.0):
		self.level = level
		self.multiplier = multiplier
		self.filter = filter
		self._deq_x = deque([ 0.0 ] * level, maxlen=level)
		self._deq_y = deque([ 0.0 ] * level, maxlen=level)
		self._range = list(xrange(level))
		self._weights = [ multiplier ** x for x in reversed(self._range) ]
		self._w_sum = sum(self._weights)
		self._last_pos = None
		self._moving = False
	
	
	def __str__(self):
		return "<Smooth %s>" % (self.action,)
	
	
	def describe(self, context):
		if self.name: return self.name
		return "%s (smooth)" % (self.action.describe(context),)
	
	
	@staticmethod
	def decode(data, a, *b):
		pars = data[SmoothModifier.COMMAND] + [ a ]
		return SmoothModifier(*pars)
	
	
	def _get_pos(self):
		""" Computes average x,y from all accumulated positions """
		x = sum(( self._deq_x[i] * self._weights[i] for i in self._range ))
		y = sum(( self._deq_y[i] * self._weights[i] for i in self._range ))
		return x / self._w_sum, y / self._w_sum
	
	
	def whole(self, mapper, x, y, what):
		if mapper.controller_flags() & ControllerFlags.HAS_RSTICK and what == RIGHT:
			return self.action.whole(mapper, x, y, what)
		if mapper.is_touched(what):
			if self._last_pos is None:
				# Just pressed - fill deque with current position
				for i in self._range:
					self._deq_x.append(x)
					self._deq_y.append(y)
				x, y = self._get_pos()
				self._last_pos = 0
			else:
				# Pressed for longer time
				self._deq_x.append(x)
				self._deq_y.append(y)
				x, y = self._get_pos()
			if abs(x + y - self._last_pos) > self.filter:
				self.action.whole(mapper, x, y, what)
			self._last_pos = x + y
		elif what == STICK:
			return self.action.whole(mapper, x, y, what)
		else:
			# Pad was just released
			x, y = self._get_pos()
			self.action.whole(mapper, x, y, what)
			self._last_pos = None


class CircularModifier(Modifier, HapticEnabledAction):
	"""
	Designed to translate rotating finger over pad to mouse wheel movement.
	Can also be used to translate same thing into movement of Axis.
	"""
	COMMAND = "circular"
	PROFILE_KEY_PRIORITY = -6
	
	def __init__(self, *params):
		# Piece of backwards compatibility
		if len(params) >= 1 and params[0] in Rels:
			params = [ MouseAction(params[0]) ]
		self._haptic_counter = 0
		Modifier.__init__(self, *params)
		HapticEnabledAction.__init__(self)
	
	
	def _mod_init(self):
		self.angle = None		# Last known finger position
		self.speed = 1.0
	
	
	def set_haptic(self, hd):
		if isinstance(self.action, HapticEnabledAction):
			self.action.set_haptic(hd)
		else:
			HapticEnabledAction.set_haptic(self, hd)
	
	
	def get_haptic(self):
		if isinstance(self.action, HapticEnabledAction):
			return self.action.get_haptic()
		else:
			return HapticEnabledAction.get_haptic(self)
	
	
	@staticmethod
	def decode(data, a, *b):
		return CircularModifier(a)
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Circular %s") % (self.action.describe(context))
	
	
	def set_speed(self, x, *a):
		self.speed = x
	
	
	def get_speed(self):
		return (self.speed,)
	
	
	def get_compatible_modifiers(self):
		return ( Action.MOD_FEEDBACK | Action.MOD_SENSITIVITY
			| Modifier.get_compatible_modifiers(self) )
	
	
	def whole(self, mapper, x, y, what):
		distance = sqrt(x*x + y*y)
		if distance < STICK_PAD_MAX_HALF:
			# Finger lifted or too close to middle
			self.angle = None
			if mapper.was_touched(what):
				self.action.change(mapper, 0, 0, what)
		else:
			# Compute current angle
			angle = atan2(x, y)
			# Compute movement
			if self.angle is None:
				# Finger just touched the pad
				self.angle, angle = angle, 0
				self._haptic_counter = 0
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
			angle *= 10000.0
			# Generate feedback, if enabled
			if self.haptic:
				self._haptic_counter += angle * self.speed / self.haptic.frequency
				if abs(self._haptic_counter) > 0.5:
					if self._haptic_counter > 0.5:
						self._haptic_counter -= 0.5
					else:
						self._haptic_counter += 0.5
					mapper.send_feedback(self.haptic)
			# Apply movement to child action
			self.action.change(mapper, -angle * self.speed, 0, what)
			mapper.force_event.add(FE_PAD)


class CircularAbsModifier(Modifier, WholeHapticAction):
	"""
	Works similary to CircularModifier, but instead of counting with finger
	movements movements, translates exact position on dpad to axis value.
	"""
	COMMAND = "circularabs"
	PROFILE_KEY_PRIORITY = -6
	
	def __init__(self, *params):
		Modifier.__init__(self, *params)
		WholeHapticAction.__init__(self)
	
	
	def _mod_init(self):
		self.angle = None		# Last known finger position
		self.speed = 1.0
	
	
	@staticmethod
	def decode(data, a, *b):
		return CircularAbsModifier(a)
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Absolute Circular %s") % (self.action.describe(context))
	
	
	def set_speed(self, x, *a):
		self.speed = x
	
	
	def get_speed(self):
		return (self.speed,)
	
	
	def get_compatible_modifiers(self):
		return ( Action.MOD_FEEDBACK | Action.MOD_SENSITIVITY | Action.MOD_ROTATE
			| Modifier.get_compatible_modifiers(self) )
	
	
	def whole(self, mapper, x, y, what):
		distance = sqrt(x*x + y*y)
		if distance < STICK_PAD_MAX_HALF:
			# Finger lifted or too close to middle
			self.angle = None
		else:
			# Compute current angle
			angle = atan2(x, y) + PI / 4
			# Compute movement
			if self.haptic:
				if self.angle is not None:
					diff = self.angle - angle
					# Ensure we don't wrap from pi to -pi creating a large delta
					if angle > PI:
						# Subtract a full rotation to counter the wrapping
						angle -= 2 * PI
					# And same from -pi to pi
					elif angle < -PI:
						# Add a full rotation to counter the wrapping
						angle += 2 * PI
					if abs(diff) < 6:# Prevents crazy feedback burst when finger cross 360' angle
						WholeHapticAction.change(self, mapper, diff * 10000, 0, what)
				self.angle = angle
			# Apply actual constant
			angle *= STICK_PAD_MAX / PI
			# Set axis on child action
			self.action.axis(mapper, angle * self.speed, 0)
			mapper.force_event.add(FE_PAD)
