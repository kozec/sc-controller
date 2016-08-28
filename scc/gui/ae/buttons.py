#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Button Component

Assigns emulated button to physical button
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, ButtonAction, MouseAction
from scc.actions import AxisAction, MultiAction, NoAction
from scc.uinput import Rels
from scc.gui.area_to_action import action_to_area
from scc.gui.key_grabber import KeyGrabber
from scc.gui.parser import InvalidAction
from scc.gui.chooser import Chooser
from scc.gui.ae import AEComponent

import os, logging
log = logging.getLogger("AE.Buttons")

__all__ = [ 'ButtonsComponent' ]


class ButtonsComponent(AEComponent, Chooser):
	GLADE = "ae/buttons.glade"
	NAME = "buttons"
	IMAGES = { "buttons" : "buttons.svg" }
	CTXS = Action.AC_BUTTON | Action.AC_MENU
	PRIORITY = 1
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		Chooser.__init__(self, app)
		self.axes_allowed = True
	
	
	def load(self):
		if not self.loaded:
			AEComponent.load(self)
			self.setup_image()
			if self.app.osd_controller:
				self.enable_cursors(self.app.osd_controller)
	
	
	def shown(self):
		if self.app.osd_controller:
			self.align_image()
	
	
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
		return _("Key or Button")
	
	
	def handles(self, mode, action):
		# Handles ButtonAction and MultiAction if all subactions are ButtonAction
		if isinstance(action, (ButtonAction, NoAction, InvalidAction)):
			return True
		if isinstance(action, AxisAction):
			return len(action.parameters) == 1
		if isinstance(action, MouseAction):
			if action.get_axis() == Rels.REL_WHEEL:
				return True
		if isinstance(action, MultiAction):
			if len(action.actions) > 0:
				for a in action.actions:
					if not isinstance(a, ButtonAction):
						return False
				return True
		return False
	
	
	def on_key_grabbed(self, keys):
		""" Handles selecting key using "Grab the Key" dialog """
		action = ButtonAction(keys[0])
		if len(keys) > 1:
			actions = [ ButtonAction(k) for k in keys ]
			action = MultiAction(*actions)
		self.editor.set_action(action)
	
	
	def on_btnGrabKey_clicked(self, *a):
		"""
		Called when user clicks on 'Grab a Key' button.
		Displays additional dialog.
		"""
		kg = KeyGrabber(self.app)
		kg.grab(self.editor.window, self.editor._action, self.on_key_grabbed)
	
	
	def hide_axes(self):
		""" Prevents user from selecting axes """
		self.axes_allowed = False
