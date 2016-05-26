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
from scc.paths import get_menus_path, get_default_menus_path
from scc.menu_data import MenuData, MenuItem
from scc.parser import TalkingActionParser
from scc.actions import Action, NoAction
from scc.profile import Encoder
import os, logging, json
log = logging.getLogger("MenuEditor")


class MenuEditor(Editor):
	GLADE = "menu_editor.glade"
	TYPE_INTERNAL	= 1
	TYPE_GLOBAL		= 2
	

	def __init__(self, app, callback):
		self.app = app
		self.next_new_item_id = 1
		self.callback = callback
		self.original_id = None
		self.original_type = MenuEditor.TYPE_INTERNAL
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
		self._remove_original()
		if self.builder.get_object("rbInProfile").get_active():
			self._save_to_profile(self.builder.get_object("entName").get_text())
		else:
			self._save_to_file(self.builder.get_object("entName").get_text())
		self.close()
	
	
	def on_tvItems_cursor_changed(self, *a):
		"""
		Handles moving cursor in Item List.
		Basically just sets Edit Item and Remove Item buttons sensitivity.
		"""
		tvItems = self.builder.get_object("tvItems")
		btEdit = self.builder.get_object("btEdit")
		btRemoveItem = self.builder.get_object("btRemoveItem")
		
		model, iter = tvItems.get_selection().get_selected()
		btRemoveItem.set_sensitive(iter is not None)
		btEdit.set_sensitive(iter is not None)
	
	
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
		tvItems = self.builder.get_object("tvItems")
		model = tvItems.get_model()
		id = "newitem_%s" % (self.next_new_item_id,)
		self.next_new_item_id += 1
		o = GObject.GObject()
		o.item = MenuItem(id, NoAction().describe(Action.AC_OSD), NoAction())
		iter = model.append(( o, o.item.label ))
		tvItems.get_selection().select_iter(iter)
		self.on_tvItems_cursor_changed()
		self.btEdit_clicked_cb()
	
	
	def on_btRemoveItem_clicked(self, *a):
		""" Handler for "Delete Item" button """
		tvItems = self.builder.get_object("tvItems")
		model, iter = tvItems.get_selection().get_selected()
		if iter is not None:
			model.remove(iter)
		self.on_tvItems_cursor_changed()
		
	
	def on_entName_changed(self, *a):
		id = self.builder.get_object("entName").get_text()
		if len(id.strip()) == 0:
			self._bad_id_no_id()
			return
		if "." in id or "/" in id:
			self._bad_id_chars()
			return
		if self.builder.get_object("rbInProfile").get_active():
			# Menu stored in profile
			if id != self.original_id and id in self.app.current.menus:
				self._bad_id_duplicate()
				return
		else:
			# Menu stored as file
			if id != self.original_id:
				path = os.path.join(get_menus_path(), "%s.menu" % (id,))
				if os.path.exists(path):
					self._bad_id_duplicate()
					return
		self._good_id()
		return
	
	
	def _good_id(self, *a):
		self.builder.get_object("rvInvalidID").set_reveal_child(False)
		self.builder.get_object("btSave").set_sensitive(True)
	
	def _bad_id_no_id(self, *a):
		self.builder.get_object("btSave").set_sensitive(False)
	
	def _bad_id_duplicate(self, *a):
		self.builder.get_object("lblNope").set_label(_('Invalid Menu ID: Menu with same ID already exists.'))
		self.builder.get_object("rvInvalidID").set_reveal_child(True)
		self.builder.get_object("btSave").set_sensitive(False)
	
	def _bad_id_chars(self, *a):
		self.builder.get_object("lblNope").set_label(_('Invalid Menu ID: Please, don\'t use dots (.) or slashes (/).'))
		self.builder.get_object("rvInvalidID").set_reveal_child(True)
		self.builder.get_object("btSave").set_sensitive(False)
	
	
	def set_new_menu(self):
		"""
		Setups editor for creating new menu.
		"""
		self.set_title(_("New Menu"))
		rbInProfile = self.builder.get_object("rbInProfile")
		entName = self.builder.get_object("entName")
		
		rbInProfile.set_active(True)
		self.original_id = None
		self.original_type = MenuEditor.TYPE_INTERNAL
		entName.set_text("")
	
	
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
			id = id.split(".")[0]
			rbGlobal.set_active(True)
			self.original_type = MenuEditor.TYPE_GLOBAL
			items = self._load_items_from_file(id)
		else:
			self.original_id = id
			rbInProfile.set_active(True)
			self.original_type = MenuEditor.TYPE_INTERNAL
			items = self._load_items_from_profile(id)
		self.original_id = id
		entName.set_text(id)
		
		model = self.builder.get_object("tvItems").get_model()
		model.clear()
		if items is None:
			self.set_new_menu()
		else:
			for i in items:
				o = GObject.GObject()
				o.item = i
				model.append(( o, i.label ))
	
	
	def _load_items_from_file(self, id):
		for p in (get_menus_path(), get_default_menus_path()):
			path = os.path.join(p, "%s.menu" % (id,))
			if os.path.exists(path):
				data = json.loads(open(path, "r").read())
				return MenuData.from_json_data(data, TalkingActionParser())
		# Menu file not found
		return None
	
	
	def _load_items_from_profile(self, id):
		try:
			return self.app.current.menus[id]
		except KeyError:
			# Menu not found
			return None
	
	
	def _remove_original(self):
		if self.original_id is None:
			# Created new menu
			pass
		elif self.original_type == MenuEditor.TYPE_INTERNAL:
			try:
				del self.app.current.menus[self.original_id]
			except: pass
		elif self.original_type == MenuEditor.TYPE_GLOBAL:
			try:
				path = os.path.join(get_menus_path(), "%s.menu" % (self.original_id,))
				log.debug("Removing %s", path)
				os.unlink(path)
			except: pass
	
	
	def _generate_menudata(self):
		"""
		Generates MenuData instance from items in list
		"""
		model = self.builder.get_object("tvItems").get_model()
		data = MenuData(*[ i[0].item for i in model ])
		i = 1
		for item in data:
			item.id = "item%s" % (i,)
			i += 1
		return data
		
	
	def _save_to_profile(self, id):
		"""
		Stores menu in loaded profile. Doesn't actually save anything, that's
		for main app window thing.
		"""
		self.app.current.menus[id] = self._generate_menudata()
		log.debug("Stored menu ID %s", id)
		self.app.on_profile_changed()
		if self.callback:
			self.callback(id)
	
	
	def _save_to_file(self, id):
		"""
		Stores menu in json file
		"""
		id = "%s.menu" % (id,)
		path = os.path.join(get_menus_path(), id)
		data = self._generate_menudata()
		jstr = Encoder(sort_keys=True, indent=4).encode(data)
		open(path, "w").write(jstr)
		log.debug("Wrote menu file %s", path)
		if self.callback:
			self.callback(id)
