#!/usr/bin/env python2
"""
SC-Controller - Action Editor - common part of "DPAD or menu" and "Special Action",
two components with MenuAction selectable.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.special_actions import MenuAction, HorizontalMenuAction
from scc.special_actions import RadialMenuAction, GridMenuAction
from scc.special_actions import PositionModifier
from scc.constants import SCButtons, SAME, STICK
from scc.actions import NoAction
from scc.tools import nameof
from scc.gui.userdata_manager import UserDataManager
from scc.gui.menu_editor import MenuEditor
from scc.gui.parser import GuiActionParser
from scc.gui.ae import AEComponent

import os, logging
log = logging.getLogger("AE.Menu")

__all__ = [ 'MenuActionCofC' ]


class MenuActionCofC(UserDataManager):
	# CofC - Component of Component
	def __init__(self):
		UserDataManager.__init__(self)
		self._current_menu = None
		self.parser = GuiActionParser()
		self.allow_globals = True
		self.allow_in_profile = True
	
	
	def allow_menus(self, allow_globals, allow_in_profile):
		"""
		Sets which type of menu should be selectable.
		By default, both are enabled.
		
		Returns self.
		"""
		self.allow_globals = allow_globals
		self.allow_in_profile = allow_in_profile
		return self
	
	
	def set_selected_menu(self, menu):
		"""
		Sets menu selected in combobox.
		Returns self.
		"""
		self._current_menu = menu
		# TODO: This currently works only if menu list is not yet loaded
	
	
	@staticmethod
	def menu_class_to_key(action):
		"""
		For subclass of MenuAction, returns correct key to be used in ListStore.
		"""
		if isinstance(action, GridMenuAction):
			return "gridmenu"
		elif isinstance(action, HorizontalMenuAction):
			return "hmenu"
		elif isinstance(action, RadialMenuAction):
			return "radialmenu"
		else:
			return "menu"
	
	
	def load_menu_data(self, action):
		if isinstance(action, PositionModifier):
			# Load menu position modifier, if used
			x, y = action.position
			self.builder.get_object("cbMenuPosX").set_active(0 if x >= 0 else 1)
			self.builder.get_object("cbMenuPosY").set_active(0 if y >= 0 else 1)
			self.builder.get_object("spMenuPosX").set_value(abs(x))
			self.builder.get_object("spMenuPosY").set_value(abs(y))
			action = action.action
		
		self._current_menu = action.menu_id
		cbm = self.builder.get_object("cbMenuType")
		self.set_cb(cbm, self.menu_class_to_key(action), 1)
		
		if self.builder.get_object("rvMaxSize"):
			rvMaxSize = self.builder.get_object("rvMaxSize")
			spMaxSize = self.builder.get_object("spMaxSize")
			visible = isinstance(action, GridMenuAction)
			max_size = spMaxSize.get_adjustment().set_value(action.max_size)
			rvMaxSize.set_reveal_child(visible)
		
		cbControlWith = self.builder.get_object("cbControlWith")
		cbConfirmWith = self.builder.get_object("cbConfirmWith")
		cbCancelWith = self.builder.get_object("cbCancelWith")
		cbMenuAutoConfirm = self.builder.get_object("cbMenuAutoConfirm")
		cbMenuConfirmWithClick = self.builder.get_object("cbMenuConfirmWithClick")
		if cbControlWith:
			self.set_cb(cbControlWith, nameof(action.control_with), 1)
			self.set_cb(cbConfirmWith, nameof(action.confirm_with), 1)
			self.set_cb(cbCancelWith, nameof(action.cancel_with), 1)
		if cbMenuAutoConfirm:
			cbMenuAutoConfirm.set_active(action.confirm_with == SAME)
		if cbMenuConfirmWithClick:
			cbMenuAutoConfirm.set_active(action.confirm_with == self.get_default_confirm())
	
	
	def get_default_confirm(self):
		"""
		Returns MenuAction.DEFAULT_CONFIRM, but may be overriden when default
		confirm button is different - specifically when used with pads.
		"""
		return MenuAction.DEFAULT_CONFIRM
	
	
	def get_default_cancel(self):
		"""
		Returns MenuAction.DEFAULT_CONFIRM, but may be overriden when default
		confirm button is different - specifically when used with pads.
		"""
		return MenuAction.DEFAULT_CANCEL
	
	
	def on_menu_changed(self, new_id):
		self._current_menu = new_id
		self.editor.set_action(MenuAction(new_id))
		self.load_menu_list()
	
	
	def on_btEditMenu_clicked(self, *a):
		name = self.get_selected_menu()
		if name:
			log.debug("Editing %s", name)
			me = MenuEditor(self.app, self.on_menu_changed)
			id = self.get_selected_menu()
			log.debug("Opening editor for menu ID '%s'", id)
			me.set_menu(id)
			me.allow_menus(self.allow_globals, self.allow_in_profile)
			me.show(self.editor.window)
	
	
	def on_menus_loaded(self, menus):
		cb = self.builder.get_object("cbMenus")
		cb.set_row_separator_func( lambda model, iter : model.get_value(iter, 1) is None )
		model = cb.get_model()
		model.clear()
		i, current_index = 0, 0
		if self.allow_in_profile:
			# Add menus from profile
			for key in sorted(self.app.current.menus):
				model.append((key, key))
				if self._current_menu == key:
					current_index = i
				i += 1
			if i > 0:
				model.append((None, None))	# Separator
				i += 1
		if self.allow_globals:
			for f in menus:
				key = f.get_basename()
				name = key
				if name.startswith("."): continue
				if "." in name:
					name = _("%s (global)" % (name.split(".")[0]))
				model.append((name, key))
				if self._current_menu == key:
					current_index = i
				i += 1
		if i > 0:
			model.append((None, None))	# Separator
		model.append(( _("New Menu..."), "" ))
		
		self._recursing = True
		cb.set_active(current_index)
		self._recursing = False
		name = self.get_selected_menu()
		if name:
			self.builder.get_object("btEditMenu").set_sensitive(name not in MenuEditor.OPEN)
	
	
	def handles(self, mode, action):
		if isinstance(action, PositionModifier):
			return isinstance(action.action, MenuAction)
		return isinstance(action, MenuAction)
	
	
	def get_selected_menu(self):
		cb = self.builder.get_object("cbMenus")
		model = cb.get_model()
		iter = cb.get_active_iter()
		if iter is None:
			# Empty list
			return None
		return model.get_value(iter, 1)
	
	
	def confirm_with_same_active(self):
		"""
		Returns value of 'Confirm selection by releasing the button' checkbox,
		if there is any.
		"""
		return False	# there isn't any by default
	
	
	def prevent_confirm_cancel_nonsense(self, widget, *a):
		"""
		If 'confirm with click', 'confirm with release' and
		'cbMenuAutoCancel' are all present, this method prevents them from
		being checked in nonsensical way.
		"""
		cbMenuConfirmWithClick = self.builder.get_object("cbMenuConfirmWithClick")
		cbMenuAutoConfirm = self.builder.get_object("cbMenuAutoConfirm")
		cbMenuAutoCancel = self.builder.get_object("cbMenuAutoCancel")
		if widget.get_active():
			if widget == cbMenuConfirmWithClick:
				if cbMenuAutoConfirm:
					cbMenuAutoConfirm.set_active(False)
			elif widget == cbMenuAutoConfirm:
				if cbMenuConfirmWithClick:
					cbMenuConfirmWithClick.set_active(False)
				if cbMenuAutoCancel:
					cbMenuAutoCancel.set_active(False)
			elif widget == cbMenuAutoCancel:
				if cbMenuAutoConfirm:
					cbMenuAutoConfirm.set_active(False)
	
	
	def on_cbMenus_changed(self, *a):
		""" Called when user changes any menu settings """
		if self._recursing : return
		cbMenuConfirmWithClick = self.builder.get_object("cbMenuConfirmWithClick")
		cbMenuAutoConfirm = self.builder.get_object("cbMenuAutoConfirm")
		cbMenuAutoCancel = self.builder.get_object("cbMenuAutoCancel")
		lblConfirmWith = self.builder.get_object("lblConfirmWith")
		cbConfirmWith = self.builder.get_object("cbConfirmWith")
		cbCancelWith = self.builder.get_object("cbCancelWith")
		
		if cbConfirmWith:
			sensitive = True
			if cbMenuAutoConfirm and cbMenuAutoConfirm.get_active():
				sensitive = False
			if cbMenuConfirmWithClick and cbMenuConfirmWithClick.get_active():
				sensitive = False
			lblConfirmWith.set_sensitive(sensitive)
			cbConfirmWith.set_sensitive(sensitive)
		
		if cbCancelWith:
			sensitive = True
			if cbMenuAutoCancel and cbMenuAutoCancel.get_active():
				sensitive = False
			cbCancelWith.set_sensitive(sensitive)
		
		name = self.get_selected_menu()
		if name == "":
			# 'New menu' selected
			self.load_menu_list()
			log.debug("Creating editor for new menu")
			me = MenuEditor(self.app, self.on_menu_changed)
			me.set_new_menu()
			me.allow_menus(self.allow_globals, self.allow_in_profile)
			me.show(self.editor.window)
			return
		if name:
			# There is some menu choosen
			self.builder.get_object("btEditMenu").set_sensitive(name not in MenuEditor.OPEN)
			params = [ name, self.get_control_with() ]
			if cbConfirmWith:
				if self.confirm_with_same_active():
					params += [ SAME ]
				else:
					params += [ getattr(SCButtons, cbConfirmWith.get_model().get_value(cbConfirmWith.get_active_iter(), 1)) ]
			if cbCancelWith:
				params += [ getattr(SCButtons, cbCancelWith.get_model().get_value(cbCancelWith.get_active_iter(), 1)) ]
			elif self.confirm_with_same_active():
				params += [ STICK, SAME ]
			
			cbm = self.builder.get_object("cbMenuType")
			# Hide / apply and display 'Items per row' selector if it exists in UI
			if self.builder.get_object("rvMaxSize"):
				rvMaxSize = self.builder.get_object("rvMaxSize")
				spMaxSize = self.builder.get_object("spMaxSize")
				visible = cbm.get_model().get_value(cbm.get_active_iter(), 1) == "gridmenu"
				rvMaxSize.set_reveal_child(visible)
				if visible:
					max_size = int(spMaxSize.get_adjustment().get_value())
					if max_size > 0:
						# max_size is 2nd parameter
						params = [ params[0], max_size ] + params[1:]
			
			# Grab menu type and choose apropriate action
			action = NoAction()
			if cbm and cbm.get_model().get_value(cbm.get_active_iter(), 1) == "gridmenu":
				# Grid menu
				action = GridMenuAction(*params)
			elif cbm and cbm.get_model().get_value(cbm.get_active_iter(), 1) == "radialmenu":
				# Circular menu
				action = RadialMenuAction(*params)
			elif cbm and cbm.get_model().get_value(cbm.get_active_iter(), 1) == "hmenu":
				# Horizontal menu
				action = HorizontalMenuAction(*params)
			else:
				# Normal menu
				action = MenuAction(*params)
			
			# Apply Menu Position options, if such block exists in UI
			if self.builder.get_object("spMenuPosX"):
				cbMenuPosX = self.builder.get_object("cbMenuPosX")
				cbMenuPosY = self.builder.get_object("cbMenuPosY")
				x = int(self.builder.get_object("spMenuPosX").get_value())
				y = int(self.builder.get_object("spMenuPosY").get_value())
				x *= cbMenuPosX.get_model().get_value(cbMenuPosX.get_active_iter(), 0)
				y *= cbMenuPosY.get_model().get_value(cbMenuPosY.get_active_iter(), 0)
				if (x, y) != MenuAction.DEFAULT_POSITION:
					action = PositionModifier(x, y, action)
			
			self.editor.set_action(action)
	
	
	def get_control_with(self):
		""" Returns value of "Control With" combo or STICK if there is none """
		cbControlWith = self.builder.get_object("cbControlWith")
		if cbControlWith:
			return cbControlWith.get_model().get_value(cbControlWith.get_active_iter(), 1)
		return STICK
	
	
	def on_spMaxSize_format_value(self, spinner):
		val = int(spinner.get_adjustment().get_value())
		if val < 1:
			spinner.get_buffer().set_text(_("auto"), -1)
		else:
			spinner.get_buffer().set_text(str(val), -1)
		return True
