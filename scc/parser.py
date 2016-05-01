#!/usr/bin/env python2
"""
SC Controller - ActionParser

Parses action(s) expressed as string (loaded from JSON file) into
one or more Action instances.
"""
from __future__ import unicode_literals
from tokenize import generate_tokens, TokenError
from collections import namedtuple

from scc.actions import ACTIONS, NoAction, MultiAction
from scc.uinput import Keys, Axes, Rels
from scc.constants import SCButtons
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
		'None'		: NoAction(),
	}
	for tpl in (Keys, Axes, Rels, SCButtons):
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
			raise ParseError("Expected action name, got '%s'" % (t.value,))
		if t.value not in ACTIONS:
			raise ParseError("Unknown action '%s'" % (t.value,))
		action_name = t.value
		action_class = ACTIONS[action_name]
		
		# Check if there are any tokens left - return action without parameters
		# if not
		if not self._tokens_left():
			return self._create_action(action_class)
		
		# Check if token after action name is parenthesis and if yes, parse
		# parameters from it
		t = self._peek_token()
		parameters = []
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
