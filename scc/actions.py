#!/usr/bin/env python2
"""
SC Controller - Actions and ActionParser

Action describes what should be done when event from physical controller button,
stick, pad or trigger is generated - typicaly what emulated button, stick or
trigger should be pressed.

ActionParser parses action(s) expressed as string (loaded from JSON file) into
one or more Action instances.
"""
from __future__ import unicode_literals

from tokenize import generate_tokens
from collections import namedtuple
from scc.uinput import Keys, Axes, Rels
import token as TokenType
import sys
_ = lambda x : x

MOUSE_BUTTONS = [ Keys.BTN_LEFT, Keys.BTN_MIDDLE, Keys.BTN_RIGHT, Keys.BTN_SIDE, Keys.BTN_EXTRA ]

class Action(object):
	"""
	Simple action that executes one of predefined methods.
	See ACTIONS for list of them.
	"""
	
	# "Action Context" constants used by describe method
	AC_BUTTON = 1
	
	def __init__(self, action, parameters):
		self.action = action
		self.parameters = parameters
	
	
	def describe(self, context):
		"""
		Returns string that describes what action does in human-readable form.
		Used in GUI.
		"""
		return str(self)
	
	
	def execute(self, event):
		return getattr(event, self.action)(*self.parameters)
	
	
	def __str__(self):
		return "<Action '%s', %s>" % (self.action, self.parameters)
	
	__repr__ = __str__


class KeyAction(Action):
	def describe(self, context):
		return _("Key %s") % (self.parameters[0].name.split("_")[-1],)


class AxisAction(Action):
	AXIS_NAMES = {
		Axes.ABS_X : ("LStick", "Left", "Right"),
		Axes.ABS_Y : ("LStick", "Up", "Down"),
		Axes.ABS_RX : ("RStick", "Left", "Right"),
		Axes.ABS_RY : ("RStick", "Up", "Down"),
		Axes.ABS_HAT0X : ("D-PAD", "Left", "Right"),
		Axes.ABS_HAT0Y : ("D-PAD", "Up", "Down"),
		Axes.ABS_Z  : ("Left Trigger", "Press", "Press"),
		Axes.ABS_RZ : ("Right Trigger", "Press", "Press"),
	}
	def describe(self, context):
		axis, neg, pos = "%s %s" % (self.parameters[0].name, _("Axis")), _("Negative"), _("Positive")
		if self.parameters[0] in AxisAction.AXIS_NAMES:
			axis, neg, pos = [ _(x) for x in AxisAction.AXIS_NAMES[self.parameters[0]] ]
		
		if context == Action.AC_BUTTON:
			for x in self.parameters:
				if type(x) in (int, float):
					if x > 0:
						return "%s %s" % (axis, pos)
					if x < 0:
						return "%s %s" % (axis, neg)
		return axis


class RAxisAction(Action):
	def describe(self, context):
		return _("Reverse %s Axis") % (self.parameters[0].name.split("_", 1)[-1],)


class DPadAction(Action):
	def describe(self, context):
		return "DPad"


class MouseAction(Action):
	def describe(self, context):
		if self.parameters[0] == Rels.REL_WHEEL:
			return _("Wheel")
		return _("Mouse %s") % (self.parameters[0].name.split("_", 1)[-1],)


class TrackpadAction(Action):
	def describe(self, context):
		return "Trackpad"


class TrackballAction(Action):
	def describe(self, context):
		return "Trackball"


class WheelAction(Action):
	def describe(self, context):
		return _("Mouse Wheel")


class ButtonAction(Action):
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
	
	def describe(self, context):
		p = self.parameters[0]
		if p in ButtonAction.SPECIAL_NAMES:
			return _(ButtonAction.SPECIAL_NAMES[p])
		elif p in MOUSE_BUTTONS:
			return _("Mouse %s") % (p,)
		else:
			return p.name.split("_", 1)[-1]


class ClickAction(Action):
	def describe(self, context):
		return _("(if pressed)")


class HatAction(Action):
	def describe(self, context):
		return "Hat"


ACTIONS = {
	# Actions
	'key'		: KeyAction,
	'axis'		: AxisAction,
	'dpad'		: DPadAction,
	'mouse'		: MouseAction,
	'trackpad'	: TrackpadAction,
	'trackball'	: TrackballAction,
	'wheel'		: WheelAction,
	'button'	: ButtonAction,
	'click'		: ClickAction,
	# Shortcuts
	'raxis'		: RAxisAction,
	'hatup'		: HatAction,
	'hatdown'	: HatAction,
	'hatleft'	: HatAction,
	'hatright'	: HatAction,
}


class MultiAction(object):
	"""
	Two or more actions executed in sequence.
	Generated when parsing ';'
	"""
	
	def __init__(self, *actions):
		self.actions = []
		self._add_all(actions)
	
	
	def _add_all(self, actions):
		for x in actions:
			self._add(x)
	
	
	def _add(self, action):
		if action.__class__ == self.__class__:	# I don't wan't subclasses here
			self._add_all(action.actions)
		else:
			self.actions.append(action)
	
	
	def execute(self, event):
		rv = False
		for a in actions:
			rv = a.execute(event)
		return rv
	
	
	def __str__(self):
		return "<[ %s ]>" % ("; ".join([ str(x) for x in self.actions ]), )
	
	__repr__ = __str__	


class LinkedActions(MultiAction):
	"""
	Two actions linked together.
	Action 2 is executed only if action 1 returns True - currently used only
	with 'click' action that returns True only if pad or stick is pressed.
	"""
	
	def execute(self, event):
		for x in self.actions:
			if not x.execute(event): return False
		return True
	
	
	def __str__(self):
		return "< %s >" % (" and ".join([ str(x) for x in self.actions ]), )
	
	__repr__ = __str__


class ParseError(Exception): pass


class ActionParser(object):
	"""
	Parses action expressed as string into Action instances.
	
	Usage:
		ap = ActionParser(string)
		action = ap.parse()
		if action is None:
			error = ap.get_error()
			# do something with error
	"""
	Token = namedtuple('Token', 'type value')
	
	CONSTS = {
		'Keys' : Keys,
		'Axes' : Axes,
		'Rels' : Rels
	}
	
	def __init__(self, string=""):
		self.restart(string)
	
	
	def restart(self, string):
		"""
		Restarts parsing with new string
		Returns self for chaining.
		"""
		
		self.tokens = [
			ActionParser.Token(type, string)
			for (type, string, trash, trash, trash)
			in generate_tokens( iter([string]).next )
			if type != TokenType.ENDMARKER
		]
		self.index = 0
		return self
	
	
	def _next_token(self):
		rv = self.tokens[self.index]
		self.index += 1
		return rv
	
	
	def _peek_token(self):
		""" As _next_token, but without increasing counter """
		return self.tokens[self.index]
	
	
	def _tokens_left(self):
		""" Returns True if there are any tokens left """
		return self.index < len(self.tokens)
	
	
	def _parse_parameter(self):
		""" Parses single parameter """
		t = self._next_token()
		if t.type == TokenType.NAME:
			# Constant or action used as parameter
			if self._tokens_left() and self._peek_token().type == TokenType.OP and self._peek_token().value == '(':
				# Action used as parameter
				self.index -= 1 # go step back and reparse as action
				parameter = self._parse_action()
			else:
				# Constant
				if not t.value in ActionParser.CONSTS:
					raise ParseError("Excepted parameter, got '%s' which is not defined" % (t.value,))
				parameter = ActionParser.CONSTS[t.value]
			
			# Check for dots
			while self._tokens_left() and self._peek_token().type == TokenType.OP and self._peek_token().value == '.':
				self._next_token()
				if not self._tokens_left():
					raise ParseError("Excepted NAME after '.'")
				
				t = self._next_token()
				if not hasattr(parameter, t.value):
					raise ParseError("%s has no attribute '%s'" % (t.value,))
				parameter = getattr(parameter, t.value)
			return parameter
		
		if t.type == TokenType.OP and t.value == "-":
			if not self._tokens_left() or self._peek_token().type != TokenType.NUMBER:
				raise ParseError("Excepted number after '-'")
			return - self._parse_number()
		
		
		if t.type == TokenType.NUMBER:
			self.index -= 1
			return self._parse_number()
		
		raise ParseError("Excepted parameter, got '%s'" % (t.value,))
	
	
	def _parse_number(self):
		t = self._next_token()
		if t.type != TokenType.NUMBER:
			raise ParseError("Excepted number, got '%s'" % (t.value,))
		if "." in t.value:
			return float(t.value)
		elif "e" in t.value.lower():
			return float(t.value)
		elif t.value.lower().startswith("0x"):
			return int(t.value, 16)
		elif t.value.lower().startswith("0b"):
			return int(t.value, 2)
		else:
			return int(t.value)
	
	
	def _parse_parameters(self):
		""" Parses parameter list """
		# Check and skip over '('
		t = self._next_token()
		if t.type != TokenType.OP or t.value != '(':
			raise ParseError("Excepted '(' of parameter list, got '%s'" % (t.value,))
		
		parameters = []
		while self._tokens_left():
			# Check for ')' that would end parameter list
			t = self._peek_token()
			if t.type == TokenType.OP and t.value == ')':
				self._next_token()
				return parameters
			
			# Parse one parameter
			parameters.append(self._parse_parameter())
			# Check if next token is either ')' or ','
			t = self._peek_token()
			if t.type == TokenType.OP and t.value == ')':
				pass
			elif t.type == TokenType.OP and t.value == ',':
				 self._next_token()
			else:
				raise ParseError("Excepted ',' or end of parameter list after parameter '%s'" % (parameters[-1],))
			
		
		# Code shouldn't reach here, unless there is not closing ')' in parameter list
		raise ParseError("Unmatched parenthesis")
	
	
	def _parse_action(self):
		"""
		Parses one action, that is one of:
		 - something(params)
		 - something()
		 - something
		"""
		# Check if next token is TokenType.NAME and grab action name from it
		t = self._next_token()
		if t.type != TokenType.NAME:
			raise ParseError("Excepted action name, got '%s'" % (t.value,))
		if t.value not in ACTIONS:
			raise ParseError("Unknown action '%s'" % (t.value,))
		action_name = t.value
		action_class = ACTIONS[action_name]
		
		# Check if there are any tokens left - return action without parameters
		# if not
		if not self._tokens_left():
			return action_class(action_name, [])
		
		# Check if token after action name is parenthesis and if yes, parse
		# parameters from it
		t = self._peek_token()
		if t.type == TokenType.OP and t.value == '(':
			parameters  = self._parse_parameters()
			if not self._tokens_left():
				return action_class(action_name, parameters)
			t = self._peek_token()
		
		# ... or, if it is one of ';', 'and' or 'or' and if yes, parse next action
		if t.type == TokenType.NAME and t.value == 'and':
			# Two (or more) actions joined by 'and'
			self._next_token()
			if not self._tokens_left():
				raise ParseError("Excepted action after 'and'")
			action1 = action_class(action_name, parameters)
			action2 = self._parse_action()
			return LinkedActions(action1, action2)
		
		if t.type == TokenType.OP and t.value == ';':
			# Two (or more) actions joined by ';'
			self._next_token()
			if not self._tokens_left():
				# Having ';' at end of string is not actually error
				return action_class(action_name, parameters)
			action1 = action_class(action_name, parameters)
			action2 = self._parse_action()
			return MultiAction(action1, action2)
		
		return action_class(action_name, parameters)
	
	
	def parse(self):
		"""
		Returns parsed action.
		Throws ParseError if action cannot be parsed.
		"""
		return self._parse_action()
	
	
class TalkingActionParser(ActionParser):
	"""
	ActionParser that returns None when parsing fails instead of
	trowing exception and outputs message to stderr
	"""
	
	def restart(self, string):
		self.string = string
		return ActionParser.restart(self, string)
	
	
	def parse(self):
		"""
		Returns parsed action or None if action cannot be parsed.
		"""
		try:
			return ActionParser.parse(self)
		except ParseError, e:
			print >>sys.stderr, "Warning: Failed to parse '%s':" % (self.string,), e

