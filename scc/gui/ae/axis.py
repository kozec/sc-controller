#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Handles specific XYActions
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, AxisAction, MouseAction
from scc.gui.area_to_action import action_to_area
from scc.gui.chooser import Chooser
from scc.gui.ae import AEComponent

import os, logging
log = logging.getLogger("AE.Axis")

__all__ = [ 'AxisComponent' ]


class AxisComponent(AEComponent, Chooser):
	GLADE = "ae/axis.glade"
	NAME = "axis"
	IMAGES = { "axis" : "axistrigger.svg" }
	CTXS = Action.AC_TRIGGER,
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		Chooser.__init__(self, app)
		self.axes_allowed = True
	
	
	def load(self):
		if not self.loaded:
			AEComponent.load(self)
			self.setup_image()
	
	
	def area_action_selected(self, area, action):
		self.set_active_area(area)
		self.editor.set_action(action)
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			area = action_to_area(action)
			if area is not None:
				self.set_active_area(area)
				return
		self.set_active_area(None)
	
	
	def get_button_title(self):
		return _("Trigger or Axis")
	
	
	def handles(self, mode, action):
		return isinstance(action, AxisAction) or isinstance(action, MouseAction)
	
	
	def hide_axes(self):
		""" Prevents user from selecting axes """
		self.axes_allowed = False
