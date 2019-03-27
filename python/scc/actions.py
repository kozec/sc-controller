#!/usr/bin/env python2
"""
SC Controller - Actions

Action describes what should be done when event from physical controller button,
stick, pad or trigger is generated - typicaly what emulated button, stick or
trigger should be pressed.
"""
import ctypes
from itertools import chain
from scc.constants import SCButtons, HapticPos
from scc.tools import find_library
from scc.parser import ParseError
from scc.lib import Enum

import logging
log = logging.getLogger("Actions")


class Parameter:
	class CParameterOE(ctypes.Structure):
		_fields_ = [
			("type", ctypes.c_uint32),
			("ref_count", ctypes.c_size_t),
		]
	
	CParameterOEp = ctypes.POINTER(CParameterOE)
	CParameterOEpp = ctypes.POINTER(CParameterOEp)
	
	PT_ERROR					= 0b000000001
	PT_CONSTANT					= 0b000000010
	PT_ACTION					= 0b000000100
	PT_RANGE					= 0b000001000
	PT_NONE						= 0b000010100
	PT_INT						= 0b000100000
	PT_FLOAT					= 0b001100000
	PT_STRING					= 0b010000000
	PT_TUPLE					= 0b100000000
	PT_ANY						= 0b111111110
	
	def __init__(self, value):
		if isinstance(value, Parameter.CParameterOEp):
			if (value.contents.type & Parameter.PT_ERROR) != 0:
				try:
					raise ValueError(lib_bindings.scc_error_get_message(CAPError(value)))
				finally:
					lib_bindings.scc_parameter_unref(value)
			if (value.contents.type & Parameter.PT_ANY) == 0:
				raise ValueError("Invalid parameter")
			self._cparam = value
		else:
			if type(value) == int:
				cparam = lib_actions.scc_new_int_parameter(value)
			elif type(value) == float:
				cparam = lib_actions.scc_new_float_parameter(value)
			elif type(value) == str:
				cparam = lib_actions.scc_new_string_parameter(value)
			elif type(value) == unicode:
				cparam = lib_actions.scc_new_string_parameter(value.encode("utf-8"))
			elif isinstance(value, Action):
				cparam = lib_actions.scc_new_action_parameter(value._caction)
			elif isinstance(value, Enum):
				print value.name
				cparam = lib_bindings.scc_get_const_parameter(value.name)
			else:
				raise TypeError("Cannot convert %s" % (repr(value),))
			self._cparam = cparam
	
	def __del__(self):
		lib_bindings.scc_parameter_unref(self._cparam)
		self._cparam = None
	
	def get_value(self):
		""" Returns python value """
		if (self._cparam.contents.type & Parameter.PT_ACTION) != 0:
			caction = lib_bindings.scc_parameter_as_action(self._cparam)
			lib_bindings.scc_action_ref(caction)
			return Action._from_c(caction)
		elif (self._cparam.contents.type & Parameter.PT_STRING) != 0:
			return lib_bindings.scc_parameter_as_string(self._cparam)
		elif (self._cparam.contents.type & Parameter.PT_INT) != 0:
			if (self._cparam.contents.type & Parameter.PT_FLOAT) == Parameter.PT_FLOAT:
				return round(lib_bindings.scc_parameter_as_float(self._cparam), 4)
			return lib_bindings.scc_parameter_as_int(self._cparam)
		elif (self._cparam.contents.type & Parameter.PT_TUPLE) != 0:
			count = lib_bindings.scc_parameter_tuple_get_count(self._cparam)
			return tuple((
				Parameter(lib_bindings.scc_parameter_ref(cp)).get_value()
				for cp in (
					lib_bindings.scc_parameter_tuple_get_child(self._cparam, i)
					for i in xrange(count)
				)
			))
		return None


class Action(object):
	class CActionOE(ctypes.Structure):
		_fields_ = [
			("flags", ctypes.c_uint32),
			("ref_count", ctypes.c_size_t),
		]
	
	CActionOEp = ctypes.POINTER(CActionOE)
	CActionOEpp = ctypes.POINTER(CActionOEp)
	
	AF_NONE					= 0b00000000
	AF_ERROR				= 0b00000001
	AF_ACTION				= 0b00001 << 9
	AF_MODIFIER				= 0b00010 << 9
	AF_SPECIAL_ACTION		= 0b00100 << 9
	
	def __init__(self, *args):
		"""
		Takes either CActionOEp instance or action parameters.
		If CActionOEp is passed, steals one reference.
		"""
		self._caction = None
		if len(args) == 1 and isinstance(args[0], Action.CActionOEp):
			caction = args[0]
		else:
			if self.__class__ in (Action, Modifier):
				raise TypeError("%s cannot be instantiated directly (use subclass)" % (self.__class__.__name__,))
			pars = [ Parameter(v) for v in args ]
			cpars = (Parameter.CParameterOEp * (len(pars)))()
			for i, par in enumerate(pars):
				cpars[i] = par._cparam
			caction = lib_bindings.scc_action_new_from_array(self.KEYWORD, len(pars),
								ctypes.cast(cpars, Parameter.CParameterOEpp))
		
		if caction.contents.flags == Action.AF_NONE:
			pass
		elif (caction.contents.flags & (Action.AF_ACTION | Action.AF_MODIFIER)) == 0:
			if (caction.contents.flags & Action.AF_ERROR) != 0:
				raise ParseError(lib_bindings.scc_error_get_message(CAPError(caction)))
			raise OSError("Invalid value returned by scc_parse_action (flags = 0x%x)" % caction.contents.flags)
		
		self._caction = caction
	
	def __del__(self):
		if self._caction:
			lib_bindings.scc_action_unref(self._caction)
			self._caction = None
	
	def to_string(self, multiline=False):
		""" Converts action back to string """
		return lib_actions.scc_action_to_string(self._caction).decode("utf-8")
	
	def compress(self):
		"""
		For most of actions, returns itself.
		
		For modifier that's not needed for execution (such as NameModifier
		or SensitivityModifier that already applied its settings), returns child
		action.
		"""
		caction = lib_bindings.scc_action_get_compressed(self._caction)
		if not caction:
			return self
		return Action._from_c(caction)
	
	def strip(self):
		# TODO: This? Is it still needed?
		return self
	
	def get_haptic(self):
		return HapticData(*self.haptic)
	
	def __str__(self):
		if self._caction is None: return "<C>"
		tpe = lib_bindings.scc_action_get_type(self._caction)
		pars = lib_actions.scc_action_to_string(self._caction)
		pars = pars.split("(", 1)[-1]
		if pars.endswith(")"): pars = pars[:-1]
		return "<%s, %s>" % (self.__class__.__name__, pars)
	
	__repr__ = __str__
	
	def __nonzero__(self):
		return True
	
	@staticmethod
	def parse(s):
		caction = lib_parse.scc_parse_action(s)
		if (caction.contents.flags & Action.AF_ERROR) != 0:
			try:
				raise OSError(lib_bindings.scc_error_get_message(CAPError(caction)))
			finally:
				lib_bindings.scc_action_unref(caction)
		return Action._from_c(caction)
	
	@staticmethod
	def _from_c(caction):
		tpe = lib_bindings.scc_action_get_type(caction)
		cls = KEYWORD_TO_ACTION.get(tpe, Action)
		if cls is Action:
			log.warning("Parsed unknown action type '%s'", tpe)
			instance = cls(caction)
			instance.KEYWORD = tpe
			return instance
		return cls(caction)
	
	def __getattr__(self, name):
		rv = lib_bindings.scc_action_get_property(self._caction, name)
		if not rv:
			raise AttributeError("%s '%s' has no property '%s'" % (
								self.__class__.__name__, self.KEYWORD, name))
		return Parameter(rv).get_value()
	
	# Stuff needed for backwards-compatibility with old python code follows
	def get_speed(self):
		return self.sensitivity


class CAPError(ctypes.Union):
	_fields_ = [
		('e1', Action.CActionOEp),
		('e2', Parameter.CParameterOEp),
	]


class HapticData(object):
	""" Simple container to hold haptic feedback settings """
	
	def __init__(self, position, amplitude=512, frequency=4, period=1024):
		"""
		'frequency' is used only when emulating touchpad and describes how many
		pixels should mouse travell between two feedback ticks.
		"""
		data = tuple([ position ] + [ int(x) for x in (amplitude, frequency, period) ])
		if data[0] not in HapticPos.__members__:
			raise ValueError("Invalid position: '%s'" % (data[0], ))
		for i in (1,3):
			if data[i] > 0x8000 or data[i] < 0:
				raise ValueError("Value out of range")
		self.data = data
	
	def with_position(self, position):
		""" Creates copy of HapticData with position value changed """
		trash, amplitude, frequency, period = self.data
		return HapticData(position, amplitude, frequency, period)
	
	def get_position(self):
		return HapticPos(self.data[0])
	
	def get_amplitude(self):
		return self.data[1]
	
	def get_frequency(self):
		return self.data[2]
	
	def get_period(self):
		return self.data[3]
	
	def __mul__(self, by):
		"""
		Allows multiplying HapticData by scalar to get same values
		with increased amplitude.
		"""
		position, amplitude, frequency, period = self.data
		amplitude = min(amplitude * by, 0x8000)
		return HapticData(position, amplitude, frequency, period)


class NoAction(Action):
	KEYWORD = "None"
	
	def __nonzero__(self):
		return False

class Modifier(Action):
	
	@property
	def child(self):
		c = lib_bindings.scc_action_get_child(self._caction)
		if not c:
			raise AttributeError("Action '%s' has no child" % (self.KEYWORD,))
		return Action._from_c(c)
	
	action = child	# backwards compatibility :(


class BallModifier(Modifier): KEYWORD = "ball"
class MenuAction(Action): KEYWORD = "menu"
class ChangeProfileAction(Action): KEYWORD = "profile"
class TapAction(Action): KEYWORD = "tap"
class MouseAbsAction(Action): KEYWORD = "mouseabs"
class SmoothModifier(Modifier): KEYWORD = "smooth"
class PressAction(Action): KEYWORD = "press"
class ReleaseAction(Action): KEYWORD = "release"
class TurnoffAction(Action): KEYWORD = "turnoff"
class AxisAction(Action): KEYWORD = "axis"
class RAxisAction(Action): KEYWORD = "raxis"
class HatUpAction(Action): KEYWORD = "hatup"
class HatDownAction(Action): KEYWORD = "hatdown"
class HatLeftAction(Action): KEYWORD = "hatleft"
class HatRightAction(Action): KEYWORD = "hatright"
class XYAction(Action): KEYWORD = "XY"
class RelXYAction(Action): KEYWORD = "relXY"
class Cycle(Action): KEYWORD = "cycle"
class Type(Action): KEYWORD = "type"
class ButtonAction(Action): KEYWORD = "button"
class DeadzoneModifier(Modifier): KEYWORD = "deadzone"
class MouseAction(Action): KEYWORD = "mouse"
class TrackpadAction(Action): KEYWORD = "trackpad"
class TrackballAction(Action): KEYWORD = "trackball"
class HoldModifier(Modifier): KEYWORD = "hold"
class DblclickModifier(Modifier): KEYWORD = "dblclick"
class SleepAction(Action): KEYWORD = "sleep"
class Repeat(Modifier): KEYWORD = "repeat"
class SensitivityModifier(Modifier): KEYWORD = "sens"
class FeedbackModifier(Modifier): KEYWORD = "feedback"
class ClickedModifier(Modifier): KEYWORD = "clicked"
class NameModifier(Modifier): KEYWORD = "name"
class TriggerAction(Action): KEYWORD = "trigger"
class DPadAction(Action): KEYWORD = "dpad"
class DPad8Action(Action): KEYWORD = "dpad8"
class DoubleclickModifier(Modifier): KEYWORD = "doubleclick"


class ModeModifier(Modifier):
	KEYWORD = "mode"
	
	class CModeshiftModes(ctypes.Structure):
		_fields_ = [
			("mode", Parameter.CParameterOEp),
			("action", Action.CActionOEp),
		]
	
	CModeshiftModesp = ctypes.POINTER(CModeshiftModes)
	CModeshiftModespp = ctypes.POINTER(CModeshiftModesp)
	
	@property
	def mods(self):
		""" Backwards-python-compatibile way to retrieve modifiers """
		return {
			SCButtons(k): v
			for (k, v) in Parameter(lib_actions
				.scc_modeshift_get_modes(self._caction)).get_value()
			if k
		}


KEYWORD_TO_ACTION = {
	y.KEYWORD: y
	for (x, y) in locals().items()
	if hasattr(y, "KEYWORD")
}


lib_bindings = find_library("libscc-bindings")


class MultiAction(Action):
	BUILD_FN = lib_bindings.scc_multiaction_new
	
	def __init__(self, *args):
		self._caction = None
		pars = (Action.CActionOEp * (len(args)))()
		for i, value in enumerate(args):
			if not isinstance(value, Action) or value._caction is None:
				raise TypeError("%s is not Action" % (repr(value), ))
			pars[i] = value._caction
		Action.__init__(self, self.BUILD_FN(ctypes.cast(pars, Action.CActionOEpp), len(pars)))


class Macro(MultiAction):
	BUILD_FN = lib_bindings.scc_macro_new


lib_bindings.scc_action_get_type.argtypes = [ Action.CActionOEp ]
lib_bindings.scc_action_get_type.restype = ctypes.c_char_p

lib_bindings.scc_action_get_property.argtypes = [ Action.CActionOEp, ctypes.c_char_p ]
lib_bindings.scc_action_get_property.restype = Parameter.CParameterOEp

lib_bindings.scc_parameter_as_action.argtypes = [ Parameter.CParameterOEp ]
lib_bindings.scc_parameter_as_action.restype = Action.CActionOEp

lib_bindings.scc_parameter_as_string.argtypes = [ Parameter.CParameterOEp ]
lib_bindings.scc_parameter_as_string.restype = ctypes.c_char_p

lib_bindings.scc_parameter_as_float.argtypes = [ Parameter.CParameterOEp ]
lib_bindings.scc_parameter_as_float.restype = ctypes.c_float

lib_bindings.scc_parameter_as_int.argtypes = [ Parameter.CParameterOEp ]
lib_bindings.scc_parameter_as_int.restype = ctypes.c_int64

lib_bindings.scc_parameter_tuple_get_count.argtypes = [ Parameter.CParameterOEp ]
lib_bindings.scc_parameter_tuple_get_count.restype = ctypes.c_uint8

lib_bindings.scc_parameter_tuple_get_child.argtypes = [ Parameter.CParameterOEp, ctypes.c_uint8 ]
lib_bindings.scc_parameter_tuple_get_child.restype = Parameter.CParameterOEp

lib_bindings.scc_error_get_message.argtypes = [ CAPError ]
lib_bindings.scc_error_get_message.restype = ctypes.c_char_p

lib_bindings.scc_action_new_from_array.argtypes = [ ctypes.c_char_p, ctypes.c_size_t, Parameter.CParameterOEpp ]
lib_bindings.scc_action_new_from_array.restype = Action.CActionOEp

lib_bindings.scc_multiaction_new.argtypes = [ Action.CActionOEpp, ctypes.c_size_t ]
lib_bindings.scc_multiaction_new.restype = Action.CActionOEp

lib_bindings.scc_macro_new.argtypes = [ Action.CActionOEpp, ctypes.c_size_t ]
lib_bindings.scc_macro_new.restype = Action.CActionOEp

lib_bindings.scc_action_ref.argtypes = [ Action.CActionOEp ]
lib_bindings.scc_action_ref.restype = Action.CActionOEp
lib_bindings.scc_action_unref.argtypes = [ Action.CActionOEp ]
lib_bindings.scc_parameter_ref.argtypes = [ Parameter.CParameterOEp ]
lib_bindings.scc_parameter_ref.restype = Parameter.CParameterOEp
lib_bindings.scc_parameter_unref.argtypes = [ Parameter.CParameterOEp ]

lib_bindings.scc_action_get_compressed.argtypes = [ Action.CActionOEp ]
lib_bindings.scc_action_get_compressed.restype = Action.CActionOEp

lib_bindings.scc_action_get_child.argtypes = [ Action.CActionOEp ]
lib_bindings.scc_action_get_child.restype = Action.CActionOEp

lib_bindings.scc_get_const_parameter.argtypes = [ ctypes.c_char_p ]
lib_bindings.scc_get_const_parameter.restype = Parameter.CParameterOEp


lib_parse = find_library("libscc-parser")
lib_parse.scc_parse_action.argtypes = [ ctypes.c_char_p ]
lib_parse.scc_parse_action.restype = Action.CActionOEp


lib_actions = find_library("libscc-actions")

lib_actions.scc_action_to_string.argtypes = [ Action.CActionOEp ]
lib_actions.scc_action_to_string.restype = ctypes.c_char_p

lib_actions.scc_new_int_parameter.argtypes = [ ctypes.c_int64 ]
lib_actions.scc_new_int_parameter.restype = Parameter.CParameterOEp

lib_actions.scc_new_float_parameter.argtypes = [ ctypes.c_float ]
lib_actions.scc_new_float_parameter.restype = Parameter.CParameterOEp

lib_actions.scc_new_action_parameter.argtypes = [ Action.CActionOEp ]
lib_actions.scc_new_action_parameter.restype = Parameter.CParameterOEp

lib_actions.scc_new_string_parameter.argtypes = [ ctypes.c_char_p ]
lib_actions.scc_new_string_parameter.restype = Parameter.CParameterOEp

lib_actions.scc_modeshift_get_modes.argtypes = [ Action.CActionOEp ]
lib_actions.scc_modeshift_get_modes.restype = Parameter.CParameterOEp

