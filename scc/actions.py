#!/usr/bin/env python2
"""
SC Controller - Actions

Action describes what should be done when event from physical controller button,
stick, pad or trigger is generated - typicaly what emulated button, stick or
trigger should be pressed.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.tools import ensure_size, quat2euler, anglediff
from scc.tools import circle_to_square, clamp, nameof
from scc.uinput import Keys, Axes, Rels
from scc.lib import xwrappers as X
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX, STICK_PAD_MIN_HALF
from scc.constants import STICK_PAD_MAX_HALF, TRIGGER_MIN, TRIGGER_HALF
from scc.constants import HIPFIRE_NORMAL, HIPFIRE_SENSIBLE, HIPFIRE_EXCLUSIVE
from scc.constants import LEFT, RIGHT, CPAD, STICK, PITCH, YAW, ROLL
from scc.constants import PARSER_CONSTANTS, ControllerFlags
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import TRIGGER_CLICK, TRIGGER_MAX
from scc.constants import SCButtons
from scc.aliases import ALL_BUTTONS as GAMEPAD_BUTTONS
from math import sqrt, sin, cos, atan2, pi as PI

import sys, time, logging, inspect
log = logging.getLogger("Actions")

# Default delay after action, if used in macro. May be overriden using sleep() action.
DEFAULT_DELAY = 0.01
MOUSE_BUTTONS = ( Keys.BTN_LEFT, Keys.BTN_MIDDLE, Keys.BTN_RIGHT, Keys.BTN_SIDE, Keys.BTN_EXTRA )
TRIGGERS = ( Axes.ABS_Z, Axes.ABS_RZ )


class Action(object):
	"""
	Action is what actually does something in SC-Controller. User can assotiate
	one or more Action to each available button, stick or pad in profile file.
	"""
	
	# Static dict of all available actions, filled later
	ALL = {}	# used by action parser
	PKEYS = {}	# used by profile parser
	
	# Used everywhere, but mainly in parser, to convert strings
	# to Action classes and back
	COMMAND = None
	
	# Additionaly, action can have aliases that are recognized by parser
	# ALIASES = ("x", "y", "z")
	
	# If action class has static 'decode' method defined, profile parser 
	# will look for matching key in profile nodes and call this method to
	# decode action stored in profile.
	# Normaly, key to look for is same as COMMAND, but this can be overriden
	# by setting PROFILE_KEYS to tuple. Additionaly, PROFILE_KEY_PRIORITY can
	# be used to set which modifier should be parsed first.
	# This is used mainly by modifiers
	#
	PROFILE_KEY_PRIORITY = 0	# default one. Loewer is parsed first
	# PROFILE_KEYS = ("foo", "bar")
	#
	# @staticmethod
	# def decode(jsondatta, action, parser, profile_version):
	# 	...
	# 	return action
	
	# "Action Context" constants
	AC_BUTTON	= 1 << 0
	AC_STICK	= 1 << 2
	AC_TRIGGER	= 1 << 3
	AC_GYRO		= 1 << 4
	AC_PAD		= 1 << 5
	AC_OSD		= 1 << 8
	AC_OSK		= 1 << 9	# On screen keyboard
	AC_MENU		= 1 << 10	# Menu Item
	AC_SWITCHER	= 1 << 11	# Autoswitcher display
	#		bit 	09876543210
	AC_ALL		= 0b10111111111	# ALL means everything but OSK
	
	
	# See get_compatible_modifiers
	MOD_CLICK		= 1 << 0
	MOD_OSD			= 1 << 1
	MOD_FEEDBACK	= 1 << 2
	MOD_DEADZONE	= 1 << 3
	MOD_SENSITIVITY	= 1 << 4
	MOD_SENS_Z		= 1 << 5	# Sensitivity of 3rd axis
	MOD_ROTATE		= 1 << 6
	MOD_POSITION	= 1 << 7
	MOD_SMOOTH		= 1 << 8
	MOD_BALL		= 1 << 9
	
	def __init__(self, *parameters):
		self.parameters = parameters
		self.name = None
		self.delay_after = DEFAULT_DELAY
		# internal, insignificant and never saved value used only by editor.
		# Has to be set to iterable of callbacks to do something usefull;
		# Callbacks in lilst are called with cb(app, action) after action is
		# set while editting the profile.
		self.on_action_set = None
	
	
	@staticmethod
	def register(action_cls, prefix=None):
		"""
		Registers action class. Basically, adds it to Action.ALL dict.
		If prefix is specified, action is registered as Prefix.COMMAND.
		"""
		dct = Action.ALL
		if prefix:
			if not prefix in Action.ALL:
				Action.ALL[prefix] = {}
			dct = Action.ALL[prefix]
		if action_cls.COMMAND is not None:
			dct[action_cls.COMMAND] = action_cls
			if hasattr(action_cls, "ALIASES"):
				for a in action_cls.ALIASES:
					dct[a] = action_cls
		
		if hasattr(action_cls, "decode"):
			keys = (action_cls.COMMAND,)
			if hasattr(action_cls, "PROFILE_KEYS"):
				keys = action_cls.PROFILE_KEYS
			for k in keys:
				Action.PKEYS[k] = action_cls
	
	
	@staticmethod
	def unregister_prefix(prefix):
		"""
		Unregisters prefix (as in Prefix.COMMAND) recognized by parser.
		Returns True on sucess, False if there is no such prefix registered.
		"""
		if prefix in Action.ALL:
			if type(Action.ALL) == dict:
				del Action.ALL[prefix]
				return True
		return False
	
	
	@staticmethod
	def register_all(module, prefix=None):
		""" Registers all actions from module """
		for x in dir(module):
			g = getattr(module, x)
			if hasattr(g, 'COMMAND'):
				Action.register(g, prefix=prefix)
	
	
	def encode(self):
		""" Called from json encoder """
		rv = { 'action' : self.to_string() }
		if self.name: rv['name'] = self.name
		return rv
	
	
	def get_child_actions(self):
		"""
		Returns iterable with all direct child actions or emtpty iterable if
		there are none. Child action is, for example, any action that DPadAction
		can choose from.
		
		May returns NoActions as well.
		"""
		return []	# Most will return this
	
	
	def get_all_actions(self):
		"""
		Returns generator with self, actions from get_child_actions and child
		actions of every child action, recursively including their children.
		"""
		yield self
		for c in self.get_child_actions():
			for cc in c.get_all_actions():
				yield cc
	
	
	def get_compatible_modifiers(self):
		"""
		Returns bit combination of MOD_* constants to indicate which modifier
		can be used with this action.
		Used by GUI.
		"""
		return 0
	
	
	def get_previewable(self):
		"""
		Returns True if action can be saved immediately to preview user changes.
		Used by editor.
		"""
		# Not for most of actions
		return False
	
	
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
		applied, when modifier doesn't do anything anymore.
		"""
		return self
	
	
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
	
	
	def whole_blocked(self, mapper, x, y, what):
		"""
		Special case called when ClickModifier is used and prevents 'whole'
		to be called because finger moves over non-pressed pad.
		"""
		pass
	
	
	def add(self, mapper, dx, dy):
		"""
		Called from BallModifier while virtual "ball" is rolling.
		
		Passed to 'whole' by default.
		"""
		self.whole(mapper, dx, dy, None)
	
	
	def change(self, mapper, dx, dy, what):
		"""
		Called from CircularModifier to indicate incremental (or decremental)
		change in value.
		
		'what' can be None.
		"""
		log.warn("Action %s can't handle incremental changes", self.__class__.__name__)
	
	
	def cancel(self, mapper):
		"""
		Called when profile is changed to give action chance to cancel
		long-running effects it may have created.
		"""
		pass
	
	
	def strip_defaults(self):
		"""
		Returns self.parameters list with all default values stripped from right
		side.
		That means, if last parameter is default, it's removed from list; if
		before-last parameter is default, it's removed as well; et cetera et
		cetera until first non-default parameter is reached.
		
		if as_strings is set to True, all parameters are converted to apropriate
		strings (x.name for enums, x.encode('string_escape') for strings, 
		"""
		argspec = inspect.getargspec(self.__class__.__init__)
		required_count = len(argspec.args) - len(argspec.defaults) - 1
		d = list(argspec.defaults)
		l = list(self.parameters)
		while len(d) and len(l) > required_count and d[-1] == l[-1]:
			d, l = d[:-1], l[:-1]
		return l
	
	
	@staticmethod
	def encode_parameters(parameters):
		"""
		Returns list with parameters encoded to strings in following way:
		- x.name for enums
		- str(x) numbers
		- '%s' % (x.encode('string_escape'),) for strings
		"""
		return [ Action._encode_parameter(p) for p in parameters ]
	
	
	@staticmethod
	def _encode_parameter(parameter):
		""" Encodes one parameter. Used by encode_parameters """
		if parameter in PARSER_CONSTANTS:
			return parameter
		if type(parameter) in (str, unicode):
			return "'%s'" % (str(parameter).encode('string_escape'),)
		return nameof(parameter)
	
	
	def trigger(self, mapper, position, old_position):
		"""
		Called when action is executed by pressing (or releasing) physical
		trigger.
		
		'position' contains current trigger position.
		'old_position' contains last known trigger position.
		"""
		log.warn("Action %s can't handle trigger event", self.__class__.__name__)


class RangeOP(object):
	"""
	Allows to specify and store axis range and then use it in modeshift
	instead of button.
	"""
	OPS = ("<", ">", "<=", ">=")
	
	def __init__(self, what, op, value):
		""" Raises ValueError if 'what' or 'op' is not supported value """
		self.what = what
		self.op = op
		self.value = value
		self.min = float(TRIGGER_MIN)
		self.max = float(TRIGGER_MAX)
		
		if op == "<":
			self.op_method = self.cmp_lt
		elif op == ">":
			self.op_method = self.cmp_gt
		elif op == "<=":
			self.op_method = self.cmp_le
		elif op == ">=":
			self.op_method = self.cmp_ge
		elif op == "ABS<":
			self.op_method = self.cmp_labs
		elif op == "ABS>":
			self.op_method = self.cmp_gabs
		else:
			raise ValueError("Unknown operator: '%s'" % (op, ))
		
		if what == SCButtons.LT:
			# TODO: Somehow unify names here, LT button is related to ltrig axis and so on
			self.axis_name = "ltrig"
		elif what == SCButtons.RT:
			self.axis_name = "rtrig"
		elif what == SCButtons.X:
			self.axis_name = "lpad_x"
			self.min, self.max = float(STICK_PAD_MIN), float(STICK_PAD_MAX)
		elif what == SCButtons.Y:
			self.axis_name = "lpad_y"
			self.min, self.max = float(STICK_PAD_MIN), float(STICK_PAD_MAX)
		elif what == STICK:
			# Most special case of all special cases
			self.axis_name = STICK
			op = "ABS" + op.replace("=", "")
			self.children = RangeOP(SCButtons.X, op, value), RangeOP(SCButtons.Y, op, value)
			self.min, self.max = float(STICK_PAD_MIN), float(STICK_PAD_MAX)
			self.op_method = self.cmp_or
		else:
			raise ValueError("'%s' is not trigger nor axis" % (nameof(what), ))
	
	def cmp_or(self, mapper):
		return any([ x(mapper) for x in self.children ])
	
	def cmp_gt(self, mapper):
		if mapper.state is None:
			return False
		state = float(getattr(mapper.state, self.axis_name)) / self.max
		return state > self.value
	
	def cmp_lt(self, mapper):
		if mapper.state is None:
			return False
		state = float(getattr(mapper.state, self.axis_name)) / self.max
		return state < self.value
	
	def cmp_ge(self, mapper):
		if mapper.state is None:
			return False
		state = float(getattr(mapper.state, self.axis_name)) / self.max
		return state >= self.value
	
	def cmp_le(self, mapper):
		if mapper.state is None:
			return False
		state = float(getattr(mapper.state, self.axis_name)) / self.max
		return state <= self.value
	
	def cmp_labs(self, mapper):
		if mapper.state is None:
			return False
		state = float(getattr(mapper.state, self.axis_name)) / self.max
		return abs(state) < self.value
	
	def cmp_gabs(self, mapper):
		if mapper.state is None:
			return False
		state = float(getattr(mapper.state, self.axis_name)) / self.max
		return abs(state) > self.value
	
	def __call__(self, mapper):
		return self.op_method(mapper)
	
	
	def __str__(self):
		return "%s %s %s" % (nameof(self.what), self.op, self.value)


class HapticEnabledAction(object):
	""" Action that can generate haptic feedback """
	def __init__(self):
		self.haptic = None
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_FEEDBACK
	
	
	def set_haptic(self, hd):
		self.haptic = hd
	
	
	def get_haptic(self):
		return self.haptic


class OSDEnabledAction(object):
	""" Action that displays some sort of OSD when executed """
	def __init__(self):
		self.osd_enabled = False
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_OSD
	
	
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
		return self.execute_named(self.SA, mapper, *a)
	
	# Prevent warnings when special action is bound to button
	def button_press(self, mapper): pass
	def button_release(self, mapper): pass


class AxisAction(Action):
	"""
	Action used to controll one output axis, such as one trigger
	or one axis of stick.
	"""
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
		Rels.REL_WHEEL : ("Mouse Wheel", "Up", "Down"),
		Rels.REL_HWHEEL : ("Horizontal Wheel", "Left", "Right"),
	}
	AXES_PAIRS = [
		(Axes.ABS_X, Axes.ABS_Y),
		(Axes.ABS_RX, Axes.ABS_RY),
		(Axes.ABS_HAT0X, Axes.ABS_HAT0Y)
	]
	X = [ Axes.ABS_X, Axes.ABS_RX, Axes.ABS_HAT0X ]
	Z = [ Axes.ABS_Z, Axes.ABS_RZ ]
	
	# Storage of positions per axis common for all AxisActions
	# This is important for cases when two different bindigs
	# are mapped to same axis using change() / CircularModifier
	# See https://github.com/kozec/sc-controller/issues/213
	old_positions = {}
	
	def __init__(self, id, min = None, max = None):
		Action.__init__(self, id, *strip_none(min, max))
		self.id = id
		self.speed = 1.0
		if self.id not in AxisAction.old_positions:
			AxisAction.old_positions[self.id] = 0
		if self.id in TRIGGERS:
			self.min = TRIGGER_MIN if min is None else min
			self.max = TRIGGER_MAX if max is None else max
		else:
			self.min = STICK_PAD_MIN if min is None else min
			self.max = STICK_PAD_MAX if max is None else max
	
	
	def set_speed(self, x, y, z):
		self.speed = x
	
	
	def get_speed(self):
		return (self.speed,)
	
	
	def get_previewable(self):
		return True
	
	
	def get_compatible_modifiers(self):	
		return Action.MOD_DEADZONE
	
	
	@staticmethod
	def get_axis_description(id, xy=False):
		"""
		Returns (axis_description, 'Negative', 'Positive'), where all strings
		are localized and Negative/Positive may be switched over depending on
		axis.
		"""
		if id in Axes or id in Rels:
			axis, neg, pos = "%s %s" % (id.name, _("Axis")), _("Negative"), _("Positive")
			if id in AxisAction.AXIS_NAMES:
				axis, neg, pos = [ _(x) for x in AxisAction.AXIS_NAMES[id] ]
			if xy:
				if id.name.endswith("X"): axis = _("%s X") % (axis,)
				if id.name.endswith("Y"): axis = _("%s Y") % (axis,)
			return axis, neg, pos
		elif hasattr(id, "name"):
			return _("Axis %s") % (id.name,), _("Negative"), _("Positive")
		else:
			return _("Axis %s") % (id,), _("Negative"), _("Positive")
	
	
	def get_axis(self):
		return self.id
	
	
	def describe(self, context):
		if self.name: return self.name
		axis, neg, pos = AxisAction.get_axis_description(self.id)
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
		mapper.gamepad.axisEvent(self.id, AxisAction.clamp_axis(self.id, self.max))
		mapper.syn_list.add(mapper.gamepad)
	
	
	def button_release(self, mapper):
		mapper.gamepad.axisEvent(self.id, AxisAction.clamp_axis(self.id, self.min))
		mapper.syn_list.add(mapper.gamepad)
	
	
	@staticmethod
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
	
	
	def axis(self, mapper, position, what):
		p = float(position * self.speed - STICK_PAD_MIN) / (STICK_PAD_MAX - STICK_PAD_MIN)
		p = int((p * (self.max - self.min)) + self.min)
		p = AxisAction.clamp_axis(self.id, p)
		AxisAction.old_positions[self.id] = p
		mapper.gamepad.axisEvent(self.id, p)
		mapper.syn_list.add(mapper.gamepad)
	
	
	def change(self, mapper, dx, dy, what):
		""" Called from CircularModifier """
		p = AxisAction.old_positions[self.id]
		p = clamp(-STICK_PAD_MAX, p + dx, STICK_PAD_MAX)
		AxisAction.old_positions[self.id] = p
		self.axis(mapper, p, None)
	
	
	def add(self, mapper, dx, dy):
		""" Called from BallModifier """
		self.axis(mapper, clamp(STICK_PAD_MIN, dx, STICK_PAD_MAX), None)
	
	
	def trigger(self, mapper, position, old_position):
		p = float(position * self.speed - TRIGGER_MIN) / (TRIGGER_MAX - TRIGGER_MIN)
		p = int((p * (self.max - self.min)) + self.min)
		p = AxisAction.clamp_axis(self.id, p)
		AxisAction.old_positions[self.id] = p
		mapper.gamepad.axisEvent(self.id, p)
		mapper.syn_list.add(mapper.gamepad)


class RAxisAction(AxisAction):
	""" Reversed AxisAction (outputs reversed values) """
	COMMAND = "raxis"
	
	def __init__(self, id, min = None, max = None):
		AxisAction.__init__(self, id, min, max)
		self.min, self.max = self.max, self.min
	
	
	def describe(self, context):
		if self.name: return self.name
		axis, neg, pos = AxisAction.get_axis_description(self.id)
		if context in (Action.AC_STICK, Action.AC_PAD):
			xy = "X" if self.parameters[0] in AxisAction.X else "Y"
			return _("%s %s (reversed)") % (axis, xy)
		return _("Reverse %s Axis") % (axis,)


class HatAction(AxisAction):
	"""
	Works as AxisAction, but has values preset to emulate emulate movement in
	either only positive or only negative half of range.
	"""
	COMMAND = None
	def describe(self, context):
		if self.name: return self.name
		axis, neg, pos = AxisAction.get_axis_description(self.id)
		if "up" in self.COMMAND or "left" in self.COMMAND:
			return "%s %s" % (axis, neg)
		else:
			return "%s %s" % (axis, pos)
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s(%s)" % (self.COMMAND, self.id)


class HatUpAction(HatAction):
	COMMAND = "hatup"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MIN + 1)

class HatDownAction(HatAction):
	COMMAND = "hatdown"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MAX - 1)

class HatLeftAction(HatAction):
	COMMAND = "hatleft"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MIN + 1)
	
class HatRightAction(HatAction):
	COMMAND = "hatright"
	def __init__(self, id, *a):
		HatAction.__init__(self, id, 0, STICK_PAD_MAX - 1)


class WholeHapticAction(HapticEnabledAction):
	"""
	Helper class for actions that are generating haptic 'rolling clicks' as
	finger moves over pad.
	MouseAction, CircularModifier, XYAction and BallModifier currently.
	"""
	def __init__(self):
		HapticEnabledAction.__init__(self)
		self.reset_wholehaptic()
	
	
	def change(self, mapper, dx, dy, what):
		self._ax += dx
		self._ay += dy
		
		distance = sqrt(self._ax * self._ax + self._ay * self._ay)
		if distance > self.haptic.frequency:
			self._ax = self._ay = 0
			mapper.send_feedback(self.haptic)	
	
	
	def add(self, mapper, dx, dy):
		self.change(mapper, dx, dy, None)
	
	
	def reset_wholehaptic(self):
		self._ax = self._ay = 0.0


class MouseAction(WholeHapticAction, Action):
	"""
	Controlls mouse movement in either vertical or horizontal direction
	or scroll wheel.
	"""
	COMMAND = "mouse"
	ALIASES = ("trackpad", )
	HAPTIC_FACTOR = 75.0	# Just magic number
	
	def __init__(self, axis=None, speed=None):
		Action.__init__(self, *strip_none(axis, speed))
		WholeHapticAction.__init__(self)
		self._mouse_axis = axis or None
		self._old_pos = None
		if speed:
			self.speed = (speed, speed)
		else:
			self.speed = (1.0, 1.0)
	
	
	def get_compatible_modifiers(self):
		return ( Action.MOD_SENSITIVITY | Action.MOD_SENS_Z | Action.MOD_ROTATE
				| Action.MOD_SMOOTH | Action.MOD_BALL | Action.MOD_FEEDBACK
				| Action.MOD_DEADZONE )
	
	
	def get_previewable(self):
		return True
	
	
	def get_axis(self):
		return self._mouse_axis
	
	
	def set_speed(self, x, y, z):
		self.speed = (x, y)
	
	
	def get_speed(self):
		return self.speed
	
	
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
		if self._mouse_axis in (Rels.REL_WHEEL, Rels.REL_HWHEEL):
			self.change(mapper, 100000, 0, None)
		else:
			self.change(mapper, 100, 0, None)
	
	
	def button_release(self, mapper):
		# Nothing
		pass
	
	
	def axis(self, mapper, position, what):
		self.change(mapper, position * MouseAbsAction.MOUSE_FACTOR, 0, what)
		mapper.force_event.add(FE_STICK)
	
	
	def pad(self, mapper, position, what):
		if mapper.is_touched(what):
			if self._old_pos and mapper.was_touched(what):
				d = position - self._old_pos[0]
				self.change(mapper, d, 0, what)
			self._old_pos = position, 0
		else:
			# Pad just released
			self._old_pos = None
	
	
	def change(self, mapper, dx, dy, what):
		self.add(mapper, dx, dy)
	
	
	def add(self, mapper, dx, dy):
		""" Called from BallModifier """
		if self.haptic:
			WholeHapticAction.change(self, mapper, dx, dy, None)
		
		dx, dy = dx * self.speed[0], dy * self.speed[1]
		if self._mouse_axis is None:
			mapper.mouse.moveEvent(dx, dy)
		elif self._mouse_axis == Rels.REL_X:
			mapper.mouse_move(dx, 0)
		elif self._mouse_axis == Rels.REL_Y:
			mapper.mouse_move(0, dx)
		elif self._mouse_axis == Rels.REL_WHEEL:
			mapper.mouse_wheel(0, -dx)
		elif self._mouse_axis == Rels.REL_HWHEEL:
			mapper.mouse_wheel(dx, 0)
	
	
	def whole(self, mapper, x, y, what):
		if what == STICK:
			mapper.mouse_move(x * self.speed[0] * 0.01, y * self.speed[1] * 0.01)
			mapper.force_event.add(FE_STICK)
		elif what == RIGHT and mapper.controller_flags() & ControllerFlags.HAS_RSTICK:
			mapper.mouse_move(x * self.speed[0] * 0.01, y * self.speed[1] * 0.01)
			mapper.force_event.add(FE_PAD)
		else:	# left or right pad
			if mapper.is_touched(what):
				if self._old_pos and mapper.was_touched(what):
					dx, dy = x - self._old_pos[0], self._old_pos[1] - y
					self.change(mapper, dx, dy, what)
				self._old_pos = x, y
			else:
				# Pad just released
				self._old_pos = None
	
	
	def gyro(self, mapper, pitch, yaw, roll, *a):
		if self._mouse_axis == YAW:
			mapper.mouse_move(yaw * -self.speed[0], pitch * -self.speed[1])
		else:
			mapper.mouse_move(roll * -self.speed[0], pitch * -self.speed[1])
	
	def trigger(self, mapper, position, old_position):
		delta = position - old_position
		self.add(mapper, delta, delta) # add() will figure out the axis from the action parameters

class MouseAbsAction(Action):
	"""
	Maps gyro rotation or position on pad to immediate mouse movement, similary
	to how GyroAbsAction maps gyro rotation to gamepad stick.
	
	Controlls mouse movement in either vertical or horizontal direction
	or scroll wheel.
	"""
	COMMAND = "mouseabs"
	MOUSE_FACTOR = 0.005	# Just random number to put default sensitivity into sane range
	
	def __init__(self, axis = None):
		Action.__init__(self, *strip_none(axis))
		self._mouse_axis = axis
		self._old_pos = None
		self.speed = 1.0, 1.0
	
	
	def get_compatible_modifiers(self):
		return ( Action.MOD_SENSITIVITY | Action.MOD_SENS_Z | Action.MOD_DEADZONE )
	
	
	def get_previewable(self):
		return True
	
	
	def get_axis(self):
		return self._mouse_axis
	
	
	def set_speed(self, x, y, *a):
		self.speed = x, y
	
	
	def get_speed(self):
		return self.speed
	
	
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
	
	
	def axis(self, mapper, position, what):
		mapper.force_event.add(FE_STICK)
		
		p = position * self.speed[0] * MouseAbsAction.MOUSE_FACTOR
		if self._mouse_axis == Rels.REL_X:
			mapper.mouse_move(p, 0)
		elif self._mouse_axis == Rels.REL_Y:
			mapper.mouse_move(0, p)
		elif self._mouse_axis == Rels.REL_WHEEL:
			mapper.mouse_wheel(0, -p)
		elif self._mouse_axis == Rels.REL_HWHEEL:
			mapper.mouse_wheel(p, 0)
	pad = axis
	
	
	def whole(self, mapper, x, y, what):
		dx = x * self.speed[0] * MouseAbsAction.MOUSE_FACTOR
		dy = y * self.speed[0] * MouseAbsAction.MOUSE_FACTOR
		mapper.mouse.moveEvent(dx, dy)


class AreaAction(Action, SpecialAction, OSDEnabledAction):
	"""
	Translates pad position to position in specified area of screen.
	"""
	SA = COMMAND = "area"
	
	def __init__(self, x1, y1, x2, y2):
		Action.__init__(self, x1, y1, x2, y2)
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
	
	
	def get_compatible_modifiers(self):
		return OSDEnabledAction.get_compatible_modifiers(self)
	
	
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
		if mapper.get_xdisplay() is None:
			log.warning("XServer is not available, cannot use 'AreaAction")
			return
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
	""" Uses *relative* gyroscope position as input for emulated axes """
	COMMAND = "gyro"
	
	def __init__(self, axis1, axis2=None, axis3=None):
		Action.__init__(self, axis1, *strip_none(axis2, axis3))
		self.axes = [ axis1, axis2, axis3 ]
		self.speed = (1.0, 1.0, 1.0)
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_SENSITIVITY | Action.MOD_SENS_Z
	
	
	def set_speed(self, x, y, z):
		self.speed = (x, y, z)
	
	
	def get_speed(self):
		return self.speed
	
	
	def gyro(self, mapper, *pyr):
		for i in (0, 1, 2):
			axis = self.axes[i]
			# 'gyro' cannot map to mouse, but 'mouse' does that.
			if axis in Axes or type(axis) == int:
				mapper.gamepad.axisEvent(axis, AxisAction.clamp_axis(axis, pyr[i] * self.speed[i] * -10))
				mapper.syn_list.add(mapper.gamepad)
	
	
	def describe(self, context):
		if self.name : return self.name
		rv = []
		
		if self.axes[0] in Rels:
			return _("Mouse")
		
		for x in self.axes:
			if x:
				s, trash, trash = AxisAction.get_axis_description(x)
				if s not in rv: rv.append(s)
		return "\n".join(rv)


class GyroAbsAction(HapticEnabledAction, GyroAction):
	""" Uses *absolute* gyroscope position as input for emulated axes """
	COMMAND = "gyroabs"
	MOUSE_FACTOR = 0.01	# Just random number to put default sensitivity into sane range
	
	def __init__(self, *blah):
		GyroAction.__init__(self, *blah)
		HapticEnabledAction.__init__(self)
		self.ir = [ 0, 0, None, 0 ]	# Initial rotation, last has to be determined
		self._was_oor = False
		self._deadzone_fn = None
	
	
	def reset(self):
		self.ir = [ None, None, None, None ]	# Determine everything
	
	
	def get_compatible_modifiers(self):
		return ( HapticEnabledAction.get_compatible_modifiers(self)
			| GyroAction.get_compatible_modifiers(self)
			| Action.MOD_DEADZONE )
	
	
	def get_previewable(self):
		return True
	
	GYROAXES = (0, 1, 2)
	def gyro(self, mapper, pitch, yaw, roll, q1, q2, q3, q4):
		if mapper.get_controller().flags & ControllerFlags.EUREL_GYROS:
			pyr = [q1 / 10430.37, q2 / 10430.37, q3 / 10430.37]	# 2**15 / PI
		else:
			pyr = list(quat2euler(q1 / 32767.0, q2 / 32767.0, q3 / 32767.0, q4 / 32767.0))
		for i in self.GYROAXES:
			self.ir[i] = self.ir[i] or pyr[i]
			pyr[i] = anglediff(self.ir[i], pyr[i]) * (2**15) * self.speed[2] * 2 / PI
		if self.haptic:
			oor = False # oor - Out Of Range
			for i in self.GYROAXES:
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
			for i in self.GYROAXES:
				pyr[i] = int(clamp(STICK_PAD_MIN, pyr[i], STICK_PAD_MAX))
		for i in self.GYROAXES:
			axis = self.axes[i]
			if axis in Axes or type(axis) == int:
				val = AxisAction.clamp_axis(axis, pyr[i] * self.speed[i])
				if self._deadzone_fn:
					val, trash = self._deadzone_fn(val, 0, STICK_PAD_MAX)
					val = int(val)
				mapper.gamepad.axisEvent(axis, val)
				mapper.syn_list.add(mapper.gamepad)
			elif axis == Rels.REL_X:
				mapper.mouse_move(AxisAction.clamp_axis(axis, pyr[i] * GyroAbsAction.MOUSE_FACTOR * self.speed[i]), 0)
			elif axis == Rels.REL_Y:
				mapper.mouse_move(0, AxisAction.clamp_axis(axis, pyr[i] * GyroAbsAction.MOUSE_FACTOR * self.speed[i]))


class ResetGyroAction(Action):
	"""
	Asks mapper to search for all GyroAbsActions in profile and adjust offsets
	so current pad orientation is treated as neutral.
	"""
	COMMAND = "resetgyro"
	
	def button_press(self, mapper):
		mapper.reset_gyros()
	
	
	def describe(self, context):
		if self.name : return self.name
		return _("Recenter Gyro")


class MultichildAction(Action):
	""" Mixin with nice looking to_string() method """
	
	def compress(self):
		self.actions = [ x.compress() for x in self.actions ]
		return self
	
	
	def get_child_actions(self):
		return self.actions
	
	
	def cancel(self, mapper):
		for a in self.actions:
			a.cancel(mapper)
	
	
	def to_string(self, multiline=False, pad=0, prefixparams=""):
		if multiline:
			rv = [ (" " * pad) + self.COMMAND + "(" + prefixparams.strip() ]
			pad += 2
			for a in strip_none(*self.actions):
				rv += [ a.to_string(True, pad) + ","]
			if rv[-1].endswith(","):
				rv[-1] = rv[-1][0:-1]
			pad -= 2
			rv += [ (" " * pad) + ")" ]
			return "\n".join(rv)
		return self.COMMAND + "(" + prefixparams + (", ".join([
			x.to_string() if x is not None else "None"
			for x in strip_none(*self.actions)
		])) + ")"


class TiltAction(MultichildAction):
	"""
	Activates one of 6 defined actions based on direction in
	which controller is tilted or rotated.
	"""
	COMMAND = "tilt"
	MIN = 0.75
	
	def __init__(self, *actions):
		"""
		Order of actions:
		 - Front faces down
		 - Front faces up
		 - Tilted left
		 - Tilted right
		 - Rotated left
		 - Rotated right
		"""
		MultichildAction.__init__(self, *strip_none(*actions))
		self.actions = ensure_size(6, actions, NoAction())
		self.states = [ None, None, None, None, None, None ]
		self.speed = (1.0, 1.0, 1.0)
	
	
	def set_speed(self, x, y, z):
		self.speed = (x, y, z)
	
	
	def get_speed(self):
		return self.speed
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_SENSITIVITY | Action.MOD_SENS_Z
	
	
	def gyro(self, mapper, *pyr):
		q1, q2, q3, q4 = pyr[-4:]
		pyr = quat2euler(q1 / 32767.0, q2 / 32767.0, q3 / 32767.0, q4 / 32767.0)
		for j in (0, 1, 2):
			i = j * 2
			if self.actions[i]:
				if pyr[j] < TiltAction.MIN * -1 / self.speed[j]:
					# Side faces down
					if not self.states[i]:
						# print self.actions[i]
						self.actions[i].button_press(mapper)
						self.states[i] = True
				elif self.states[i]:
					# Side no longer faces down
					self.actions[i].button_release(mapper)
					self.states[i] = False
			if self.actions[i+1]:
				if pyr[j] > TiltAction.MIN / self.speed[j]:
					# Side faces up
					if not self.states[i+1]:
						self.actions[i+1].button_press(mapper)
						self.states[i+1] = True
				elif self.states[i+1]:
					# Side no longer faces up
					self.actions[i+1].button_release(mapper)
					self.states[i+1] = False
	
	
	@staticmethod
	def decode(data, a, parser, *b):
		""" Called when decoding profile from json """
		args = [ parser.from_json_data(x) for x in data[TiltAction.COMMAND] ]
		return TiltAction(*args)
	
	
	def describe(self, context):
		if self.name : return self.name
		return _("Tilt")


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
	"""
	Action that outputs as button press and release.
	Button can be gamepad button, mouse button or keyboard key.
	"""
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
		
		Keys.KEY_PREVIOUSSONG	: "<< Song",
		Keys.KEY_STOP			: "Stop",
		Keys.KEY_PLAYPAUSE		: "Play/Pause",
		Keys.KEY_NEXTSONG		: "Song >>",
		Keys.KEY_VOLUMEDOWN		: "- Volume",
		Keys.KEY_VOLUMEUP		: "+ Volume"
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
	CIRCULAR_INTERVAL = 1000
	STICK_DEADZONE = 100
	
	def __init__(self, button1, button2 = None, minustrigger = None, plustrigger = None):
		Action.__init__(self, button1, *strip_none(button2, minustrigger, plustrigger))
		HapticEnabledAction.__init__(self)
		self.button = button1 or None
		self.button2 = button2 or None
		# minustrigger and plustrigger are not used anymore, __init__ takes
		# them only for backwards compatibility.
		# TODO: Remove backwards compatibility
		self._change = 0
		self._pressed_key = None
		self._released = True
	
	
	def describe(self, context):
		if self.name:
			return self.name
		elif self.button is Rels.REL_WHEEL:
			if len(self.parameters) < 2 or self.parameters[1] > 0:
				return _("Wheel UP")
			else:
				return _("Wheel DOWN")
		else:
			rv = [ ]
			for x in (self.button, self.button2):
				if x:
					rv.append(ButtonAction.describe_button(x, context=context))
			return ", ".join(rv)
	
	
	@staticmethod
	def describe_button(button, context=Action.AC_BUTTON):
		if button in ButtonAction.SPECIAL_NAMES:
			return _(ButtonAction.SPECIAL_NAMES[button])
		elif button in MOUSE_BUTTONS:
			return _("Mouse %s") % (button,)
		elif context == Action.AC_OSK:
			if button in ButtonAction.MODIFIERS_NAMES:
				return _(ButtonAction.MODIFIERS_NAMES[button])
			elif button in Keys:
				return button.name.split("_", 1)[-1].title()
			return ""
		elif button is None: # or isinstance(button, NoAction):
			return "None"
		elif button in Keys:
			return button.name.split("_", 1)[-1]
		else:
			return _("Button %i") % (button,)
	
	
	def describe_short(self):
		"""
		Used when multiple ButtonActions are chained together, for
		combinations like Alt+TAB
		"""
		if self.button in self.MODIFIERS_NAMES:
			# Modifiers are special case here
			return self.MODIFIERS_NAMES[self.button]
		return self.describe(Action.AC_BUTTON)
	
	
	def get_compatible_modifiers(self):
		# Allows feedback and OSD
		return Action.MOD_OSD | HapticEnabledAction.get_compatible_modifiers(self)
	
	
	@staticmethod
	def _button_press(mapper, button, immediate=False, haptic=None):
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
		if haptic:
			mapper.send_feedback(haptic)
	
	
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
		ButtonAction._button_press(mapper, self.button, haptic=self.haptic)
		if self.haptic:
			mapper.send_feedback(self.haptic)
	
	
	def button_release(self, mapper):
		ButtonAction._button_release(mapper, self.button)
	
	
	def whole(self, mapper, x, y, what):
		if what == STICK:
			# Stick used used as one big button (probably as part of ring bindings)
			if abs(x) < ButtonAction.STICK_DEADZONE and abs(y) < ButtonAction.STICK_DEADZONE:
				if self._pressed_key == self.button:
					self.button_release(mapper)
					self._pressed_key = None
			elif self._pressed_key != self.button:
				self.button_press(mapper)
				self._pressed_key = self.button
			return
		elif what in (LEFT, RIGHT):
			# Possibly special case, pressing with click() on entire pad
			if mapper.is_pressed(what) and not mapper.was_pressed(what):
				return self.button_press(mapper)
			elif not mapper.is_pressed(what) and mapper.was_pressed(what):
				return self.button_release(mapper)
		# Entire pad used as one big button
		if mapper.is_touched(what) and not mapper.was_touched(what):
			# Touched the pad
			self.button_press(mapper)
		if mapper.was_touched(what) and not mapper.is_touched(what):
			# Released the pad
			self.button_release(mapper)
	
	
	def axis(self, mapper, position, what):
		# Choses which key or button should be pressed or released based on
		# current stick position.
		
		# TODO: Remove this, convert it to DPAD internally
		if self._pressed_key == self.button and position > STICK_PAD_MIN_HALF:
			ButtonAction._button_release(mapper, self.button)
			self._pressed_key = None
		elif self._pressed_key != self.button and position <= STICK_PAD_MIN_HALF:
			ButtonAction._button_press(mapper, self.button)
			self._pressed_key = self.button
		if self.button2 is not None:
			if self._pressed_key == self.button2 and position < STICK_PAD_MAX_HALF:
				ButtonAction._button_release(mapper, self.button2)
				self._pressed_key = None
			elif self._pressed_key != self.button2 and position >= STICK_PAD_MAX_HALF:
				ButtonAction._button_press(mapper, self.button2)
				self._pressed_key = self.button2
	
	
	def trigger(self, mapper, p, old_p):
		# Choses which key or button should be pressed or released based on
		# current trigger position.
		# TODO: Remove this, call to TriggerAction instead
		if self.button2 is None:
			if p >= TRIGGER_HALF and old_p < TRIGGER_HALF:
				ButtonAction._button_press(mapper, self.button, haptic=self.haptic)
			elif p < TRIGGER_HALF and old_p >= TRIGGER_HALF:
				ButtonAction._button_release(mapper, self.button)
		else:
			if p >= TRIGGER_HALF and p < TRIGGER_CLICK:
				if self._pressed_key != self.button and self._released:
					ButtonAction._button_press(mapper, self.button)
					self._pressed_key = self.button
					self._released = False
			else:
				if self._pressed_key == self.button:
					ButtonAction._button_release(mapper, self.button)
					self._pressed_key = None
			if p > TRIGGER_CLICK and old_p < TRIGGER_CLICK:
				if self._pressed_key != self.button2:
					if self._pressed_key is not None:
						ButtonAction._button_release(mapper, self._pressed_key)
					ButtonAction._button_press(mapper, self.button2, haptic=self.haptic)
					self._pressed_key = self.button2
					self._released = False
			else:
				if self._pressed_key == self.button2:
					ButtonAction._button_release(mapper, self.button2)
					self._pressed_key = None
		
		if p <= TRIGGER_MIN:
			self._released = True
	
	
	def change(self, mapper, dx, dy, what):
		""" Makes sense with circular() modifier """
		self._change += dx
		if self._change < -ButtonAction.CIRCULAR_INTERVAL:
			self._change += ButtonAction.CIRCULAR_INTERVAL
			if self.button:
				ButtonAction._button_press(mapper, self.button)
				ButtonAction._button_release(mapper, self.button)
		elif self._change > ButtonAction.CIRCULAR_INTERVAL:
			self._change -= ButtonAction.CIRCULAR_INTERVAL
			if self.button2:
				ButtonAction._button_press(mapper, self.button2)
				ButtonAction._button_release(mapper, self.button2)


class MultiAction(MultichildAction):
	"""
	Two or more actions executed at once.
	Generated when parsing 'and'
	"""
	COMMAND = None
	PROFILE_KEYS = "actions",
	PROFILE_KEY_PRIORITY = -20	# First possible
	
	def __init__(self, *actions):
		self.actions = []
		self.name = None
		self._add_all(actions)
	
	
	@staticmethod
	def decode(data, a, parser, *b):
		""" Called when decoding profile from json """
		return MultiAction.make(*[
			parser.from_json_data(a) for a in data['actions']
		])
	
	
	@staticmethod
	def make(*a):
		"""
		Connects two or more actions, ignoring NoActions.
		Returns resulting MultiAction or just one action if every other
		parameter is NoAction or only one parameter was passed.
		Returns NoAction() if there are no parameters,
		or every parameter is NoAction.
		"""
		a = [ a for a in a if a.strip() ]	# 8-)
		# (^^ NoAction is eveluated as False)
		if len(a) == 0:
			return NoAction()
		if len(a) == 1:
			return a[0]
		return MultiAction(*a)
	
	
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
			if action.name : self.name = action.name
	
	
	def deduplicate(self):
		"""
		Removes duplicate actions. This is done by comparing string
		representations, so it's slow and ususally unnecesary, but can be
		usefull when importing.
		
		Returns new MultiAction, or, if only one action is left, returns
		that last action.
		"""
		actions, strings = [], []
		# TODO: Action comparison, don't use strings
		for x in self.actions:
			s = x.to_string()
			if s in strings: continue
			actions.append(x)
			strings.append(s)
		if len(actions) == 0:
			# Impossible
			return NoAction()
		elif len(actions) == 1:
			return actions[0]
		else:
			return MultiAction.make(*actions)
	
	
	def compress(self):
		nw = [ x.compress() for x in self.actions ]
		self.actions = nw
		return self
	
	
	def set_haptic(self, hapticdata):
		for a in self.actions:
			if a and hasattr(a, "set_haptic"):
				# Only first feedback-supporting action should do feedback
				a.set_haptic(hapticdata)
				return
	
	
	def get_haptic(self):
		for a in self.actions:
			if a and hasattr(a, "set_haptic"):
				return a.get_haptic()
		return None
	
	
	def set_speed(self, x, y, z):
		for a in self.actions:
			if hasattr(a, "set_speed"):
				a.set_speed(x, y, z)
	
	
	def get_speed(self):
		for a in self.actions:
			if hasattr(a, "set_speed"):
				return a.get_speed()
		return (1.0,)
	
	
	def is_key_combination(self):
		""" Returns True if all child actions are ButtonActions """
		if len(self.actions) == 0:
			return False
		for x in self.actions:
			if not isinstance(x, ButtonAction):
				return False
		return True
	
	
	def describe(self, context):
		if self.name: return self.name
		if self.is_key_combination():
			rv = []
			for a in self.actions:
				if isinstance(a, ButtonAction):
					rv.append(a.describe_short())
			return "+".join(rv)
		if len(self.actions) >= 2 and isinstance(self.actions[1], RingAction):
			# Special case, should be multiline
			return "\n".join([ x.describe(context) for x in self.actions ])
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
	
	def add(self, *p):
		for a in self.actions: a.add(*p)
	
	def change(self, *p):
		for a in self.actions: a.change(*p)
	
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


class DPadAction(MultichildAction, HapticEnabledAction):
	COMMAND = "dpad"
	PROFILE_KEY_PRIORITY = -10	# First possible
	
	DEFAULT_DIAGONAL_RANGE = 45
	MIN_DISTANCE_P2 = 2000000	# Power of 2 from minimal distance that finger
								# has to be from center
	
	SIDE_NONE = (None, None)
	SIDES = (
		# Just list of magic numbers that would have
		# to be computed on the fly otherwise
		# 0 - up, 1 - down, 2 - left, 3 - right
		( None, 1 ),		# Index 0, down
		( 2, 1 ),			# Index 1, down-left
		( 2, None),			# Index 2, left
		( 2, 0 ),			# Index 3, up-left
		( None, 0 ),		# Index 4, up
		( 3, 0 ),			# Index 5, up-right
		( 3, None ),		# Index 6, right
		( 3, 1 ),			# Index 7, down-right
		( None, 1 ),		# Index 8, same as 0
	)
	
	def __init__(self, *actions):
		MultichildAction.__init__(self, *actions)
		HapticEnabledAction.__init__(self)
		self.diagonal_rage = DPadAction.DEFAULT_DIAGONAL_RANGE
		if len(actions) > 0 and type(actions[0]) in (int, float):
			self.diagonal_rage = clamp(1, int(actions[0]), 89)
			actions = actions[1:]
		self.actions = self._ensure_size(actions)
		self.dpad_state = [ None, None ]	# X, Y
		self.side_before = None
		# Generate mapping of angle range -> index
		self.ranges = []
		normal_range = 90 - self.diagonal_rage
		i = 360-normal_range / 2
		for x in xrange(0, 9):
			r = normal_range if x % 2 == 0 else self.diagonal_rage
			i, j = (i + r) % 360, i
			self.ranges.append(( j, i, x % 8 ))
	
	
	def _ensure_size(self, actions):
		return ensure_size(4, actions, NoAction())
	
	
	@staticmethod
	def decode(data, a, parser, *b):
		""" Called when decoding profile from json """
		args = [ parser.from_json_data(x) for x in data[DPadAction.COMMAND] ]
		if len(args) > 4:
			a = DPad8Action(*args)
		else:
			a = DPadAction(*args)
		return a
	
	
	def to_string(self, multiline=False, pad=0, prefixparams=""):
		if self.diagonal_rage != DPadAction.DEFAULT_DIAGONAL_RANGE:
			return MultichildAction.to_string(self, multiline, pad,
					prefixparams = "%s, " % (self.diagonal_rage, ))
		return MultichildAction.to_string(self, multiline, pad)
	
	
	def get_compatible_modifiers(self):
		return (Action.MOD_CLICK | Action.MOD_ROTATE
			| Action.MOD_DEADZONE | Action.MOD_FEEDBACK )
	
	
	def describe(self, context):
		if self.name: return self.name
		# Two special, most used cases of dpad
		wsad = [ a.button for a in self.actions if isinstance(a, ButtonAction) ]
		if len(wsad) == 4:
			if wsad == [Keys.KEY_UP, Keys.KEY_DOWN, Keys.KEY_LEFT, Keys.KEY_RIGHT]:
				return _("Arrows")
			if wsad == [Keys.KEY_W, Keys.KEY_S, Keys.KEY_A, Keys.KEY_D]:
				return _("WSAD")
		return "DPad"
	
	
	def compute_side(self, x, y):
		""" Computes which sides of dpad are supposed to be active """
		## dpad(up, down, left, right)
		## dpad8(up, down, left, right, upleft, upright, downleft, downright)
		side = self.SIDE_NONE
		if x*x + y*y > self.MIN_DISTANCE_P2:
			# Compute angle from center of pad to finger position
			angle = (atan2(x, y) * 180.0 / PI) + 180
			# Translate it to index
			index = 0
			for a1, a2, i in self.ranges:
				if angle >= a1 and angle < a2:
					index = i
					break
			side = self.SIDES[index]
		return side
	
	
	def whole(self, mapper, x, y, what):
		if self.haptic:
			# Called like this just so there is not same code on two places
			side = self.whole_blocked(mapper, x, y, what)
		else:
			side = self.compute_side(x, y)
		
		for i in (0, 1):
			if side[i] != self.dpad_state[i] and self.dpad_state[i] is not None:
				if self.actions[self.dpad_state[i]] is not None:
					self.actions[self.dpad_state[i]].button_release(mapper)
				self.dpad_state[i] = None
			if side[i] is not None and side[i] != self.dpad_state[i]:
				if self.actions[side[i]] is not None:
					self.actions[side[i]].button_press(mapper)
				self.dpad_state[i] = side[i]
	
	
	def whole_blocked(self, mapper, x, y, what):
		if self.haptic:
			side = self.compute_side(x, y)
			if self.side_before != side:
				self.side_before = side
				mapper.send_feedback(self.haptic)
			return side
		return None
	
	
	def change(self, mapper, dx, dy, what):
		self.whole(mapper, dx, -dy, what)


class DPad8Action(DPadAction):
	COMMAND = "dpad8"
	PROFILE_KEYS = ()
	
	SIDE_NONE = None
	SIDES = (
		# Another list of magic numbers that would have`
		# to be computed on the fly otherwise
		1,	# index 0 - down
		6,	# index 1 - down-left
		2,	# index 2 - left
		4,	# index 3 - up-left
		0,	# index 4 - up
		5,	# index 5 - up-right
		3,	# index 6 - right
		7,	# index 7 - downright
		1,	# index 8 - same as 0
	)
	
	
	def _ensure_size(self, actions):
		return ensure_size(8, actions, NoAction())
	
	
	def describe(self, context):
		if self.name: return self.name
		return "8-Way DPad"
	
	
	def whole(self, mapper, x, y, what):
		side = self.compute_side(x, y)
		
		# 8-way dpad presses only one button at time, so only one index
		# in dpad_state is used.
		if side != self.dpad_state[0]:
			if self.dpad_state[0] is not None:
				self.actions[self.dpad_state[0]].button_release(mapper)
			if side is not None:
				self.actions[side].button_press(mapper)
			self.dpad_state[0] = side


class RingAction(MultichildAction):
	"""
	Ring action splits pad into "inner" and "outer" ring and allow binding
	two different child actions in same way as DPadAction does.
	
	Combining RingAction with two DPad8Actions allows to assign
	up to 16 different bindings to one pad.
	"""
	COMMAND = "ring"
	PROFILE_KEY_PRIORITY = -10	# First possible
	DEFAULT_RADIUS = 0.5
	
	
	def __init__(self, *params):
		# 1st parameter may be inner ring radius (0.1 to 0.9), defaults to 50%
		# of pad diameter.
		self.radius = RingAction.DEFAULT_RADIUS
		if len(params) > 1 and type(params[0]) in (int, float):
			self.radius = float(params[0])
			params = params[1:]
		MultichildAction.__init__(self, *params)
		self.actions = ensure_size(2, params, NoAction())
		self.inner, self.outer = self.actions
		self._radius_m = STICK_PAD_MAX * self.radius	# radius, multiplied
		self._active = NoAction()
	
	
	def compress(self):
		self.inner = self.inner.compress()
		self.outer = self.outer.compress()
		return self
	
	
	@staticmethod
	def decode(data, a, parser, *b):
		""" Called when decoding profile from json """
		args, data = [], data[RingAction.COMMAND]
		if 'radius' in data: args.append(float(data['radius']))
		args.append(parser.from_json_data(data['inner']) if 'inner' in data else NoAction())
		args.append(parser.from_json_data(data['outer']) if 'outer' in data else NoAction())
		return RingAction(*args)
	
	
	def get_compatible_modifiers(self):
		return 0
	
	
	def describe(self, context):
		if self.name: return self.name
		lines = [ x.describe(Action.AC_BUTTON) for x in self.actions if x ]
		if any(["\n" in l for l in lines ]):
			return " / ".join([ l for l in lines ])
		else:
			return "\n".join([ l for l in lines ])
	
	
	def to_string(self, multiline=False, pad=0):
		if self.radius != RingAction.DEFAULT_RADIUS:
			return MultichildAction.to_string(self, multiline, pad, "%s, " % (self.radius,))
		else:
			return MultichildAction.to_string(self, multiline, pad)
	
	
	def whole(self, mapper, x, y, what):
		if what == STICK or mapper.is_touched(what):
			angle = atan2(x, y)
			distance = sqrt(x*x + y*y)
			if distance < self._radius_m:
				# Inner radius
				action = self.inner
				distance /= self.radius
			else:
				action = self.outer
				distance = (distance - self._radius_m) / (1.0 - self.radius)
			x = distance * sin(angle)
			y = distance * cos(angle)
			
			if action == self._active:
				action.whole(mapper, x, y, what)
			elif what == STICK:
				# Stck crossed radius border, so active action is changing.
				# Simulate centering stick for former...
				self._active.whole(mapper, 0, 0, what)
				# ... and moving it back for new active child action
				action.whole(mapper, x, y, what)
				self._active = action
			else:
				# Finger crossed radius border, so active action is changing.
				# Simulate releasing pad for former...
				mapper.set_button(what, False)
				self._active.whole(mapper, 0, 0, what)
				# ... and touching it for new active child action
				was = mapper.was_touched(what)
				mapper.set_button(what, True)
				mapper.set_was_pressed(what, False)
				action.whole(mapper, x, y, what)
				mapper.set_was_pressed(what, was)
				self._active = action
		elif mapper.was_touched(what):
			# Pad just released
			self._active.whole(mapper, x, y, what)
			self._active = NoAction()
		elif self._active and what == STICK and x == 0 and y == 0:
			# Stick is centered
			self._active.whole(mapper, x, y, what)
			self._active = NoAction()


class XYAction(WholeHapticAction, Action):
	"""
	Used for sticks and pads when actions for X and Y axis are different.
	"""
	COMMAND = "XY"
	PROFILE_KEYS = ("X", "Y")
	PROFILE_KEY_PRIORITY = -10	# First possible, but not before MultiAction
	STICK_REPEAT_INTERVAL = 0.01
	STICK_REPEAT_MIN = 10
	
	def __init__(self, x=None, y=None):
		Action.__init__(self, *strip_none(x, y))
		WholeHapticAction.__init__(self)
		self.x = x or NoAction()
		self.y = y or NoAction()
		self.actions = (self.x, self.y)
		self._old_distance = 0
		self._old_pos = None
		if hasattr(self.x, "add") or hasattr(self.y, "add"):
			self.add = self._add
	
	
	def get_compatible_modifiers(self):
		mods = ( Action.MOD_FEEDBACK | Action.MOD_SENSITIVITY
			| Action.MOD_ROTATE | Action.MOD_SMOOTH
			| self.x.get_compatible_modifiers()
			| self.y.get_compatible_modifiers()
		)
		if isinstance(self.x, AxisAction) and isinstance(self.y, AxisAction):
			if self.x.get_axis() in (Axes.ABS_X, Axes.ABS_Y, Axes.ABS_RX, Axes.ABS_RY):
				mods = (mods | Action.MOD_BALL) & ~Action.MOD_SMOOTH
		return mods
	
	
	def get_child_actions(self):
		return self.x, self.y
	
	
	@staticmethod
	def decode(data, action, parser, *a):
		""" Called when decoding profile from json """
		x = parser.from_json_data(data["X"]) if "X" in data else NoAction()
		y = parser.from_json_data(data["Y"]) if "Y" in data else NoAction()
		return XYAction(x, y)
	
	
	def compress(self):
		self.x = self.x.compress()
		self.y = self.y.compress()
		return self
	
	
	def set_haptic(self, hapticdata):
		supports = False
		if hasattr(self.x, "set_haptic"):
			self.x.set_haptic(hapticdata)
			supports = True
		if hasattr(self.y, "set_haptic"):
			self.y.set_haptic(hapticdata)
			supports = True
		if not supports:
			# Child action has no feedback support, do feedback here
			self.haptic = hapticdata
			self.big_click = hapticdata * 4
	
	
	def get_haptic(self):
		if hasattr(self.x, "set_haptic"):
			return self.x.get_haptic()
		if hasattr(self.y, "set_haptic"):
			return self.y.get_haptic()
		return self.haptic
	
	
	def set_speed(self, x, y, z):
		if hasattr(self.x, "set_speed"):
			self.x.set_speed(x, 1, 1)
		if hasattr(self.y, "set_speed"):
			self.y.set_speed(y, 1, 1)
	
	
	def get_speed(self):
		rv = [0, 0]
		if hasattr(self.x, "set_speed"): rv[0] = self.x.get_speed()[0]
		if hasattr(self.y, "set_speed"): rv[1] = self.y.get_speed()[0]
		return tuple(rv)
	
	
	def get_previewable(self):
		return self.x.get_previewable() and self.y.get_previewable()
	
	
	def _add(self, mapper, x, y):
		""" Not always available """
		if self.haptic:
			WholeHapticAction.add(self, mapper, x, y)
		if hasattr(self.x, "add"):
			self.x.add(mapper, x, 0)
		if hasattr(self.y, "add"):
			self.y.add(mapper, -y, 0)
		if self.haptic:
			WholeHapticAction.add(self, mapper, x, y)
	
	
	def whole(self, mapper, x, y, what):
		if self.haptic:
			distance = sqrt(x*x + y*y)
			is_close = distance > STICK_PAD_MAX * 2 / 3
			was_close = self._old_distance > STICK_PAD_MAX * 2 / 3
			if self._old_pos:
				WholeHapticAction.add(self, mapper,
					x - self._old_pos[0], y - self._old_pos[1])
			if is_close != was_close:
				mapper.send_feedback(self.big_click)
			
			self._old_distance = distance
			if mapper.is_touched(what):
				self._old_pos = x, y
			else:
				self._old_pos = None
		
		if mapper.controller_flags() & ControllerFlags.HAS_RSTICK and what == RIGHT:
			self.x.axis(mapper, x, what)
			self.y.axis(mapper, y, what)
			mapper.force_event.add(FE_PAD)
		elif what in (LEFT, RIGHT, CPAD):
			self.x.pad(mapper, x, what)
			self.y.pad(mapper, y, what)
		else:
			self.x.axis(mapper, x, what)
			self.y.axis(mapper, y, what)
	
	
	def describe(self, context):
		if self.name: return self.name
		rv = []
		if isinstance(self.x, AxisAction) and isinstance(self.y, AxisAction):
			if (self.x.id, self.y.id) in AxisAction.AXES_PAIRS:
				# Special cases for default stick bindings
				desc, trash, trash = AxisAction.get_axis_description(self.x.id)
				return desc
		if self.x: rv.append(self.x.describe(context))
		if self.y: rv.append(self.y.describe(context))
		if context in (Action.AC_STICK, Action.AC_PAD):
			return "\n".join(rv)
		return " ".join(rv)
	
	
	def to_string(self, multiline=False, pad=0):
		if multiline:
			rv = [ (" " * pad) + self.COMMAND + "(" ]
			rv += self.x.to_string(True, pad + 2).split("\n")
			rv += [ (" " * pad) + "," ]
			rv += self.y.to_string(True, pad + 2).split("\n")
			rv += [ (" " * pad) + ")" ]
			return "\n".join(rv)
		elif self.y:
			return self.COMMAND + "(" + (", ".join([ x.to_string() for x in (self.x, self.y) ])) + ")"
		else:
			return self.COMMAND + "(" + self.x.to_string() + ")"
	
	
	def __str__(self):
		return "<%s %s >" % (self.COMMAND, ", ".join([ str(x) for x in self.actions ]), )

	__repr__ = __str__


class RelXYAction(XYAction):
	"""
	XYAction with center positioned wherever finger touched first.
	See https://github.com/kozec/sc-controller/issues/390
	"""
	COMMAND = "relXY"
	
	def __init__(self, *a, **b):
		XYAction.__init__(self, *a, **b)
		self.origin_x, self.origin_y = 0, 0
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Joystick Camera")
	
	
	def whole(self, mapper, x, y, what):
		if what in (LEFT, RIGHT, CPAD):
			if not mapper.is_touched(what):
				return XYAction.whole(self, mapper, 0, 0, what)
			elif not mapper.was_touched(what):
				self.origin_x, self.origin_y = x, y
			x -= self.origin_x
			y -= self.origin_y
			return XYAction.whole(self, mapper, x, y, what)
		XYAction.whole(self, mapper, x, y, what)
	
	
	def get_compatible_modifiers(self):
		return (XYAction.get_compatible_modifiers(self) & ~Action.MOD_BALL)


class TriggerAction(Action, HapticEnabledAction):
	"""
	Used for sticks and pads when actions for X and Y axis are different.
	"""
	COMMAND = "trigger"
	PROFILE_KEYS = "levels",
	PROFILE_KEY_PRIORITY = -5
	
	def __init__(self, press_level, *params):
		Action.__init__(self, press_level, *params)
		HapticEnabledAction.__init__(self)
		self.press_level = int(press_level)
		if len(params) == 1:
			self.release_level = press_level
			self.action = params[0]
		elif len(params) == 2:
			self.release_level = params[0]
			self.action = params[1]
		else:
			raise TypeError("Invalid number of parameters")
		self.pressed = False
		# Having AxisAction as child of TriggerAction is special case,
		# child action recieves trigger events instead of button presses
		# and button_releases.
		self.child_is_axis = isinstance(self.action.strip(), AxisAction)
	
	
	@staticmethod
	def decode(data, a, parser, *b):
		""" Called when decoding profile from json """
		press_level, release_level = data[TriggerAction.PROFILE_KEYS[0]]
		return TriggerAction(press_level, release_level, a)
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_FEEDBACK
	
	
	def compress(self):
		self.action = self.action.compress()
		return self
	
	
	def _press(self, mapper):
		""" Called when trigger level enters active zone """
		self.pressed = True
		if self.haptic:
			mapper.send_feedback(self.haptic)
		if not self.child_is_axis:
			self.action.button_press(mapper)
	
	
	def _release(self, mapper, old_position):
		""" Called when trigger level leaves active zone """
		self.pressed = False
		if self.child_is_axis:
			self.action.trigger(mapper, 0, old_position)
		else:
			self.action.button_release(mapper)
	
	
	def trigger(self, mapper, position, old_position):
		# There are 3 modes that TriggerAction can work in
		if self.release_level > self.press_level:
			# Mode 1, action is 'pressed' if current level is
			# between press_level and release_level.
			if not self.pressed and position >= self.press_level and old_position < self.press_level:
				self._press(mapper)
			elif self.pressed and position > self.release_level and old_position <= self.release_level:
				self._release(mapper, old_position)
			elif self.pressed and position < self.press_level and old_position >= self.press_level:
				self._release(mapper, old_position)
		if self.release_level == self.press_level:
			# Mode 2, there is only press_level and action is 'pressed'
			# while current level is above it.
			if not self.pressed and position >= self.press_level and old_position < self.press_level:
				self._press(mapper)
			elif self.pressed and position < self.press_level and old_position >= self.press_level:
				self._release(mapper, old_position)
		if self.release_level < self.press_level:
			# Mode 3, action is 'pressed' if current level is above 'press_level'
			# and then released when it returns beyond 'release_level'.
			if not self.pressed and position >= self.press_level and old_position < self.press_level:
				self._press(mapper)
			elif self.pressed and position < self.release_level and old_position >= self.release_level:
				self._release(mapper, old_position)
		if self.child_is_axis and self.pressed:
			self.action.trigger(mapper, position, old_position)
	
	
	def describe(self, context):
		if self.name: return self.name
		return self.action.describe(context)
	
	
	def __str__(self):
		return "<Trigger %s-%s %s >" % (self.press_level, self.release_level, self.action)
	
	__repr__ = __str__

class HipfireAction(Action, HapticEnabledAction):
	"""
	Hip fire style trigger setting the two ranges for two different actions
	allowing activating the fully pressed action without activating partially pressed one
	"""

	COMMAND = "hipfire"
	PROFILE_KEYS = "levels",
	DEFAULT_TIMEOUT = 0.15
	DEFAULT_PARTIALPRESS_LEVEL = 50
	DEFAULT_FULLPRESS_LEVEL = 254
	DEFAULT_MODE = HIPFIRE_NORMAL
	TIMEOUT_KEY = "time"
	PROFILE_KEY_PRIORITY = -5
	
	def __init__(self, *params):
		Action.__init__(self, *params)
		HapticEnabledAction.__init__(self)
		# set default values in case is not provided
		self.partialpress_level = HipfireAction.DEFAULT_PARTIALPRESS_LEVEL
		self.fullpress_level = HipfireAction.DEFAULT_FULLPRESS_LEVEL
		self.mode = HipfireAction.DEFAULT_MODE
		self.timeout = HipfireAction.DEFAULT_TIMEOUT

		if len(params) >= 2:
			if type(params[0]) in (int, float):
				self.partialpress_level = int(params[0])
				if type(params[1]) in (int, float):
					self.fullpress_level = int(params[1])
					params = params[2:]
				else:
					params = params[1:]

			self.partialpress_action = params[0]
			self.fullpress_action = params[1]
			if len(params) >= 3:
				self.mode = params[2]
			if len(params) == 4:
				self.timeout = params[3]
		else:
			raise TypeError("Invalid number of parameters")

		if self.mode not in (HIPFIRE_NORMAL, HIPFIRE_EXCLUSIVE, HIPFIRE_SENSIBLE):
			raise ValueError("Invalid hipfire mode")
		self.partialpress_active = False
		self.range = "None"
		self.waiting_task = None
		self.sensible_state = "READY"
		self._partialpress_level = self.partialpress_level

	
	@staticmethod
	def decode(data, a, parser, *b):
		args = [ parser.from_json_data(data[HipfireAction.COMMAND]), a ]
		a = HipfireAction(*args)
		if HipfireAction.TIMEOUT_KEY in data:
			a.timeout = data[HipfireAction.TIMEOUT_KEY]
		return a

			
	def get_compatible_modifiers(self):
		return Action.MOD_FEEDBACK
	
	
	def compress(self):
		self.partialpress_action = self.partialpress_action.compress()
		self.fullpress_action = self.fullpress_action.compress()
		return self
	
	def on_timeout(self, mapper, *a):
		if self.waiting_task:
			self.waiting_task = None
			if self.range == "PARTIALPRESS":
				# Timeouted while inside partial press range
				if self.haptic:
					mapper.send_feedback(self.haptic)
				self._partial_press(mapper)
	
	def _partial_press(self, mapper):
		self.partialpress_active = True
		if self.haptic:
			mapper.send_feedback(self.haptic)
		self.partialpress_action.button_press(mapper)
	
	
	def _partial_release(self, mapper):
		self.partialpress_active = False
		if self.haptic:
			mapper.send_feedback(self.haptic)
		self.partialpress_action.button_release(mapper)
	
	def _full_press(self, mapper):
		if self.haptic:
			mapper.send_feedback(self.haptic)
		self.fullpress_action.button_press(mapper)
	
	def _full_release(self, mapper):
		if self.haptic:
			mapper.send_feedback(self.haptic)
		self.fullpress_action.button_release(mapper)
	
	
	def trigger(self, mapper, position, old_position):
		# Checks the current position of the trigger and apply the action based on three possible range: [None, PARTIALPRESS, FULLPRESS]

		# Checks full press first to prevent unnecessary conditional evaluation
		if position >= self.fullpress_level and old_position < self.fullpress_level:
			self.range = "FULLPRESS"
			# Entered now in full press range and activate fully pressed action
			
			# Checks if it's in exclusive mode and if partial press is active before activating
			if (self.mode == HIPFIRE_EXCLUSIVE) and self.partialpress_active: return

			self._full_press(mapper)
			# Cancel any pending timer to prevent partially pressed action from activating
			if self.waiting_task:
				mapper.cancel_task(self.waiting_task)
				self.waiting_task = None
		
		elif position < self.fullpress_level and old_position >= self.fullpress_level:
			self.range = "PARTIALPRESS"
			# left the full press range and released the fully pressed action
			self._full_release(mapper)	
		
		elif position >= self.partialpress_level:
			self.range = "PARTIALPRESS"
			# Entered now in partial press range and should start the timer
			# normal behavior. without the sensible trigger 
			if old_position < self.partialpress_level:
				# Cancels previous timer
				if self.waiting_task:
					mapper.cancel_task(self.waiting_task)
					self.waiting_task = None
				# Start the timer to execute the action if the full press range is not reached before timeout
				self.waiting_task = mapper.schedule(self.timeout, self.on_timeout)

			# Spliting conditional for treating the sensible mode
			# in this mode after reaching the partial press level, releasing the trigger a little will cause it to deactivate the action
			# allowing fast repeatly presses without needing to release the trigger the all the way back
			if self.mode == HIPFIRE_SENSIBLE:
				if position > old_position and self.sensible_state == "READY":
					## Create the new partial press point while pressing the trigger and the trigger is in its initial state
					self.new_partialpress_level = max(old_position, self.new_partialpress_level) - 45 # using a arbitrary value just for tests
				
				if self.sensible_state != "RELEASED" and position < self.new_partialpress_level and old_position >= self.new_partialpress_level:
					# Leaving the sensible range deactivating the action if it's already activated otherwise just schedule a short press
					self.sensible_state = "RELEASED"
					if self.waiting_task:
						mapper.cancel_task(self.waiting_task)
						self.waiting_task = None
						self._partial_press(mapper)
						mapper.schedule(0.02, self._partial_release)
					else:
						self._partial_release(mapper)

				elif self.sensible_state != "PRESSED" and position >= self.new_partialpress_level and old_position < self.new_partialpress_level:
					# Activate the action (schedule) again without needed to release the action until the partial press level
					self.sensible_state = "PRESSED"
					if self.waiting_task:
						mapper.cancel_task(self.waiting_task)
						self.waiting_task = None
					#start the timer to execute the action if the full press is not reached before timeout
					self.waiting_task = mapper.schedule(self.timeout, self.on_timeout)

		## Normal release of the partial press, deactivates the partially pressed action if it was active or if the time was still going schedule a short press 
		elif position < self.partialpress_level and old_position >= self.partialpress_level:
			self.range = "NONE"
			if self.waiting_task:
				mapper.cancel_task(self.waiting_task)
				self.waiting_task = None
				self._partial_press(mapper)
				mapper.schedule(0.02, self._partial_release)
			else:
				self._partial_release(mapper)

			# reset the sensible state
			self.sensible_state = "READY"
			self.new_partialpress_level = self.partialpress_level

	
	def describe(self, context):
		l = [ ]
		if self.partialpress_action:
			l += [ self.partialpress_action ]
		if self.fullpress_action:
			l += [ self.fullpress_action ]
		return "\n".join([ x.describe(context) for x in l ])
	
	
	def __str__(self):
		return "<Hipfire %s-%s %s %s %s >" % (self.partialpress_level, self.fullpress_level, self.partialpress_action, self.fullpress_action, self.mode)
	
	__repr__ = __str__


class NoAction(Action):
	"""
	Parsed from None.
	Singleton, treated as False in boolean ops.
	"""
	COMMAND = "None"
	ALIASES = (None, )
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


def strip_none(*lst):
	""" Returns lst without trailing None's and NoActions """
	while len(lst) and (lst[-1] is None or isinstance(lst[-1], NoAction)):
		lst = lst[0:-1]
	return lst


# Register actions from current module
Action.register_all(sys.modules[__name__])

# Import important action modules and register actions from them.
# (needs to be done at end as all this imports Action class from this module)
import scc.macros
Action.register_all(sys.modules['scc.macros'])
import scc.modifiers
Action.register_all(sys.modules['scc.modifiers'])
import scc.special_actions
Action.register_all(sys.modules['scc.special_actions'])
