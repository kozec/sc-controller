#!/usr/bin/env python2
"""
SC Controller - OSD Keyboard Actions

Special Actions that are used to bind functions like closing keyboard or moving
cursors around.

Actions defined here are accessible as OSK.something, if this module is imported.
"""
from __future__ import unicode_literals

from scc.lib import Enum
from scc.actions import Action, SpecialAction, ACTIONS
from scc.constants import TRIGGER_HALF
from scc.tools import strip_none

import time, logging
log = logging.getLogger("OSDKeyActs")
_ = lambda x : x


class OSDKeyboardAction(Action, SpecialAction):
	def __init__(self, *a):
		Action.__init__(self, *a)
		self.speed = 1.0
	
	
	def set_speed(self, x, y, z):
		self.speed = x
		return True
	
	
	def trigger(self, mapper, p, old_p):
		if p * self.speed >= TRIGGER_HALF and old_p * self.speed < TRIGGER_HALF:
			self.button_press(mapper)
		elif p * self.speed < TRIGGER_HALF and old_p * self.speed >= TRIGGER_HALF:
			self.button_release(mapper)


class CloseOSDKeyboardAction(OSDKeyboardAction):
	SA = COMMAND = "close"
	
	def describe(self, context):
		return _("Close OSD Keyboard")
	
		
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)
	
	def button_press(self, mapper):
		self.execute(mapper)
	
	def button_release(self, mapper): pass


class KeyboardCursorAction(Action, SpecialAction):
	SA = COMMAND = "cursor"
	
	def __init__(self, side):
		Action.__init__(self, side)
		if hasattr(side, "name"): side = side.name
		self.side = side
	
	
	def whole(self, mapper, x, y, what):
		self.execute(mapper, x, y)
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s(%s)" % (self.COMMAND, self.side)


class MoveKeyboardAction(OSDKeyboardAction):
	SA = COMMAND = "move"
	
	def whole(self, mapper, x, y, what):
		self.execute(mapper, x, y)
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)


class PressKeyboardButtonAction(OSDKeyboardAction):
	SA = COMMAND = "press"
	
	def __init__(self, side):
		OSDKeyboardAction.__init__(self, side)
		if hasattr(side, "name"): side = side.name
		self.side = side
	
	
	def button_press(self, mapper):
		self.execute(mapper, True)
	
	
	def button_release(self, mapper):
		self.execute(mapper, False)
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND, self.side)


# Add stuff to ACTIONS dict
ACTIONS['OSK'] = {}
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'COMMAND') ]:
	if i.COMMAND is not None:
		ACTIONS['OSK'][i.COMMAND] = i
