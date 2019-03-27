#!/usr/bin/env python2
"""
SC Controller - ActionParser

Parses action(s) expressed as string or in dict loaded from json file into
one or more Action instances.
"""
from __future__ import unicode_literals


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
	
	def __init__(self, string=""):
		self.restart(string)
	
	def restart(self, string):
		self.string = string
		return self
	
	def parse(self):
		"""
		Returns parsed action.
		Throws ParseError if action cannot be parsed.
		"""
		from scc.actions import Action
		return Action.parse(self.string)


class TalkingActionParser(ActionParser):
	"""
	ActionParser that returns None when parsing fails instead of
	trowing exception and outputs message to stderr
	"""
	
	def parse(self):
		"""
		Returns parsed action or None if action cannot be parsed.
		"""
		try:
			return ActionParser.parse(self)
		except ParseError, e:
			print >>sys.stderr, "Warning: Failed to parse '%s':" % (self.string,), e

