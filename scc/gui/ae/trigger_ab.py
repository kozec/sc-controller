#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Trigger-as-button Component

Assigns one or two emulated buttons to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, ButtonAction
from scc.actions import TRIGGER_HALF, TRIGGER_CLICK
from scc.gui.ae import AEComponent, describe_action
from scc.gui.area_to_action import action_to_area
from scc.gui.simple_chooser import SimpleChooser
from scc.gui.parser import InvalidAction

import os, logging
log = logging.getLogger("AE.TriggerAB")

__all__ = [ 'TriggerABComponent' ]


class TriggerABComponent(AEComponent):
	GLADE = "ae/trigger_ab.glade"
	NAME = "trigger_ab"
	CTXS = Action.AC_TRIGGER,
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self.half = None
		self.full = None
	
	
	def handles(self, mode, action):
		# Handles only None and ButtonAction
		return isinstance(action, (ButtonAction, NoAction, InvalidAction))
	
	
	def get_button_title(self):
		return _("Key or Button")
	
	
	def set_action(self, mode, action):
		self.half = None
		self.full = None
		if isinstance(action, ButtonAction):
			if len(action.parameters) > 1 and action.parameters[1]:
				self.half = action.parameters[0]
				self.full = action.parameters[1]
			else:
				self.half = action.parameters[0]
			if action.minustrigger is not None:
				self.builder.get_object("sclPartialLevel").set_value(action.minustrigger)
			if action.plustrigger is not None:
				self.builder.get_object("sclFullLevel").set_value(action.plustrigger)
			
		self.update()
	
	
	def update(self):
		self.builder.get_object("lblPartPressed").set_label(describe_action(Action.AC_BUTTON, ButtonAction, self.half))
		self.builder.get_object("lblFullPressed").set_label(describe_action(Action.AC_BUTTON, ButtonAction, self.full))
	
	
	def send(self):
		levels = []
		half_level = int(self.builder.get_object("sclPartialLevel").get_value() + 0.1)
		full_level = int(self.builder.get_object("sclFullLevel").get_value() + 0.1)
		
		if half_level != TRIGGER_HALF or full_level != TRIGGER_CLICK:
			levels.append(half_level)
		if full_level != TRIGGER_CLICK:
			levels.append(full_level)
		
		self.editor.set_action(ButtonAction(self.half, self.full, *levels))
	
	
	def on_btFullPressedClear_clicked(self, *a):
		self.full = None
		self.update()
		self.send()
	
	
	def on_triggerSclchange_value(self, *a):
		self.send()
	
	
	def on_btPartPressed_clicked(self, *a):
		""" 'Select Partialy Pressed Action' handler """
		def cb(action):
			self.half = action.button
			self.update()
			self.send()
		self.grab_action(self.half, cb)
	
	
	def on_btFullPress_clicked(self, *a):
		""" 'Select Fully Pressed Action' handler """
		def cb(action):
			self.full = action.button
			self.update()
			self.send()
		self.grab_action(self.full, cb)
	
	
	def grab_action(self, button, cb):
		b = SimpleChooser(self.app, "buttons", cb)
		b.set_title(_("Select Button"))
		b.hide_axes()
		b.display_action(Action.AC_BUTTON, ButtonAction(button))
		b.show(self.editor.window)
	
	
	def on_btFullyPresedClear_clicked(self, *a):
		self.builder.get_object("sclFullLevel").set_value(TRIGGER_CLICK)
	
	
	def on_btPartPresedClear_clicked(self, *a):
		self.builder.get_object("sclPartialLevel").set_value(TRIGGER_HALF)
