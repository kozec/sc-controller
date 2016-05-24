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

from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD, SCButtons
from scc.constants import LEFT, RIGHT, STICK, SCButtons
from scc.actions import Action, NoAction, ButtonAction
from scc.actions import ACTIONS, MOUSE_BUTTONS
from scc.tools import strip_none

import time, logging
log = logging.getLogger("SActions")
_ = lambda x : x


class SpecialAction(Action):
	def execute(self, mapper, *a):
		sa = mapper.get_special_actions_handler()
		h_name = "on_sa_%s" % (self.COMMAND,)
		if sa is None:
			log.warning("Mapper can't handle special actions (set_special_actions_handler never called)")
		elif hasattr(sa, h_name):
			return getattr(sa, h_name)(mapper, self, *a)
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
		if context == Action.AC_OSD:
			return _("Profile: %s") % (self.profile,)
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
		if context == Action.AC_OSD:
			return _("Turning controller OFF")
		return _("Turn Off the Controller")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)
	
	
	def button_release(self, mapper):
		# Execute only when button is released (executing this when button
		# is pressed would hold stuck any other action bound to same button,
		# as button_release is not sent after controller turns off)
		self.execute(mapper)


class OSDAction(SpecialAction):
	"""
	Displays text in OSD, or, if used as modifier, displays action description
	and executes that action.
	"""
	COMMAND = "osd"
	DEFAULT_TIMEOUT = 5
	
	def __init__(self, *parameters):
		Action.__init__(self, *parameters)
		self.action = None
		self.timeout = self.DEFAULT_TIMEOUT
		if len(parameters) > 1:
			# timeout parameter included
			self.timeout = parameters[0]
		if isinstance(parameters[-1], Action):
			self.action = parameters[-1]
			self.text = self.action.describe(Action.AC_OSD)
		else:
			self.text = unicode(parameters[-1])
	
	def describe(self, context):
		if self.name: return self.name
		if self.action:
			return _("%s (with OSD)") % (self.action.describe(context), )
		elif context == Action.AC_OSD:
			return _("Display '%s'" % self.text)
		return _("OSD Message")
	
	
	def to_string(self, multiline=False, pad=0):
		if isinstance(self.parameters[0], Action):
			p0str = self.parameters[0].to_string()
		else:
			p0str = "'%s'" % (str(self.parameters[0]).encode('string_escape'),)
		if len(self.parameters) == 1:
			return (" " * pad) + "%s(%s)" % (self.COMMAND, p0str)
		else:
			return (" " * pad) + "%s(%s, %s)" % (self.COMMAND,
				p0str, self.parameters[1]
			)
	
	
	def strip(self):
		if self.action:
			self.action = self.action.strip()
		return self
	
	
	def compress(self):
		if self.action:
			self.action = self.action.compress()
		return self
	
	
	def encode(self):
		if self.action:
			rv = self.action.encode()
			if self.timeout == self.DEFAULT_TIMEOUT:
				rv['osd'] = True
			else:
				rv['osd'] = self.timeout
			return rv
		else:
			return SpecialAction.encode(self)
	
	
	def button_press(self, mapper):
		self.execute(mapper)
		if self.action:
			return self.action.button_press(mapper)
	
	
	def button_release(self, mapper):
		if self.action:
			return self.action.button_release(mapper)
	
	
	def trigger(self, mapper, position, old_position):
		if self.action:
			return self.action.trigger(mapper, position, old_position)
	
	def axis(self, mapper, position, what):
		if self.action:
			return self.action.axis(mapper, position, what)
	
	def pad(self, mapper, position, what):
		if self.action:
			return self.action.pad(mapper, position, what)
	
	def whole(self, mapper, x, y, what):
		if self.action:
			return self.action.whole(mapper, x, y, what)


class MenuAction(SpecialAction):
	"""
	Displays menu defined in profile or globally.
	"""
	COMMAND = "menu"
	MENU_TYPE = "menu"
	DEFAULT_CONFIRM = SCButtons.A
	DEFAULT_CANCEL = SCButtons.B
	
	def __init__(self, menu_id, confirm_with=None, cancel_with=None, show_with_release=None):
		Action.__init__(self, menu_id, *strip_none(confirm_with, cancel_with, show_with_release))
		self.menu_id = menu_id
		self.confirm_with = confirm_with or self.DEFAULT_CONFIRM
		self.cancel_with = cancel_with or self.DEFAULT_CANCEL
		self.show_with_release = show_with_release not in (None, False)
	
	def describe(self, context):
		if self.name: return self.name
		return _("Menu")
	
	
	def to_string(self, multiline=False, pad=0):
		pars = [] + list(self.parameters)
		pars[0] = "'%s'" % (str(pars[0]).encode('string_escape'),)
		return (" " * pad) + "%s(%s)" % (self.COMMAND, ",".join(pars))
	
	
	def button_press(self, mapper):
		if not self.show_with_release:
			self.execute(mapper)
	
	
	def button_release(self, mapper):
		if self.show_with_release:
			self.execute(mapper)
	
	
	def whole(self, mapper, x, y, what):
		if not mapper.was_pressed(SCButtons.LPADTOUCH):
			self.execute(mapper, '--control-with', LEFT, '--use-cursor')


class GridMenuAction(MenuAction):
	"""
	Same as menu, but displayed in grid
	"""
	COMMAND = "gridmenu"
	MENU_TYPE = "gridmenu"


class KeyboardAction(SpecialAction):
	"""
	Shows OSD keyboard.
	"""
	COMMAND = "keyboard"
	
	def __init__(self):
		Action.__init__(self)
	
	
	def describe(self, context):
		if self.name: return self.name
		if context == Action.AC_OSD:
			return _("Display Keyboard")
		return _("OSD Keyboard")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)
	
	
	def button_release(self, mapper):
		self.execute(mapper)


# Add macros to ACTIONS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'COMMAND') ]:
	if i.COMMAND is not None:
		ACTIONS[i.COMMAND] = i
