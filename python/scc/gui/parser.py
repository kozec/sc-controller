from __future__ import unicode_literals
from scc.parser import ActionParser, ParseError
from scc.actions import Action, NoAction
from scc.tools import _

import logging
log = logging.getLogger("gui.parse")

class InvalidAction:
	def __init__(self, string, error):
		self.string = string
		self.error = error
	
	
	def __str__(self):
		return "<Invalid Action '%s'>" % (self.string,)
	
	__repr__ = __str__
	
	
	def to_string(self, *a):
		return self.string
	
	
	def describe(self, *a):
		return _("(invalid)")


class GuiActionParser(ActionParser):
	"""
	ActionParser that stores original string and
	returns InvalidAction instance when parsing fails
	"""
	
	def restart(self, string):
		self.string = string
		return ActionParser.restart(self, string)
	
	def parse(self):
		"""
		Returns parsed action or None if action cannot be parsed.
		"""
		try:
			a = ActionParser.parse(self)
			a.string = self.string
			return a
		except ParseError, e:
			log.error("Failed to parse '%s'", self.string)
			log.error(e)
			return InvalidAction(self.string, e)
	
	def from_json_data(self, data, key=None):
		# TODO: Ideally, there shouldn't be any need for this method
		if key is not None:
			if key in data:
				return self.from_json_data(data[key])
			return NoAction()
		
		if "action" in data:
			return self.restart(data['action']).parse()
		else:
			return NoAction()

