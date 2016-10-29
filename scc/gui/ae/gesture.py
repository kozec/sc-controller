#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Per-Axis Component

Handles all XYActions
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib, GObject
from scc.actions import Action, NoAction, XYAction
from scc.special_actions import GesturesAction
from scc.gui.ae import AEComponent, describe_action
from scc.gui.area_to_action import action_to_area
from scc.gui.gestures import GestureCellRenderer
from scc.gui.simple_chooser import SimpleChooser
from scc.gui.parser import GuiActionParser

import os, logging
log = logging.getLogger("AE.PerAxis")

__all__ = [ 'GestureComponent' ]


class GestureComponent(AEComponent):
	GLADE = "ae/gesture.glade"
	NAME = "gesture"
	CTXS = Action.AC_STICK | Action.AC_PAD
	PRIORITY = 1
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self.x = self.y = NoAction()
	
	
	def load(self):
		if AEComponent.load(self):
			tvGestures = self.builder.get_object("tvGestures")
			tvGestures.insert_column_with_attributes(0,
				_("Image"),
				GestureCellRenderer(),
				gesture=0
			)
	
	
	def set_action(self, mode, action):
		lstGestures = self.builder.get_object("lstGestures")
		lstGestures.clear()
		if isinstance(action, GesturesAction):
			for gstr in action.gestures:
				o = GObject.GObject()
				o.action = action.gestures[gstr]
				o.str = gstr
				lstGestures.append( ( unicode(gstr), o.action.describe(Action.AC_MENU), o) )
	
	
	def get_button_title(self):
		return _("Gestures")
	
	
	def handles(self, mode, action):
		return isinstance(action, GesturesAction)
	
	
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
