#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Per-Axis Component

Handles all XYActions
"""

from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, XYAction
from scc.gui.ae import AEComponent, describe_action
from scc.gui.area_to_action import action_to_area
from scc.gui.simple_chooser import SimpleChooser
from scc.gui.parser import GuiActionParser

import os, logging
log = logging.getLogger("AE.PerAxis")

__all__ = [ 'PerAxisComponent' ]


class PerAxisComponent(AEComponent):
	GLADE = "ae/per_axis.glade"
	NAME = "per_axis"
	CTXS = Action.AC_STICK | Action.AC_PAD
	PRIORITY = 1
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self.x = self.y = NoAction()
	
	
	def set_action(self, mode, action):
		if isinstance(action, XYAction):
			self.x = action.x
			self.y = action.y
			self.update()
	
	
	def get_button_title(self):
		return _("Per Axis")
	
	
	def handles(self, mode, action):
		return isinstance(action, XYAction)
	
	
	def update(self):
		self.builder.get_object("lblAxisX").set_label(describe_action(Action.AC_STICK, None, self.x))
		self.builder.get_object("lblAxisY").set_label(describe_action(Action.AC_STICK, None, self.y))
	
	
	def send(self):
		self.editor.set_action(XYAction(self.x, self.y))
	
	
	def on_btAxisX_clicked(self, *a):
		""" 'Select X Axis Action' handler """
		def cb(action):
			self.x = action
			self.update()
			self.send()
		self.grab_action(self.x, cb)
	
	
	def on_btAxisY_clicked(self, *a):
		""" 'Select Y Axis Action' handler """
		def cb(action):
			self.y = action
			self.update()
			self.send()
		self.grab_action(self.y, cb)
	
	
	def grab_action(self, action, cb):
		b = SimpleChooser(self.app, "axis", cb)
		b.set_title(_("Select Axis"))
		area = action_to_area(action)
		b.display_action(Action.AC_STICK, area)
		b.show(self.editor.window)
	