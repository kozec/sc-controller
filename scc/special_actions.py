#!/usr/bin/env python2
"""
SC Controller - Special Actions

Moved from actions just to keep it shorter.
"""
from __future__ import unicode_literals

from scc.actions import Action, NoAction, ButtonAction, ACTIONS, MOUSE_BUTTONS
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import LEFT, RIGHT, STICK, SCButtons

import time, logging
log = logging.getLogger("SActions")
_ = lambda x : x


class ChangeProfileAction(Action):
	COMMAND = "profile"
	
	def __init__(self, profile):
		Action.__init__(self, profile)
		self.profile = profile
	
	def describe(self, context):
		if self.name: return self.name
		return _("Profile Change")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s('%s')" % (self.COMMAND, self.profile.encode('string_escape'))


	def button_press(self, mapper):
		pass
	
	def button_release(self, mapper):
		# Can be executed only when releasing button
		if mapper.change_profile_callback is None:
			log.warning("Mapper can't change profile by controller action")
		else:
			mapper.change_profile_callback(self.profile)


class ShellCommandAction(Action):
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
		# Can be executed only when pressing button
		if mapper.shell_command_callback is None:
			log.warning("Mapper can't execute commands")
		else:
			mapper.shell_command_callback(self.command)
	
	def button_release(self, mapper):
		pass


class TurnOffAction(Action):
	COMMAND = "turnoff"
	
	def __init__(self):
		Action.__init__(self)
	
	def describe(self, context):
		if self.name: return self.name
		return _("Turn Off the Controller")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)
	
	
	def button_press(self, mapper):
		pass
	
	
	def button_release(self, mapper):
		# Can be executed only by releasing button
		# (not by pressing it)
		if mapper.get_controller():
			mapper.get_controller().turnoff()



# Add macros to ACTIONS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'COMMAND') ]:
	if i.COMMAND is not None:
		ACTIONS[i.COMMAND] = i
