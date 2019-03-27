#!/usr/bin/env python2
"""
SC-Controller - Action Editor - On Screen Keyboard Action Component

Assigns actions from scc.osd.osk_actions
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, ButtonAction
from scc.constants import LEFT, RIGHT
from scc.uinput import Keys
from scc.gui.ae import AEComponent
from scc.gui.parser import GuiActionParser
# from scc.osd.osk_actions import OSKAction, CloseOSKAction, OSKCursorAction
# from scc.osd.osk_actions import MoveOSKAction, OSKPressAction

import os, logging
log = logging.getLogger("AE.SA")

__all__ = [ 'OSKActionComponent' ]


class OSKActionComponent(AEComponent):
	GLADE = "ae/osk_action.glade"
	NAME = "osk_action"
	CTXS = Action.AC_OSK
	PRIORITY = 2
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self._recursing = False
	
	
	def set_action(self, mode, action):
		cb = self.builder.get_object("cbActionType")
		if isinstance(action, CloseOSKAction):
			self.set_cb(cb, "OSK.close()")
		elif isinstance(action, OSKCursorAction) and action.side == LEFT:
			self.set_cb(cb, "OSK.cursor(LEFT)")
		elif isinstance(action, OSKCursorAction): # and action.side == RIGHT:
			self.set_cb(cb, "OSK.cursor(RIGHT)")
		elif isinstance(action, OSKPressAction) and action.side == LEFT:
			self.set_cb(cb, "OSK.press(LEFT)")
		elif isinstance(action, OSKPressAction): # and action.side == RIGHT:
			self.set_cb(cb, "OSK.press(RIGHT)")
		elif isinstance(action, MoveOSKAction):
			self.set_cb(cb, "OSK.move()")
		if isinstance(action, ButtonAction):
			if action.button == Keys.BTN_LEFT:
				self.set_cb(cb, "button(Keys.BTN_LEFT)")
			elif action.button == Keys.BTN_RIGHT:
				self.set_cb(cb, "button(Keys.BTN_RIGHT)")
		else:
			self.set_cb(cb, "None")
	
	
	def get_button_title(self):
		return _("On-Screen Keyboard")
	
	
	def handles(self, mode, action):
		if isinstance(action, ButtonAction):
			return action.button in ( Keys.BTN_LEFT, Keys.BTN_RIGHT )
		return isinstance(action, (NoAction, OSKAction, OSKCursorAction))
	
	
	def on_cbActionType_changed(self, *a):
		cbActionType = self.builder.get_object("cbActionType")
		key = cbActionType.get_model().get_value(cbActionType.get_active_iter(), 0)
		self.editor.set_action(GuiActionParser().restart(key).parse())
		
