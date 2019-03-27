#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Assigns emulated axis to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.actions import ChangeProfileAction, ShellCommandAction
from scc.actions import TurnOffAction, KeyboardAction, OSDAction
from scc.actions import Action, NoAction, ResetGyroAction
from scc.actions import ClearOSDAction
from scc.gui.ae.menu_action import MenuActionCofC
from scc.gui.ae import AEComponent

import logging
log = logging.getLogger("AE.SA")

__all__ = [ 'SpecialActionComponent' ]


class SpecialActionComponent(AEComponent, MenuActionCofC):
	GLADE = "ae/special_action.glade"
	NAME = "special_action"
	CTXS = Action.AC_BUTTON | Action.AC_MENU
	PRIORITY = 0
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		MenuActionCofC.__init__(self)
		self._userdata_load_started = False
		self._recursing = False
		self._current_profile = None
	
	
	def load(self):
		if self.loaded : return
		AEComponent.load(self)
		cbConfirmWith = self.builder.get_object("cbConfirmWith")
		cbCancelWith = self.builder.get_object("cbCancelWith")
		cbConfirmWith.set_row_separator_func( lambda model, iter : model.get_value(iter, 0) == "-" )
		cbCancelWith.set_row_separator_func( lambda model, iter : model.get_value(iter, 0)  == "-" )
	
	
	def shown(self):
		if not self._userdata_load_started:
			self._userdata_load_started = True
			self.load_profile_list()
			self.load_menu_list()
	
	
	def confirm_with_same_active(self):
		cbMenuAutoConfirm = self.builder.get_object("cbMenuAutoConfirm")
		return cbMenuAutoConfirm.get_active()
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			cb = self.builder.get_object("cbActionType")
			if isinstance(action, TurnOffAction):
				self.set_cb(cb, "turnoff")
			elif isinstance(action, ShellCommandAction):
				self.set_cb(cb, "shell")
				enCommand = self.builder.get_object("enCommand")
				enCommand.set_text(action.command.encode("utf-8"))
			elif isinstance(action, ResetGyroAction):
				self.set_cb(cb, "resetgyro")
			elif isinstance(action, ChangeProfileAction):
				self._current_profile = action.profile
				self.set_cb(cb, "profile")
			elif MenuActionCofC.handles(self, None, action):
				self.set_cb(cb, "menu")
				self.load_menu_data(action)
			elif isinstance(action, KeyboardAction):
				self.set_cb(cb, "keyboard")
			elif isinstance(action, OSDAction):
				self.set_cb(cb, "osd")
				sclOSDTimeout = self.builder.get_object("sclOSDTimeout")
				enOSDText = self.builder.get_object("enOSDText")
				cbOSDSize = self.builder.get_object("cbOSDSize")
				self._recursing = True
				sclOSDTimeout.set_value(action.timeout or 60.1)
				enOSDText.set_text(action.text)
				self.set_cb(cbOSDSize, action.size)
				self._recursing = False
			elif isinstance(action, ClearOSDAction):
				self.set_cb(cb, "clearosd")
			else:
				self.set_cb(cb, "none")
	
	
	def on_profiles_loaded(self, profiles):
		cb = self.builder.get_object("cbProfile")
		model = cb.get_model()
		model.clear()
		i, current_index = 0, 0
		for f in sorted(profiles, key=lambda f: f.get_basename()):
			name = f.get_basename()
			if name.endswith(".mod"):
				continue
			if name.startswith("."):
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
	
	
	def get_button_title(self):
		return _("Special Action")
	
	
	def handles(self, mode, action):
		if MenuActionCofC.handles(self, mode, action):
			return True
		if isinstance(action, OSDAction) and action.action is None:
			return True
		return isinstance(action, (NoAction, TurnOffAction, ShellCommandAction,
			ChangeProfileAction, KeyboardAction, ClearOSDAction, ResetGyroAction))
	
	
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
		elif key == "clearosd":
			stActionData.set_visible_child(self.builder.get_object("nothing"))
			if not self._recursing:
				self.editor.set_action(ClearOSDAction())
		elif key == "resetgyro":
			stActionData.set_visible_child(self.builder.get_object("nothing"))
			if not self._recursing:
				self.editor.set_action(ResetGyroAction())
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
	
	
	def on_enCommand_changed(self, *a):
		if self._recursing : return
		enCommand = self.builder.get_object("enCommand")
		self.editor.set_action(ShellCommandAction(enCommand.get_text().decode("utf-8")))
	
	
	def on_osd_settings_changed(self, *a):
		if self._recursing : return
		enOSDText = self.builder.get_object("enOSDText")
		sclOSDTimeout = self.builder.get_object("sclOSDTimeout")
		cbOSDSize = self.builder.get_object("cbOSDSize")
		timeout = sclOSDTimeout.get_value()
		size = cbOSDSize.get_model().get_value(cbOSDSize.get_active_iter(), 0)
		self.editor.set_action(OSDAction(
			0 if timeout > 60.0 else timeout,
			size,
			enOSDText.get_text().decode("utf-8"
		)))
	
	
	def on_exMenuControl_activate(self, ex, *a):
		rvMenuControl = self.builder.get_object("rvMenuControl")
		rvMenuControl.set_reveal_child(not ex.get_expanded())
	
	
	def on_exMenuPosition_activate(self, ex, *a):
		rvMenuPosition = self.builder.get_object("rvMenuPosition")
		rvMenuPosition.set_reveal_child(not ex.get_expanded())
	
	
	def on_sclOSDTimeout_format_value(self, scale, value):
		if value > 60.0:
			return _("forever")
		elif value < 1:
			return "%sms" % int(value * 1000)
		else:
			return "%ss" % value
