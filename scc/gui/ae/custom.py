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
		# Custom Action Editor handles everything
		return True
	
	
	def get_button_title(self):
		return _("Custom Action")


	def set_action(self, mode, action):
		print "custom:set_action", action
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
			if txt.startswith("X:"):
				# Special case, there are two separate actions for X and Y axis defined
				index = txt.find("Y:")
				if index == -1:
					# There is actions for X axis but not for Y
					txt = "XY(" + txt[2:] + ")"
				else:
					# Both X and Y actions are defined
					x = txt[2:index]
					y = txt[index+2:]
					txt = "XY(" + x + "," + y + ")"
			action = self.parser.restart(txt).parse()
			self.editor.set_action(action)
