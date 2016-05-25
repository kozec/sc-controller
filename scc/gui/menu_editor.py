#!/usr/bin/env python2
"""
SC-Controller - Menu Editor

Edits .menu files and menus stored in profile.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib, GObject
from scc.gui.action_editor import ActionEditor
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
from scc.menu_data import MenuData, MenuItem
from scc.actions import Action, NoAction
import os, logging
log = logging.getLogger("MenuEditor")


class MenuEditor(Editor):
	GLADE = "menu_editor.glade"

	def __init__(self, app, callback):
		self.app = app
		self.next_new_item_id = 1
		Editor.install_error_css()
		self.setup_widgets()
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.window = self.builder.get_object("Dialog")
		self.builder.connect_signals(self)
		headerbar(self.builder.get_object("header"))
	
	
	def on_action_chosen(self, id, action):
		model = self.builder.get_object("tvItems").get_model()
		for i in model:
			if i[0].item.id == id:
				i[0].item.action = action
				i[0].item.label = action.describe(Action.AC_OSD)
				i[1] = i[0].item.label
				break
	
	
	def on_btSave_clicked(self, *a):
		""" Handler for Save button """
		if self.builder.get_object("rbInProfile").get_active():
			self.save_to_profile(self.builder.get_object("entName").get_text())
		self.close()
	
	
	def btEdit_clicked_cb(self, *a):
		""" Handler for "Edit Item" button """
		tvItems = self.builder.get_object("tvItems")
		model, iter = tvItems.get_selection().get_selected()
		o = model.get_value(iter, 0)
		e = ActionEditor(self.app, self.on_action_chosen)
		e.hide_macro()
		e.hide_modeshift()
		e.set_title(_("Edit Menu Action"))
		e.set_button(o.item.id, o.item.action)
		e.show(self.window)
	
	
	def on_btAddItem_clicked(self, *a):
		""" Handler for "Add Item" button """
		model = self.builder.get_object("tvItems").get_model()
		id = "newitem_%s" % (self.next_new_item_id,)
		self.next_new_item_id += 1
		o = GObject.GObject()
		o.item = MenuItem(id, NoAction().describe(Action.AC_OSD), NoAction())
		model.append(( o, o.item.label ))
	
	
	def set_menu(self, id):
		"""
		Setups editor for menu with specified ID.
		ID may be id of menu in profile or, if it contains ".", filename.
		"""
		self.set_title(_("Menu Editor"))
		rbGlobal = self.builder.get_object("rbGlobal")
		rbInProfile = self.builder.get_object("rbInProfile")
		entName = self.builder.get_object("entName")
		
		if "." in id:
			rbGlobal.set_active(True)
			entName.set_text("Aa/Sccc/Emas")
			items = []
		else:
			rbInProfile.set_active(True)
			entName.set_text(id)
			items = self.app.current.menus[id]
		
		model = self.builder.get_object("tvItems").get_model()
		model.clear()
		for i in items:
			o = GObject.GObject()
			o.item = i
			model.append(( o, i.label ))
	
	
	def save_to_profile(self, id):
		print self.app.current.menus
		model = self.builder.get_object("tvItems").get_model()
		self.app.current.menus[id] = MenuData(*[ i[0].item for i in model ])
