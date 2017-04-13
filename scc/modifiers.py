#!/usr/bin/env python2
"""
SC Controller - Modifiers

Modifier is Action that just sits between input and actual action, changing
way how resulting action works.
For example, click() modifier executes action only if pad is pressed.
"""
from __future__ import unicode_literals

from scc.actions import Action, MouseAction, XYAction, AxisAction
from scc.actions import NoAction, WholeHapticAction, HapticEnabledAction
from scc.constants import TRIGGER_MAX, LEFT, RIGHT, STICK, FE_STICK, FE_TRIGGER
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX, STICK_PAD_MAX_HALF
from scc.constants import FE_PAD, SCButtons, HapticPos
from scc.constants import CUT, ROUND, LINEAR
from scc.controller import HapticData
from scc.tools import nameof, clamp
from scc.uinput import Axes, Rels
from math import pi as PI, sqrt, copysign, atan2, sin, cos
from collections import deque

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
	
	
	def get_child_actions(self):
		return (self.action, )
	
	
	def _mod_init(self):
		"""
		Initializes modifier with rest of parameters, after action nparameter
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
		return self.action
	
	
	def compress(self):
		if self.action:
			self.action = self.action.compress()
		return self
	
	
	def __str__(self):
		return "<Modifier '%s', %s>" % (self.COMMAND, self.action)
	
	__repr__ = __str__
	
	
	def encode(self):
		rv = self.action.encode()
		if self.name:
			rv[NameModifier.COMMAND] = self.name
		return rv


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


	def compress(self):
		return self.strip()


	def to_string(self, multiline=False, pad=0):
		return "%s(%s, %s)" % (
			self.COMMAND,
			repr(self.name).strip('u'),
			self.action.to_string(multiline, pad)
		)


class ClickModifier(Modifier):
	COMMAND = "click"

	def encode(self):
		rv = Modifier.encode(self)
		rv[ClickModifier.COMMAND] = True
		return rv


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
		if what in (STICK, LEFT) and mapper.was_pressed(SCButtons.LPAD):
			# Just released
			return self.action.axis(mapper, 0, what)
		# what == RIGHT, there are only three options
		if mapper.is_pressed(SCButtons.RPAD):
			return self.action.axis(mapper, position, what)
		if mapper.was_pressed(SCButtons.RPAD):
			# Just released
			return self.action.axis(mapper, 0, what)


	def pad(self, mapper, position, what):
		if what == LEFT and mapper.is_pressed(SCButtons.LPAD):
			if what == STICK: mapper.force_event.add(FE_STICK)
			return self.action.pad(mapper, position, what)
		if what == LEFT and mapper.was_pressed(SCButtons.LPAD):
			# Just released
			return self.action.pad(mapper, 0, what)
		# what == RIGHT, there are only two options
		if mapper.is_pressed(SCButtons.RPAD):
			return self.action.pad(mapper, position, what)
		if mapper.was_pressed(SCButtons.RPAD):
			# Just released
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
		else:
			# Nothing is pressed, but finger moves over pad
			self.action.whole_blocked(mapper, 0, 0, what)


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
	
	
	def _add(self, dx, dy):
		# Compute time step
		_tmp = time.time()
		dt = _tmp - self._lastTime
		self._lastTime = _tmp
		
		# Compute instant velocity
		try:
			self._xvel = sum(self._xvel_dq) / len(self._xvel_dq)
			self._yvel = sum(self._yvel_dq) / len(self._yvel_dq)
		except ZeroDivisionError:
			self._xvel = 0.0
			self._yvel = 0.0
		
		self._xvel_dq.append(dx * self._radscale / dt)
		self._yvel_dq.append(dy * self._radscale / dt)
	
	
	def _roll(self, mapper):
		# Compute time step
		_tmp = time.time()
		dt = _tmp - self._lastTime
		self._lastTime = _tmp
		
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
		
		if dx or dy:
			self.action.add(mapper, dx * self.speed[0], dy * self.speed[1])
			if self.haptic:
				WholeHapticAction.add(self, mapper, dx, dy)
			mapper.schedule(0, self._roll)
	
	
	def encode(self):
		rv = Modifier.encode(self)
		pars = self.strip_defaults()
		rv[BallModifier.COMMAND] = pars
		return rv
	
	
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
	
	
	def pad(self, mapper, position, what):
		self.whole(mapper, position, 0, what)
	
	
	def whole(self, mapper, x, y, what):
		if mapper.is_touched(what):
			if self._old_pos and mapper.was_touched(what):
				dx, dy = x - self._old_pos[0], self._old_pos[1] - y
				self._add(dx, dy)
				self.action.add(mapper, dx * self.speed[0], dy * self.speed[1])
			else:
				self._stop()
			self._old_pos = x, y
		elif mapper.was_touched(what):
			self._roll(mapper)
	
	
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
	
	
	def encode(self):
		rv = Modifier.encode(self)
		rv[DeadzoneModifier.COMMAND] = dict(
			upper = self.upper,
			lower = self.lower,
			mode = self.mode
		)
		return rv
	
	
	@staticmethod
	def decode(data, a, *b):
		return DeadzoneModifier(
			data["deadzone"]["mode"] if "mode" in data["deadzone"] else CUT,
			data["deadzone"]["lower"] if "lower" in data["deadzone"] else STICK_PAD_MIN,
			data["deadzone"]["upper"] if "upper" in data["deadzone"] else STICK_PAD_MAX,
			a
		)
	
	
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
		ox, oy = x, y
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
		self.mods = {}
		self.held_buttons = set()
		self.held_sticks = set()
		self.held_triggers = {}
		self.order = []
		self.old_gyro = None
		self.timeout = DoubleclickModifier.DEAFAULT_TIMEOUT
		
		button = None
		for i in stuff:
			if self.default is not None:
				# Default has to be last parameter
				raise ValueError("Invalid parameters for 'mode'")
			if isinstance(i, Action):
				if button is None:
					self.default = i
					continue
				self.mods[button] = i
				self.order.append(button)
				button = None
			elif i in SCButtons:
				button = i
			else:
				raise ValueError("Invalid parameter for 'mode': %s" % (i,))
		if self.default is None:
			self.default = NoAction()
	
	
	def get_child_actions(self):
		return [ self.mods[key] for key in self.mods ]
	
	
	def encode(self):
		rv = self.default.encode()
		modes = {}
		for key in self.mods:
			modes[key.name] = self.mods[key].encode()
		rv[ModeModifier.PROFILE_KEYS[0]] = modes
		if self.name:
			rv[NameModifier.COMMAND] = self.name
		return rv
	
	
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
		for key in self.mods:
			rv |= self.mods[key].get_compatible_modifiers()
		return rv
	
	
	def strip(self):
		# Returns default action or action assigned to first modifier
		if self.default:
			return self.default.strip()
		if len(self.order) > 0:
			return self.mods[self.order[0]].strip()
		# Empty ModeModifier
		return NoAction()
	
	
	def compress(self):
		if self.default:
			self.default = self.default.compress()
		for button in self.mods:
			self.mods[button] = self.mods[button].compress()
		return self
	
	
	def __str__(self):
		rv = [ ]
		for key in self.mods:
			rv += [ key.name, self.mods[key] ]
		if self.default is not None:
			rv += [ self.default ]
		return "<Modifier '%s', %s>" % (self.COMMAND, rv)
	
	__repr__ = __str__
	
	
	def describe(self, context):
		if self.name: return self.name
		l = []
		if self.default : l.append(self.default)
		for x in self.order:
			l.append(self.mods[x])
		return "\n".join([ x.describe(context) for x in l ])
	
	
	def to_string(self, multiline=False, pad=0):
		if multiline:
			rv = [ (" " * pad) + "mode(" ]
			for key in self.mods:
				a_str = self.mods[key].to_string(True).split("\n")
				a_str[0] = (" " * pad) + "  " + (key.name + ",").ljust(11) + a_str[0]	# Key has to be one of SCButtons
				for i in xrange(1, len(a_str)):
					a_str[i] = (" " * pad) + "  " + a_str[i]
				a_str[-1] = a_str[-1] + ","
				rv += a_str
			if self.default is not None:
				a_str = [
					(" " * pad) + "  " + x
					for x in  self.default.to_string(True).split("\n")
				]
				rv += a_str
			if rv[-1][-1] == ",":
				rv[-1] = rv[-1][0:-1]
			rv += [ (" " * pad) + ")" ]
			return "\n".join(rv)
		else:
			rv = [ ]
			for key in self.mods:
				rv += [ key.name, self.mods[key].to_string(False) ]
			if self.default is not None:
				rv += [ self.default.to_string(False) ]
			return "mode(" + ", ".join(rv) + ")"
	
	
	def select(self, mapper):
		"""
		Selects action by pressed button.
		"""
		for b in self.order:
			if mapper.is_pressed(b):
				return self.mods[b]
		return self.default
	
	
	def select_b(self, mapper):
		"""
		Same as select but returns button as well.
		"""
		for b in self.order:
			if mapper.is_pressed(b):
				return b, self.mods[b]
		return None, self.default
	
	
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
		if sel is not self.old_gyro:
			if self.old_gyro:
				self.old_gyro.gyro(mapper, 0, 0, 0, *q)
			self.old_gyro = sel
		return sel.gyro(mapper, pitch, yaw, roll, *q)
	
	
	def pad(self, mapper, position, what):
		return self.select(mapper).pad(mapper, position, what)
	
	
	def whole(self, mapper, x, y, what):
		if what == STICK:
			if abs(x) < ModeModifier.MIN_STICK and abs(y) < ModeModifier.MIN_STICK:
				for b in self.held_sticks:
					b.whole(mapper, 0, 0, what)
				self.held_sticks.clear()
			else:
				self.held_sticks.add(self.select(mapper))
				for b in self.held_sticks:
					b.whole(mapper, x, y, what)
		else:
			return self.select(mapper).whole(mapper, x, y, what)


class DoubleclickModifier(Modifier):
	COMMAND = "doubleclick"
	DEAFAULT_TIMEOUT = 0.2
	TIMEOUT_KEY = "time"
	PROFILE_KEY_PRIORITY = 3
	
	def __init__(self, doubleclickaction, normalaction=None, time=None):
		Modifier.__init__(self)
		self.action = doubleclickaction
		self.normalaction = normalaction or NoAction()
		self.holdaction = NoAction()
		self.actions = ( self.action, self.normalaction, self.holdaction )
		self.timeout = time or DoubleclickModifier.DEAFAULT_TIMEOUT
		self.haptic = None    # Set only with HoldModifier subclass
		self.waiting = False
		self.pressed = False
		self.active = None
	
	
	def encode(self):
		if self.normalaction:
			rv = self.normalaction.encode()
		else:
			rv = {}
		rv[DoubleclickModifier.COMMAND] = self.action.encode()
		if self.holdaction:
			rv[HoldModifier.COMMAND] = self.holdaction.encode()
		if self.timeout != DoubleclickModifier.DEAFAULT_TIMEOUT:
			rv[DoubleclickModifier.TIMEOUT_KEY] = self.timeout
		if self.name:
			rv[NameModifier.COMMAND] = self.name
		return rv
	
	
	def get_child_actions(self):
		return self.actions
	
	
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
		return self._mod_to_string(Action.strip_defaults(self), multiline, pad)
	
	
	def button_press(self, mapper):
		self.pressed = True
		if self.waiting:
			# Double-click happened
			mapper.remove_scheduled(self.on_timeout)
			self.waiting = False
			self.active = self.action
			self.active.button_press(mapper)
		else:
			# First click, start the timer
			self.waiting = True
			mapper.schedule(self.timeout, self.on_timeout)
	
	
	def button_release(self, mapper):
		self.pressed = False
		if self.waiting and self.active is None and not self.action:
			# In HoldModifier, button released before timeout
			mapper.remove_scheduled(self.on_timeout)
			self.waiting = False
			if self.normalaction:
				self.normalaction.button_press(mapper)
				self.normalaction.button_release(mapper)
		elif self.active:
			# Released held button
			self.active.button_release(mapper)
			self.active = None
	
	
	def on_timeout(self, mapper, *a):
		if self.waiting:
			self.waiting = False
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


class HoldModifier(DoubleclickModifier, HapticEnabledAction):
	# Hold modifier is implemented as part of DoubleclickModifier, because
	# situation when both are assigned to same button needs to be treated
	# specially.
	COMMAND = "hold"
	PROFILE_KEY_PRIORITY = 4

	def __init__(self, holdaction, normalaction=None, time=None):
		DoubleclickModifier.__init__(self, NoAction(), normalaction, time)
		HapticEnabledAction.__init__(self)
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
	
	
	def encode(self):
		rv = Modifier.encode(self)
		rv[SensitivityModifier.PROFILE_KEYS[0]] = self.speeds
		return rv
	
	
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
		while speeds[-1] == 1.0:
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
	
	
	def encode(self):
		rv = Modifier.encode(self)
		pars = self.strip_defaults()
		pars[0] = nameof(pars[0])
		rv[FeedbackModifier.COMMAND] = pars
		return rv


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


	def encode(self):
		rv = Modifier.encode(self)
		rv[RotateInputModifier.COMMAND] = self.angle
		return rv


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
		self._weights = [ multiplier ** x for x in reversed(xrange(level)) ]
		self._w_sum = sum(self._weights)
		self._last_pos = 0
		self._moving = False
	
	
	def __str__(self):
		return "<Smooth %s>" % (self.action,)
	
	
	def describe(self, context):
		if self.name: return self.name
		return "%s (smooth)" % (self.action.describe(context),)
	
	
	def encode(self):
		rv = Modifier.encode(self)
		rv[SmoothModifier.COMMAND] = [ self.level, self.multiplier, self.filter ]
		return rv
	
	
	@staticmethod
	def decode(data, a, *b):
		pars = data[SmoothModifier.COMMAND] + [ a ]
		return SmoothModifier(*pars)
	
	
	def _get_pos(self):
		""" Computes average x,y from all accumulated positions """
		x = sum(( self._deq_x[i] * self._weights[i] for i in xrange(self.level) ))
		y = sum(( self._deq_y[i] * self._weights[i] for i in xrange(self.level) ))
		return x / self._w_sum, y / self._w_sum
	
	
	def whole(self, mapper, x, y, what):
		if mapper.is_touched(what):
			if mapper.was_touched(what):
				# Pressed for longer time
				self._deq_x.append(x)
				self._deq_y.append(y)
				x, y = self._get_pos()
			else:
				# Just pressed - fill deque with current position
				for i in xrange(self.level):
					self._deq_x.append(x)
					self._deq_y.append(y)
			if abs(x + y - self._last_pos) > self.filter:
				self.action.whole(mapper, x, y, what)
			self._last_pos = x + y
		else:
			# Pad was just released
			x, y = self._get_pos()
			self.action.whole(mapper, x, y, what)
			self._last_pos = 0


class CircularModifier(Modifier, WholeHapticAction):
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
		Modifier.__init__(self, *params)
		WholeHapticAction.__init__(self)
	
	
	def _mod_init(self):
		self.angle = None		# Last known finger position
		self.speed = 1.0
	
	
	def encode(self):
		rv = Modifier.encode(self)
		rv[CircularModifier.COMMAND] = True
		return rv
	
	
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
				if self.haptic:
					WholeHapticAction.change(self, mapper, angle * 10000, 0)
			# Apply bulgarian constant
			angle *= 10000.0
			# Apply movement to child action
			self.action.change(mapper, -angle * self.speed, 0)
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
	
	
	def encode(self):
		rv = Modifier.encode(self)
		rv[CircularAbsModifier.COMMAND] = True
		return rv
	
	
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
			self.travelled = 0
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
						WholeHapticAction.change(self, mapper, diff * 10000, 0)
				self.angle = angle
			# Apply actual constant
			angle *= STICK_PAD_MAX / PI
			# Set axis on child action
			self.action.axis(mapper, angle * self.speed, 0)
			mapper.force_event.add(FE_PAD)
