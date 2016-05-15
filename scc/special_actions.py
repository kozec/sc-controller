#!/usr/bin/env python2
"""
SC Controller - Special Actions

Special Action is "special" since it cannot be handled by mapper alone.
Instead, on_sa_<actionname> method on handler instance set by
mapper.set_special_actions_handler() is called to do whatever action is supposed
to do. If handler is not set, or doesn't have reqiuired method defined,
action only prints warning to console.
"""
from __future__ import unicode_literals

from scc.actions import Action, NoAction, ButtonAction, ACTIONS, MOUSE_BUTTONS
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import LEFT, RIGHT, STICK, SCButtons
from scc.tools import strip_none

import time, logging
log = logging.getLogger("SActions")
_ = lambda x : x


class SpecialAction(Action):
	def execute(self, mapper):
		sa = mapper.get_special_actions_handler()
		h_name = "on_sa_%s" % (self.COMMAND,)
		if sa is None:
			log.warning("Mapper can't handle special actions (set_special_actions_handler never called)")
		elif hasattr(sa, h_name):
			return getattr(sa, h_name)(mapper, self)
		else:
			log.warning("Mapper can't handle '%s' action" % (self.COMMAND,))
	
	# Prevent warnings when special action is bound to button
	def button_press(self, mapper): pass
	def button_release(self, mapper): pass


class ChangeProfileAction(SpecialAction):
	COMMAND = "profile"
	
	def __init__(self, profile):
		SpecialAction.__init__(self, profile)
		self.profile = profile
	
	def describe(self, context):
		if self.name: return self.name
		return _("Profile Change")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s('%s')" % (self.COMMAND, self.profile.encode('string_escape'))
	
	def button_release(self, mapper):
		# Execute only when button is released (executing this when button
		# is pressed would send following button_release event to another
		# action from loaded profile)
		self.execute(mapper)


class ShellCommandAction(SpecialAction):
	COMMAND = "shell"
	
	def __init__(self, command):
		Action.__init__(self, command)
		self.command = command
	
	def describe(self, context):
		if self.name: return self.name
		return _("Execute Command")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s('%s')" % (self.COMMAND, self.parameters[0].encode('string_escape'))
	
	
	def button_press(self, mapper):
		# Execute only when button is pressed
		self.execute(mapper)


class TurnOffAction(SpecialAction):
	COMMAND = "turnoff"
	
	def __init__(self):
		Action.__init__(self)
	
	def describe(self, context):
		if self.name: return self.name
		return _("Turn Off the Controller")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)
	
	
	def button_release(self, mapper):
		# Execute only when button is released (executing this when button
		# is pressed would hold stuck any other action bound to same button,
		# as button_release is not sent after controller turns off)
		self.execute(mapper)


class OSDAction(SpecialAction):
	COMMAND = "osd"
	
	def __init__(self, text, timeout=None):
		Action.__init__(self, text, *strip_none(timeout))
		self.text = text
		self.timeout = timeout or 5
	
	def describe(self, context):
		if self.name: return self.name
		return _("OSD Message")
	
	
	def to_string(self, multiline=False, pad=0):
		if len(self.parameters) == 1:
			return (" " * pad) + "%s('%s')" % (self.COMMAND, self.parameters[0].encode('string_escape'))
		else:
			return (" " * pad) + "%s('%s', %s)" % (self.COMMAND,
				self.parameters[0].encode('string_escape'),
				self.parameters[1]
			)
	
	
	def button_press(self, mapper):
		self.execute(mapper)

# Add macros to ACTIONS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'COMMAND') ]:
	if i.COMMAND is not None:
		ACTIONS[i.COMMAND] = i
