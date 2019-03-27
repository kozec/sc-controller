#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Handles specific XYActions
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import ButtonAction, MultiAction, NoAction
from scc.actions import Action, AxisAction, MouseAction
from scc.gui.ae import AEComponent, describe_action
from scc.gui.area_to_action import action_to_area
from scc.gui.simple_chooser import SimpleChooser
from scc.gui.chooser import Chooser

import os, logging
log = logging.getLogger("AE.Axis")

__all__ = [ 'AxisComponent' ]


class AxisComponent(AEComponent, Chooser):
	GLADE = "ae/axis.glade"
	NAME = "axis"
	IMAGES = { "axis" : "axistrigger.svg" }
	CTXS = 0
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		Chooser.__init__(self, app)
		self.full = None
	
	
	def load(self):
		if not self.loaded:
			AEComponent.load(self)
			self.setup_image(grid_columns=2)
	
	
	def area_action_selected(self, area, action):
		if area:
			self.set_active_area(area)
		if self.full:
			action = MultiAction(ButtonAction(None, self.full), action)
		self.editor.set_action(action)
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			if isinstance(action, MultiAction) and len(action.actions) == 2:
				# axis + button on fully pressed trigger
				self.full = action.actions[0].button2
				self.builder.get_object("lblFullPressed").set_label(describe_action(Action.AC_BUTTON, ButtonAction, self.full))
				action = action.actions[1]
			area = action_to_area(action)
			if area is not None:
				self.set_active_area(area)
				return
		self.set_active_area(None)
	
	
	def get_button_title(self):
		return _("Trigger or Axis")
	
	
	def handles(self, mode, action):
		if isinstance(action, MultiAction) and len(action.actions) == 2:
			# Handles combination of axis + button on fully pressed trigger
			if not isinstance(action.actions[0], ButtonAction):
				return False
			action = action.actions[1]
		return isinstance(action, (AxisAction, MouseAction))
