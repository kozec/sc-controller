#!/usr/bin/env python2
"""
SC Controller - Modifiers

Modifier is Action that just sits between input and actual action, changing
way how resulting action works.
For example, click() modifier executes action only if pad is pressed.
"""
from __future__ import unicode_literals

from scc.actions import Action, NoAction, ACTIONS
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import LEFT, RIGHT, STICK, SCButtons

import time, logging
log = logging.getLogger("Modifiers")
_ = lambda x : x

class Modifier(Action):
	def __init__(self, action=None):
		Action.__init__(self, action)
		self.action = action or NoAction()


class ClickModifier(Modifier):
	COMMAND = "click"
	
	def describe(self, context):
		if context in (Action.AC_STICK, Action.AC_PAD):
			return _("(if pressed)") + "\n" + self.action.describe(context)
		else:
			return _("(if pressed)") + " " + self.action.describe(context)
	
	
	def to_string(self, multiline=False, pad=0):
		if multiline:
			return ((" " * pad) + "click(\n" +
				self.action.to_string(True, pad + 2) +
				(" " * pad) + ")")
		else:
			return "click( " + self.action.to_string() + " )"
	
	# For button press & co it's safe to assume that they are being pressed...
	def button_press(self, mapper):
		return self.action.button_press(mapper)
	
	def button_release(self, mapper):
		return self.action.button_release(mapper)
	
	def trigger(self, mapper, position, old_position):
		return self.action.trigger(mapper, position, old_position)
	
	
	def axis(self, mapper, position, what):
		if what in (STICK, LEFT) and mapper.is_pressed(SCButtons.LPAD):
			if what == STICK: mapper.force_event.add(FE_STICK)
			return self.action.axis(mapper, position, what)
		if what in (STICK, LEFT) and mapper.was_pressed(SCButtons.LPAD):
			# Just released
			return self.action.axis(mapper, 0, what)
		# what == RIGHT, there are only three options
		if mapper.is_pressed(SCButtons.RPAD):
			return self.action.axis(mapper, position, what)
		if mapper.was_pressed(SCButtons.RPAD):
			# Just released
			return self.action.axis(mapper, 0, what)
	
	
	def pad(self, mapper, position, what):
		if what == LEFT and mapper.is_pressed(SCButtons.LPAD):
			if what == STICK: mapper.force_event.add(FE_STICK)
			return self.action.pad(mapper, position, what)
		if what == LEFT and mapper.was_pressed(SCButtons.LPAD):
			# Just released
			return self.action.pad(mapper, 0, what)
		# what == RIGHT, there are only two options
		if mapper.is_pressed(SCButtons.RPAD):
			return self.action.pad(mapper, position, what)
		if mapper.was_pressed(SCButtons.RPAD):
			# Just released
			return self.action.pad(mapper, 0, what)
	
	
	def whole(self, mapper, x, y, what):
		if what in (STICK, LEFT) and mapper.is_pressed(SCButtons.LPAD):
			if what == STICK: mapper.force_event.add(FE_STICK)
			return self.action.whole(mapper, x, y, what)
		if what in (STICK, LEFT) and mapper.was_pressed(SCButtons.LPAD):
			# Just released
			return self.action.whole(mapper, 0, 0, what)
		# what == RIGHT, there are only three options
		if mapper.is_pressed(SCButtons.RPAD):
			# mapper.force_event.add(FE_PAD)
			return self.action.whole(mapper, x, y, what)
		if mapper.was_pressed(SCButtons.RPAD):
			# Just released
			return self.action.whole(mapper, 0, 0, what)


# Add modifiers to ACTIONS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'COMMAND') ]:
	if i.COMMAND is not None:
		ACTIONS[i.COMMAND] = i
