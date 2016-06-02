#!/usr/bin/env python2
"""
SC-Controller - Action Editor - common part of "DPAD or menu" and "Special Action",
two components with MenuAction selectable.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.special_actions import MenuAction, GridMenuAction
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
	
	
	def on_menu_changed(self, new_id):
		self._current_menu = new_id
		self.editor.set_action(MenuAction(new_id))
		self.load_menu_list()
	
	
	def on_btEditMenu_clicked(self, *a):
		name = self._get_selected_menu()
		if name:
			log.debug("Editing %s", name)
			me = MenuEditor(self.app, self.on_menu_changed)
			id = self._get_selected_menu()
			log.debug("Opening editor for menu ID '%s'", id)
			me.set_menu(id)
			me.show(self.editor.window)
	
	
	def on_menus_loaded(self, menus):
		cb = self.builder.get_object("cbMenus")
		cb.set_row_separator_func( lambda model, iter : model.get_value(iter, 1) is None )
		model = cb.get_model()
		model.clear()
		i, current_index = 0, 0
		# Add menus from profile
		for key in sorted(self.app.current.menus):
			model.append((key, key))
			if self._current_menu == key:
				current_index = i
			i += 1
		if i > 0:
			model.append((None, None))	# Separator
			i += 1
		for f in menus:
			key = f.get_basename()
			name = key
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
		self.builder.get_object("btEditMenu").set_sensitive(True)
		self._recursing = False
	
	
	def handles(self, mode, action):
		return isinstance(action, MenuAction)
	
	
	def _get_selected_menu(self):
		cb = self.builder.get_object("cbMenus")
		model = cb.get_model()
		iter = cb.get_active_iter()
		if iter is None:
			# Empty list
			return None
		return model.get_value(iter, 1)
	
	
	def on_cbMenus_changed(self, *a):
		""" Called when user chooses menu in selection combo """
		if self._recursing : return
		name = self._get_selected_menu()
		if name == "":
			# 'New menu' selected
			self.load_menu_list()
			log.debug("Creating editor for new menu")
			me = MenuEditor(self.app, self.on_menu_changed)
			me.set_new_menu()
			me.show(self.editor.window)
			return
		if name:
			cbm = self.builder.get_object("cbMenuType")
			if cbm and cbm.get_model().get_value(cbm.get_active_iter(), 1) == "gridmenu":
				# Grid menu
				self.editor.set_action(GridMenuAction(name))
			else:
				# Normal menu
				self.editor.set_action(MenuAction(name))
