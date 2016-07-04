#!/usr/bin/env python2
"""
SC Controller - ActionParser

Parses action(s) expressed as string or in dict loaded from json file into
one or more Action instances.
"""
from __future__ import unicode_literals
from tokenize import generate_tokens, TokenError
from collections import namedtuple

from scc.constants import SCButtons, HapticPos, PITCH, YAW, ROLL
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX, SAME
from scc.modifiers import ClickModifier, FeedbackModifier, DeadzoneModifier
from scc.modifiers import SensitivityModifier, ModeModifier
from scc.modifiers import HoldModifier, DoubleclickModifier
from scc.actions import XYAction, DPadAction, DPad8Action
from scc.actions import ACTIONS, NoAction, MultiAction
from scc.special_actions import OSDAction
from scc.uinput import Keys, Axes, Rels
from scc.macros import Macro

import token as TokenType
import sys


class ParseError(Exception): pass


def build_action_constants():
	""" Generates dicts for ActionParser.CONSTS """
	rv = {
		'Keys'		: Keys,
		'Axes'		: Axes,
		'Rels'		: Rels,
		'HapticPos'	: HapticPos,
		'None'		: NoAction(),
		'PITCH'		: PITCH,
		'YAW'		: YAW,
		'ROLL'		: ROLL,
		'SAME'		: SAME,
		'True'		: True,
		'False'		: False,
	}
	for tpl in (Keys, Axes, Rels, SCButtons, HapticPos):
		for x in tpl:
			rv[x.name] = x
	return rv


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
	
	CONSTS = build_action_constants()
	
	
	def __init__(self, string=""):
		self.restart(string)
	
	
	def from_json_data(self, data, key=None):
		"""
		Converts dict stored in profile file into action.
		
		May throw ParseError.
		"""
		if key is not None:
			# Don't fail if called for non-existent key, return NoAction instead.
			# Using this is sorter than
			# calling 'if button in data["buttons"]: ...' everywhere
			if key in data:
				return self.from_json_data(data[key], None)
			else:
				return NoAction()
		
		a = NoAction()
		if "action" in data:
			a = self.restart(data["action"]).parse() or NoAction()
		if "X" in data or "Y" in data:
			# "action" is ignored if either "X" or "Y" is there
			x = self.from_json_data(data["X"]) if "X" in data else NoAction()
			y = self.from_json_data(data["Y"]) if "Y" in data else NoAction()
			a = XYAction(x, y)
		if "deadzone" in data:
			lower = data["deadzone"]["lower"] if "lower" in data["deadzone"] else STICK_PAD_MIN
			upper = data["deadzone"]["upper"] if "upper" in data["deadzone"] else STICK_PAD_MAX
			a = DeadzoneModifier(lower, upper, a)
		if "sensitivity" in data:
			args = data["sensitivity"]
			args.append(a)
			a = SensitivityModifier(*args)
		if "feedback" in data:
			args = data["feedback"]
			if hasattr(HapticPos, args[0]):
				args[0] = getattr(HapticPos, args[0])
			args.append(a)
			a = FeedbackModifier(*args)
		if "osd" in data:
			a = OSDAction(a)
			if data["osd"] is not True:
				a.timeout = float(data["osd"])
		if "click" in data:
			a = ClickModifier(a)
		if "name" in data:
			a.name = data["name"]
		if "modes" in data:
			args = []
			for button in data['modes']:
				if hasattr(SCButtons, button):
					args += [ getattr(SCButtons, button), self.from_json_data(data['modes'][button]) ]
			if a:
				args += [ a ]
			a = ModeModifier(*args)
		if "doubleclick" in data:
			args = [ self.from_json_data(data['doubleclick']), a ]
			a = DoubleclickModifier(*args)
			if "time" in data: a.timeout = data["time"]
		if "hold" in data:
			if isinstance(a, DoubleclickModifier):
				a.holdaction = self.from_json_data(data['hold'])
			else:
				args = [ self.from_json_data(data['hold']), a ]
				a = HoldModifier(*args)
			if "time" in data: a.timeout = data["time"]
		if "dpad" in data:
			args = [ self.from_json_data(x) for x in data["dpad"] ]
			if len(args) > 4:
				a = DPad8Action(*args)
			else:
				a = DPadAction(*args)
		return a
	
	
	def restart(self, string):
		"""
		Restarts parsing with new string
		Returns self for chaining.
		"""
		
		try:
			self.tokens = [
				ActionParser.Token(type, string)
				for (type, string, trash, trash, trash)
				in generate_tokens( iter([string]).next )
				if type != TokenType.ENDMARKER
			]
		except TokenError:
			self.tokens = None
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
		while t.type == TokenType.NEWLINE or t.value == "\n":
			if not self._tokens_left():
				raise ParseError("Expected parameter at end of string")
			t = self._next_token()
		
		if t.type == TokenType.NAME:
			# Constant or action used as parameter
			if self._tokens_left() and self._peek_token().type == TokenType.OP and self._peek_token().value == '(':
				# Action used as parameter
				self.index -= 1 # go step back and reparse as action
				parameter = self._parse_action()
			elif self._tokens_left() and t.value in ACTIONS and type(ACTIONS[t.value]) == dict and self._peek_token().value == '.':
				# SOMETHING.Action used as parameter
				self.index -= 1 # go step back and reparse as action
				parameter = self._parse_action()
			else:
				# Constant
				if not t.value in ActionParser.CONSTS:
					raise ParseError("Expected parameter, got '%s' which is not defined" % (t.value,))
				parameter = ActionParser.CONSTS[t.value]
			
			# Check for dots
			while self._tokens_left() and self._peek_token().type == TokenType.OP and self._peek_token().value == '.':
				self._next_token()
				if not self._tokens_left():
					raise ParseError("Expected NAME after '.'")
				
				t = self._next_token()
				if not hasattr(parameter, t.value):
					raise ParseError("%s has no attribute '%s'" % (parameter, t.value,))
				parameter = getattr(parameter, t.value)
			return parameter
		
		if t.type == TokenType.OP and t.value == "-":
			if not self._tokens_left() or self._peek_token().type != TokenType.NUMBER:
				raise ParseError("Expected number after '-'")
			return - self._parse_number()
		
		if t.type == TokenType.NUMBER:
			self.index -= 1
			return self._parse_number()
		
		if t.type == TokenType.STRING:
			return t.value[1:-1].decode('string_escape')
		
		raise ParseError("Expected parameter, got '%s'" % (t.value,))


	def _parse_number(self):
		t = self._next_token()
		if t.type != TokenType.NUMBER:
			raise ParseError("Expected number, got '%s'" % (t.value,))
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
			raise ParseError("Expected '(' of parameter list, got '%s'" % (t.value,))

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
			while t.type == TokenType.NEWLINE or t.value == "\n":
				self._next_token()
				if not self._tokens_left():
					raise ParseError("Expected ',' or end of parameter list after parameter '%s'" % (parameters[-1],))
				t = self._peek_token()
			if t.type == TokenType.OP and t.value == ')':
				pass
			elif t.type == TokenType.OP and t.value == ',':
				self._next_token()
			else:
				raise ParseError("Expected ',' or end of parameter list after parameter '%s'" % (parameters[-1],))


		# Code shouldn't reach here, unless there is not closing ')' in parameter list
		raise ParseError("Unmatched parenthesis")
	
	
	def _create_action(self, cls, *pars):
		try:
			return cls(*pars)
		except ValueError, e:
			raise ParseError(unicode(e))
		except TypeError, e:
			print >>sys.stderr, e
			raise ParseError("Invalid number of parameters for '%s'" % (cls.COMMAND))
	
	
	def _parse_action(self, frm=ACTIONS):
		"""
		Parses one action, that is one of:
		 - something(params)
		 - something()
		 - something
		"""
		# Check if next token is TokenType.NAME and grab action name from it
		t = self._next_token()
		if t.type != TokenType.NAME:
			raise ParseError("Expected action name, got '%s'" % (t.value,))
		if t.value not in frm:
			raise ParseError("Unknown action '%s'" % (t.value,))
		action_name = t.value
		action_class = frm[action_name]
		
		# Check if there are any tokens left - return action without parameters
		# if not
		if not self._tokens_left():
			return self._create_action(action_class)
		
		# Check if token after action name is parenthesis and if yes, parse
		# parameters from it
		t = self._peek_token()
		parameters = []
		if t.type == TokenType.OP and t.value == '.':
			# ACTION dict can have nested dicts; SOMETHING.action
			if type(action_class) == dict:
				self._next_token()
				return self._parse_action(action_class)
			else:
				raise ParseError("Unexpected '.' after '%s'" % (action_name,))
		if t.type == TokenType.OP and t.value == '(':
			parameters  = self._parse_parameters()
			if not self._tokens_left():
				return self._create_action(action_class, *parameters)
			t = self._peek_token()
		
		# ... or, if it is one of ';', 'and' or 'or' and if yes, parse next action
		if t.type == TokenType.NAME and t.value == 'and':
			# Two (or more) actions joined by 'and'
			self._next_token()
			if not self._tokens_left():
				raise ParseError("Expected action after 'and'")
			action1 = self._create_action(action_class, *parameters)
			action2 = self._parse_action()
			return MultiAction(action1, action2)
		
		if t.type == TokenType.NEWLINE or t.value == "\n":
			# Newline can be used to join actions instead of 'and'
			self._next_token()
			if not self._tokens_left():
				# Newline at end of string is not error
				return self._create_action(action_class, *parameters)
			t = self._peek_token()
			if t.type == TokenType.OP and t.value in (')', ','):
				# ')' starts next line
				return self._create_action(action_class, *parameters)
			action1 = self._create_action(action_class, *parameters)
			action2 = self._parse_action()
			return MultiAction(action1, action2)
		
		if t.type == TokenType.OP and t.value == ';':
			# Two (or more) actions joined by ';'
			self._next_token()
			while self._tokens_left() and self._peek_token().type == TokenType.NEWLINE:
				self._next_token()
			if not self._tokens_left():
				# Having ';' at end of string is not actually error
				return self._create_action(action_class, *parameters)
			action1 = self._create_action(action_class, *parameters)
			action2 = self._parse_action()
			return Macro(action1, action2)
		
		return self._create_action(action_class, *parameters)
	
	
	def parse(self):
		"""
		Returns parsed action.
		Throws ParseError if action cannot be parsed.
		"""
		if self.tokens == None:
			raise ParseError("Syntax error")
		a = self._parse_action()
		if self._tokens_left():
			raise ParseError("Unexpected '%s'" % (self._next_token().value, ))
		return a


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
