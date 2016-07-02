#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Custom action

Custom Action page in Action Editor window
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.gui.parser import GuiActionParser, InvalidAction
from scc.gui.ae import AEComponent
from scc.actions import Action

import os, logging
log = logging.getLogger("AE.Custom")

__all__ = [ 'CustomActionComponent' ]

class CustomActionComponent(AEComponent):
	GLADE = "ae/custom.glade"
	NAME = "custom"
	PRIORITY = -1
	CTXS = Action.AC_ALL
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self.parser = GuiActionParser()
	
	
	def handles(self, mode, action):
		# Custom Action Editor handles all actions
		return isinstance(action, Action)
	
	
	def get_button_title(self):
		return _("Custom Action")
	
	
	def load(self):
		if self.loaded : return
		AEComponent.load(self)
		try:
			txCustomAction = self.builder.get_object("txCustomAction")
			txCustomAction.set_monospace(True)
		except: pass
	
	
	def set_action(self, mode, action):
		action = self.editor.generate_modifiers(action, from_custom=True)
		tbCustomAction = self.builder.get_object("tbCustomAction")
		tbCustomAction.set_text(action.to_string(True))
	
	
	def on_tbCustomAction_changed(self, tbCustomAction, *a):
		"""
		Converts text from Custom Action text area into action instance and
		sends that instance back to editor.
		"""
		txCustomAction = self.builder.get_object("txCustomAction")
		txt = tbCustomAction.get_text(tbCustomAction.get_start_iter(), tbCustomAction.get_end_iter(), True)
		if len(txt.strip(" \t\r\n")) > 0:
			action = self.parser.restart(txt).parse()
			self.editor.set_action(action, from_custom=True)
	
	
	def shown(self):
		self.editor.set_modifiers_enabled(False)
	
	
	def hidden(self):
		self.editor.set_modifiers_enabled(True)
