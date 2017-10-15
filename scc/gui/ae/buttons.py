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
from scc.macros import Cycle, PressAction, ReleaseAction
from scc.uinput import Rels, Keys
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
	MODIFIER_KEYS = ( Keys.KEY_LEFTSHIFT, Keys.KEY_LEFTMETA, Keys.KEY_LEFTALT,
		Keys.KEY_LEFTCTRL, Keys.KEY_RIGHTMETA, Keys.KEY_RIGHTSHIFT,
		Keys.KEY_RIGHTCTRL, Keys.KEY_RIGHTALT,
	)
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		Chooser.__init__(self, app)
		self.axes_allowed = True
		self.keys = set()
	
	
	def load(self):
		if not self.loaded:
			AEComponent.load(self)
			self.setup_image()
	
	
	def area_action_selected(self, area, action):
		self.set_active_area(area)
		self.editor.set_action(action)
	
	
	def set_action(self, mode, action):
		cbToggle = self.builder.get_object("cbToggle")
		if self.handles(mode, action):
			self.keys = set()
			is_togle = False
			if isinstance(action, MultiAction):
				for a in action.actions:
					if isinstance(a, ButtonAction):
						self.keys.add(a.button)
			elif isinstance(action, ButtonAction):
				self.keys.add(action.button)
			elif isinstance(action, Cycle):
				# There is only one case when self.handles returns True for Cycle
				self.keys.add(action.actions[0].action.button)
				is_togle = True
			cbToggle.set_active(is_togle)
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
		if is_button_togle(action):
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
		self.keys = set(keys)
		self.apply_keys()
	
	
	def on_additional_key_grabbed(self, keys):
		self.keys.update(keys)
		self.apply_keys()
	
	
	@staticmethod
	def modifiers_first(key):
		if key in ButtonsComponent.MODIFIER_KEYS:
			return 0
		return 1
	
	
	def apply_keys(self, *a):
		""" Common part of on_*key_grabbed """
		cbToggle = self.builder.get_object("cbToggle")
		keys = list(sorted(self.keys, key=ButtonsComponent.modifiers_first))
		print keys
		action = ButtonAction(keys[0])
		if len(keys) > 1:
			actions = [ ButtonAction(k) for k in keys ]
			action = MultiAction(*actions)
		if cbToggle.get_active():
			action = Cycle(PressAction(action), ReleaseAction(action))
		self.editor.set_action(action)
	
	
	def on_btnGrabKey_clicked(self, *a):
		"""
		Called when user clicks on 'Grab a Key' button.
		Displays additional dialog.
		"""
		kg = KeyGrabber(self.app)
		kg.grab(self.editor.window, self.editor._action, self.on_key_grabbed)
	
	
	def on_btnGrabAnother_clicked(self, *a):
		"""
		Same as above, but adds another key to action
		"""
		kg = KeyGrabber(self.app)
		kg.grab(self.editor.window, self.editor._action,
				self.on_additional_key_grabbed)
	
	
	def hide_axes(self):
		""" Prevents user from selecting axes """
		self.axes_allowed = False


def is_button_togle(action):
	if not isinstance(action, Cycle):
		return False
	if len(action.actions) != 2:
		return False
	if isinstance(action.actions[0], PressAction):
		if isinstance(action.actions[1], ReleaseAction):
			if isinstance(action.actions[0].action, ButtonAction):
				if isinstance(action.actions[1].action, ButtonAction):
					return action.actions[0].action.button == action.actions[1].action.button
	return False
