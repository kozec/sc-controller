#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
SC-Controller - Action Editor - "DPAD or Menu"

Setups DPAD emulation or menu display
"""

from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import HatUpAction, HatDownAction, HatLeftAction,HatRightAction
from scc.actions import Action, NoAction, DPadAction, DPad8Action, ButtonAction
from scc.constants import LEFT, RIGHT, STICK, SAME, DEFAULT, SCButtons
from scc.modifiers import NameModifier
from scc.special_actions import MenuAction
from scc.uinput import Keys, Axes
from scc.gui.ae import AEComponent, describe_action
from scc.gui.ae.menu_action import MenuActionCofC
from scc.gui.binding_editor import BindingEditor
from scc.gui.action_editor import ActionEditor


import os, logging
log = logging.getLogger("AE.DPAD")

__all__ = [ 'DPADComponent' ]


class DPADComponent(AEComponent, MenuActionCofC, BindingEditor):
	GLADE = "ae/dpad.glade"
	NAME = "dpad"
	CTXS = Action.AC_STICK | Action.AC_PAD
	PRIORITY = 2
	
	DPAD8_WIDGETS = [ 'btDPAD4', 'btDPAD5', 'btDPAD6', 'btDPAD7' ]
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		MenuActionCofC.__init__(self)
		BindingEditor.__init__(self, app)
		self._recursing = False
		self._userdata_load_started = False
		self.actions = [ NoAction() ] * 8
	
	
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
			self.load_menu_list()
	
	
	def set_action(self, mode, action):
		cbm = self.builder.get_object("cbMenuType")
		cb = self.builder.get_object("cbActionType")
		scl = self.builder.get_object("sclDiagonalRange")
		if isinstance(action, DPadAction):
			self.set_cb(cbm, "menu", 1)
			scl.set_value(action.diagonal_rage)
			if isinstance(action, DPad8Action):
				self.set_cb(cb, "dpad8", 1)
			else:
				self.set_cb(cb, "dpad", 1)
			self.update_button_desc(action)
		elif MenuActionCofC.handles(self, None, action):
			self.set_cb(cb, "menu", 1)
			self.load_menu_data(action)
		self.on_cbActionType_changed()
	
	
	def update_button_desc(self, action):
		for i in range(0, len(action.actions)):
			self.actions[i] = action.actions[i]
		for i in range(0, 8):
			self.set_button_desc(i)
	
	
	def set_button_desc(self, i):
		desc = describe_action(Action.AC_BUTTON, None, self.actions[i])
		l = self.builder.get_object("lblDPAD%s" % (i,))
		if l is None:
			l = self.builder.get_object("btDPAD%s" % (i,)).get_children()[0]
		l.set_markup(desc)
	
	
	def get_button_title(self):
		return _("DPAD / Menu")
	
	
	def handles(self, mode, action):
		if MenuActionCofC.handles(self, mode, action):
			return True
		return isinstance(action, DPadAction) # DPad8Action is derived from DPadAction
	
	
	def update(self):
		cb = self.builder.get_object("cbActionType")
		scl = self.builder.get_object("sclDiagonalRange")
		key = cb.get_model().get_value(cb.get_active_iter(), 1)
		if key == "dpad8":
			# 8-way dpad
			self.editor.set_action(DPad8Action(scl.get_value(), *self.actions))
		elif key == "dpad":
			# 4-way dpad
			self.editor.set_action(DPadAction(scl.get_value(),
				*self.actions[0:4]))
		elif key == "wsad":
			# special case of 4-way dpad
			a = DPadAction(scl.get_value(),
				ButtonAction(Keys.KEY_W), ButtonAction(Keys.KEY_S),
				ButtonAction(Keys.KEY_A), ButtonAction(Keys.KEY_D))
			self.actions = [ NoAction() ] * 8
			self.editor.set_action(a)
			self.update_button_desc(a)
		elif key == "arrows":
			# special case of 4-way dpad
			a = DPadAction(scl.get_value(),
				ButtonAction(Keys.KEY_UP), ButtonAction(Keys.KEY_DOWN),
				ButtonAction(Keys.KEY_LEFT), ButtonAction(Keys.KEY_RIGHT))
			self.actions = [ NoAction() ] * 8
			self.editor.set_action(a)
			self.update_button_desc(a)
		elif key == "actual_dpad":
			# maps to dpad as real gamepad usually has
			a = DPadAction(scl.get_value(),
				HatUpAction(Axes.ABS_HAT0Y), HatDownAction(Axes.ABS_HAT0Y),
				HatLeftAction(Axes.ABS_HAT0X), HatRightAction(Axes.ABS_HAT0X))
			self.actions = [ NoAction() ] * 8
			self.editor.set_action(a)
			self.update_button_desc(a)
		else:
			# Menu
			self.on_cbMenus_changed()
	
	
	def on_cbActionType_changed(self, *a):
		if self._recursing: return
		cb = self.builder.get_object("cbActionType")
		stActionData = self.builder.get_object("stActionData")
		key = cb.get_model().get_value(cb.get_active_iter(), 1)
		if key in ("dpad", "dpad8", "wsad", "arrows", "actual_dpad"):
			for i in self.DPAD8_WIDGETS:
				self.builder.get_object(i).set_visible(key == "dpad8")
			stActionData.set_visible_child(self.builder.get_object("grDPAD"))
		else: # key == "menu"
			stActionData.set_visible_child(self.builder.get_object("grMenu"))
		self.update()
	
	
	def on_action_chosen(self, i, action, mark_changed=True):
		self.actions[i] = action
		cb = self.builder.get_object("cbActionType")
		key = cb.get_model().get_value(cb.get_active_iter(), 1)
		if key != "dpad8":
			# When user chooses WSAD, Arrows or DPAD emulation and then changes
			# one of actions, swap back to 'Simple DPAD' mode.
			self.set_cb(cb, "dpad", 1)
		#if action.name:
		#	action = NameModifier(action.name, action)
		self.set_button_desc(i)
		self.update()
	
	
	def on_sclDiagonalRange_format_value(self, scale, value):
		return _("%s°") % (value,)
	
	
	def on_btClearDiagonalRange_clicked(self, *a):
		scl = self.builder.get_object("sclDiagonalRange")
		scl.set_value(DPadAction.DEFAULT_DIAGONAL_RANGE)
	
	
	def on_sclDiagonalRange_value_changed(self, *a):
		self.update()
	
	
	def on_btDPAD_clicked(self, b):
		""" 'Select DPAD Left Action' handler """
		i = int(b.get_name())
		action = self.actions[i]
		#f isinstance(action, NameModifier):
		#action.action.name = action.name
		#action = action.action
		ae = self.choose_editor(action, "")
		# ae = ActionEditor(self.app, self.on_choosen)
		ae.set_title(_("Select DPAD Action"))
		ae.set_input(i, action, mode = Action.AC_BUTTON)
		ae.show(self.editor.window)
	
	
	def get_default_confirm(self):
		"""
		Returns default confirm button for pads/stick - LPAD, RPAD or STICKPRESS
		"""
		if self.editor.id == STICK:
			return SCButtons.STICKPRESS
		return getattr(SCButtons, self.editor.id)
	
	
	def get_default_cancel(self):
		"""
		Returns default cancel button for stick/pad - SAME or B
		"""
		if self.editor.id == STICK:
			return SCButtons.B
		return SAME
	
	
	def get_control_with(self):
		"""
		'control_with' argument is ignored when menu is used with stick/pad.
		"""
		return DEFAULT
	
	
	def on_exMenuControl_activate(self, ex, *a):
		rvMenuControl = self.builder.get_object("rvMenuControl")
		rvMenuControl.set_reveal_child(not ex.get_expanded())
	
	
	def on_exMenuPosition_activate(self, ex, *a):
		rvMenuPosition = self.builder.get_object("rvMenuPosition")
		rvMenuPosition.set_reveal_child(not ex.get_expanded())
