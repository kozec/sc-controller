#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Assigns emulated axis to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.special_actions import ChangeProfileAction, ShellCommandAction
from scc.special_actions import TurnOffAction, KeyboardAction, OSDAction
from scc.special_actions import MenuAction
from scc.actions import Action, NoAction
from scc.gui.userdata_manager import UserDataManager
from scc.gui.parser import GuiActionParser
from scc.gui.ae import AEComponent

import os, logging
log = logging.getLogger("AE.SpecialAction")

__all__ = [ 'SAComponent' ]


class SpecialActionComponent(AEComponent, UserDataManager):
	GLADE = "ae/special_action.glade"
	NAME = "special_action"
	CTXS = Action.AC_BUTTON,
	PRIORITY = 0
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		UserDataManager.__init__(self)
		self._recursing = False
		self._userdata_load_started = False
		self._current_profile = None
		self._current_menu = None
		self.parser = GuiActionParser()
	
	
	def load(self):
		if self.loaded : return
		AEComponent.load(self)
	
	
	def shown(self):
		if not self._userdata_load_started:
			self._userdata_load_started = True
			self.load_profile_list()
			self.load_menu_list()
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			if isinstance(action, TurnOffAction):
				self.select_action_type("turnoff")
			elif isinstance(action, ShellCommandAction):
				self.select_action_type("shell")
				enCommand = self.builder.get_object("enCommand")
				enCommand.set_text(action.command)
			elif isinstance(action, ChangeProfileAction):
				self._current_profile = action.profile
				self.select_action_type("profile")
			elif isinstance(action, MenuAction):
				self._current_menu = action.menu_id
				self.select_action_type("menu")
			elif isinstance(action, KeyboardAction):
				self.select_action_type("keyboard")
			elif isinstance(action, OSDAction):
				self.select_action_type("osd")
				enOSDText = self.builder.get_object("enOSDText")
				enOSDText.set_text(action.text)
			else:
				self.select_action_type("none")
	
	
	def on_profiles_loaded(self, profiles):
		cb = self.builder.get_object("cbProfile")
		model = cb.get_model()
		model.clear()
		i, current_index = 0, 0
		for f in profiles:
			name = f.get_basename()
			if name.endswith(".mod"):
				continue
			if name.endswith(".sccprofile"):
				name = name[0:-11]
			if name == self._current_profile:
				current_index = i
			model.append((name, f, None))
			i += 1
		
		self._recursing = True
		cb.set_active(current_index)
		self._recursing = False
	
	
	def on_menus_loaded(self, menus):
		cb = self.builder.get_object("cbMenus")
		cb.set_row_separator_func( lambda model, iter : model.get_value(iter, 1) is None )
		model = cb.get_model()
		model.clear()
		i, current_index = 0, 0
		# Add menus from profile
		for key in self.app.current.menus:
			model.append((key, key))
			if self._current_menu == key:
				current_index = i
			i += 1
		if i > 0:
			model.append((None, None))	# Separator
			i += 1
		for f in menus:
			name = f.get_basename()
			key = name
			model.append((name, key))
			if self._current_menu == key:
				current_index = i
			i += 1
		
		self._recursing = True
		cb.set_active(current_index)
		self._recursing = False
	
	
	def get_button_title(self):
		return _("Special Action")
	
	
	def handles(self, mode, action):
		return isinstance(action, (NoAction, TurnOffAction, ShellCommandAction,
			ChangeProfileAction, KeyboardAction, OSDAction, MenuAction))
	
	
	def select_action_type(self, key):
		""" Just sets combobox value """
		cb = self.builder.get_object("cbActionType")
		model = cb.get_model()
		self._recursing = True
		for row in model:
			if key == row[0]:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return
		self._recursing = False
	
	
	def on_cbActionType_changed(self, *a):
		cbActionType = self.builder.get_object("cbActionType")
		stActionData = self.builder.get_object("stActionData")
		key = cbActionType.get_model().get_value(cbActionType.get_active_iter(), 0)
		if key == "shell":
			stActionData.set_visible_child(self.builder.get_object("vbShell"))
			self.on_enCommand_changed()
		elif key == "profile":
			stActionData.set_visible_child(self.builder.get_object("vbProfile"))
			self.on_cbProfile_changed()
		elif key == "keyboard":
			stActionData.set_visible_child(self.builder.get_object("nothing"))
			if not self._recursing:
				self.editor.set_action(KeyboardAction())
		elif key == "osd":
			stActionData.set_visible_child(self.builder.get_object("vbOSD"))
			if not self._recursing:
				self.editor.set_action(OSDAction(""))
		elif key == "menu":
			stActionData.set_visible_child(self.builder.get_object("grMenu"))
			self.on_cbMenus_changed()
		elif key == "turnoff":
			stActionData.set_visible_child(self.builder.get_object("nothing"))
			if not self._recursing:
				self.editor.set_action(TurnOffAction())
		else: # none
			stActionData.set_visible_child(self.builder.get_object("nothing"))
			if not self._recursing:
				self.editor.set_action(NoAction())
	
	
	def on_cbProfile_changed(self, *a):
		""" Called when user chooses profile in selection combo """
		if self._recursing : return
		cb = self.builder.get_object("cbProfile")
		model = cb.get_model()
		iter = cb.get_active_iter()
		if iter is None:
			# Empty list
			return
		f = model.get_value(iter, 1)
		name = f.get_basename()
		if name.endswith(".sccprofile"):
			name = name[0:-11]
		self.editor.set_action(ChangeProfileAction(name))
	
	
	def on_cbMenus_changed(self, *a):
		""" Called when user chooses menu in selection combo """
		if self._recursing : return
		cb = self.builder.get_object("cbMenus")
		model = cb.get_model()
		iter = cb.get_active_iter()
		if iter is None:
			# Empty list
			return
		name = model.get_value(iter, 1)
		self.editor.set_action(MenuAction(name))
	
	
	def on_enCommand_changed(self, *a):
		if self._recursing : return
		enCommand = self.builder.get_object("enCommand")
		self.editor.set_action(ShellCommandAction(enCommand.get_text()))
	
	
	def on_enOSDText_changed(self, *a):
		if self._recursing : return
		enOSDText = self.builder.get_object("enOSDText")
		self.editor.set_action(OSDAction(enOSDText.get_text()))
