#!/usr/bin/env python2
"""
SC-Controller - Menu Editor

Edits .menu files and menus stored in profile.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib, GObject
from scc.gui.action_editor import ActionEditor
from scc.gui.icon_chooser import IconChooser
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
from scc.menu_data import ProfileListMenuGenerator, RecentListMenuGenerator, GameListMenuGenerator
from scc.menu_data import MenuData, MenuItem, Submenu, Separator
from scc.paths import get_menus_path, get_default_menus_path
from scc.parser import TalkingActionParser
from scc.actions import Action, NoAction
from scc.tools import find_icon
from scc.profile import Encoder
import os, traceback, logging, json
log = logging.getLogger("MenuEditor")


class MenuIcon(Gtk.Image):
	def __init__(self, a, b):
		Gtk.Image.__init__(self)
		pass


class MenuEditor(Editor):
	GLADE = "menu_editor.glade"
	TYPE_INTERNAL	= 1
	TYPE_GLOBAL		= 2
	
	
	OPEN = set()	# Set of menus that are being edited.
	
	
	def __init__(self, app, callback):
		self.app = app
		self.next_auto_id = 1
		self.callback = callback
		self.selected_icon = None
		self.original_id = None
		self.original_type = MenuEditor.TYPE_INTERNAL
		Editor.install_error_css()
		self.setup_widgets()
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		lblItemIconName  = self.builder.get_object("lblItemIconName")
		vbChangeItemIcon = self.builder.get_object("vbChangeItemIcon")
		self.window = self.builder.get_object("Dialog")
		self.menu_icon = MenuIcon(None, True)
		vbChangeItemIcon.remove(lblItemIconName)
		vbChangeItemIcon.pack_start(self.menu_icon, False, True, 0)
		vbChangeItemIcon.pack_start(lblItemIconName, True, True, 0)
		self.builder.connect_signals(self)
		headerbar(self.builder.get_object("header"))
	
	
	def allow_menus(self, allow_globals, allow_in_profile):
		"""
		Sets which type of menu should be selectable.
		By default, both are enabled.
		"""
		if not allow_globals:
			self.builder.get_object("rbInProfile").set_active(True)
			self.builder.get_object("rbGlobal").set_sensitive(False)
			self.builder.get_object("rbInProfile").set_sensitive(True)
		elif not allow_in_profile:
			self.builder.get_object("rbGlobal").set_active(True)
			self.builder.get_object("rbGlobal").set_sensitive(True)
			self.builder.get_object("rbInProfile").set_sensitive(False)
		else:
			self.builder.get_object("rbGlobal").set_sensitive(True)
			self.builder.get_object("rbInProfile").set_sensitive(True)
	
	
	def on_action_chosen(self, id, a, mark_changed=True):
		model = self.builder.get_object("tvItems").get_model()
		for i in model:
			item = i[0].item
			if item.id == id:
				if isinstance(item, Separator):
					item.label = a.get_name()
				elif isinstance(item, Submenu):
					i[0].item = item = Submenu(
						a.get_current_page().get_selected_menu(),
						a.get_name())
					item.icon = self.selected_icon
				elif isinstance(item, RecentListMenuGenerator):
					i[0].item = item = RecentListMenuGenerator(
						rows = a.get_current_page().get_row_count())
				elif isinstance(item, MenuItem):
					item.action = a
					item.label = item.action.describe(Action.AC_OSD)
					item.icon = self.selected_icon
				else:
					raise TypeError("Edited %s" % (item.__class__.__name__))
				i[1] = item.describe()
				break
	
	
	def on_btSave_clicked(self, *a):
		""" Handler for Save button """
		self._remove_original()
		if self.builder.get_object("rbInProfile").get_active():
			self._save_to_profile(self.builder.get_object("entName").get_text().decode("utf-8"))
		else:
			self._save_to_file(self.builder.get_object("entName").get_text().decode("utf-8"))
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
		if iter is None:
			btRemoveItem.set_sensitive(False)
			btEdit.set_sensitive(False)
		else:
			btRemoveItem.set_sensitive(True)
			o = model.get_value(iter, 0)
			# if isinstance(o.item, (MenuItem, RecentListMenuGenerator)):
			if isinstance(o.item, MenuItem):
				# TODO: Reenable for RecentListMenuGenerator
				btEdit.set_sensitive(True)
			else:
				btEdit.set_sensitive(False)
	
	
	def btEdit_clicked_cb(self, *a):
		""" Handler for "Edit Item" button """
		tvItems = self.builder.get_object("tvItems")
		model, iter = tvItems.get_selection().get_selected()
		item = model.get_value(iter, 0).item
		self.selected_icon = None
		# Setup editor
		e = ActionEditor(self.app, self.on_action_chosen)
		if isinstance(item, Separator):
			e.set_title(_("Edit Separator"))
			e.hide_editor()
			e.set_menu_item(item, _("Separator Name"))
		elif isinstance(item, Submenu):
			e.set_title(_("Edit Submenu"))
			e.hide_action_str()
			e.hide_clear()
			(e.force_page(e.load_component("menu_only"), True)
				.allow_menus(True, False)
				.set_selected_menu(item.filename))
			e.set_menu_item(item, _("Menu Label"))
			self.selected_icon = item.icon
			self.setup_menu_icon(e)
			self.update_menu_icon()
		elif isinstance(item, MenuItem):
			e = ActionEditor(self.app, self.on_action_chosen)
			e.set_title(_("Edit Menu Action"))
			e.set_input(item.id, item.action, mode = Action.AC_MENU)
			self.selected_icon = item.icon
			self.setup_menu_icon(e)
			self.update_menu_icon()
		elif isinstance(item, RecentListMenuGenerator):
			e.set_title(_("Edit Recent List"))
			e.hide_action_str()
			e.hide_clear()
			e.hide_name()
			(e.force_page(e.load_component("recent_list"), True)
				.set_row_count(item.rows))
			e.set_menu_item(item)
		else:
			# Cannot edit this
			return
		# Display editor
		e.show(self.window)
	
	
	def _add_menuitem(self, item):
		""" Adds MenuItem or MenuGenerator object """
		tvItems = self.builder.get_object("tvItems")
		model = tvItems.get_model()
		o = GObject.GObject()
		if not item.id:
			item.id = "_auto_id_%s" % (self.next_auto_id,)
			self.next_auto_id += 1
		o.item = item
		iter = model.append(( o, o.item.describe() ))
		tvItems.get_selection().select_iter(iter)
		self.on_tvItems_cursor_changed()
	
	
	def on_btAddItem_clicked(self, *a):
		""" Handler for "Add Action" button and menu item """
		item = MenuItem(None, NoAction().describe(Action.AC_OSD), NoAction())
		self._add_menuitem(item)
		self.btEdit_clicked_cb()
	
	
	def on_mnuAddSeparator_clicked(self, *a):
		""" Handler for "Add Separator" menu item """
		self._add_menuitem(Separator())
	
	
	def on_mnuAddSubmenu_clicked(self, *a):
		""" Handler for "Add Separator" menu item """
		self._add_menuitem(Submenu(""))
	
	
	def on_mnuAddProfList_clicked(self, *a):
		""" Handler for "Add List of All Profiles" menu item """
		self._add_menuitem(ProfileListMenuGenerator())
	
	
	def on_mnuAddRecentList_clicked(self, *a):
		""" Handler for "Add List of Recent Profiles" menu item """
		self._add_menuitem(RecentListMenuGenerator())
	
	def on_mnuAddGamesList_activate(self, *a):
		""" Handler for "Add List of Games" menu item """
		self._add_menuitem(GameListMenuGenerator())
	
	
	def on_btRemoveItem_clicked(self, *a):
		""" Handler for "Delete Item" button """
		tvItems = self.builder.get_object("tvItems")
		model, iter = tvItems.get_selection().get_selected()
		if iter is not None:
			model.remove(iter)
		self.on_tvItems_cursor_changed()
		
	
	def on_entName_changed(self, *a):
		id = self.builder.get_object("entName").get_text().decode("utf-8")
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
	
	
	@staticmethod
	def menu_is_global(id):
		return "." in id
	
	
	def set_menu(self, id):
		"""
		Setups editor for menu with specified ID.
		ID may be id of menu in profile or, if it contains ".", filename.
		"""
		self.set_title(_("Menu Editor"))
		rbGlobal = self.builder.get_object("rbGlobal")
		rbInProfile = self.builder.get_object("rbInProfile")
		entName = self.builder.get_object("entName")
		
		MenuEditor.OPEN.add(id)
		if MenuEditor.menu_is_global(id):
			id = id.split(".")[0]
			rbGlobal.set_active(True)
			self.original_type = MenuEditor.TYPE_GLOBAL
			items = self._load_items_from_file(id)
		else:
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
				self._add_menuitem(i)
	
	
	def on_Dialog_delete_event(self, *a):
		try:
			if self.original_type == MenuEditor.TYPE_GLOBAL:
				MenuEditor.OPEN.remove(self.original_id + ".menu")
			else:
				MenuEditor.OPEN.remove(self.original_id)
		except KeyError: pass
		return False
	
	
	def close(self, *a):
		self.on_Dialog_delete_event()
		Editor.close(self)
	
	
	def _load_items_from_file(self, id):
		for p in (get_menus_path(), get_default_menus_path()):
			path = os.path.join(p, "%s.menu" % (id,))
			if os.path.exists(path):
				return MenuData.from_file(path, TalkingActionParser())
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
		self.app.on_profile_modified()
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
	
	
	def setup_menu_icon(self, editor):
		container = self.builder.get_object("menu_icon")
		editor.add_widget(_("Icon"), container)
	
	
	def update_menu_icon(self):
		lblItemIconName = self.builder.get_object("lblItemIconName")
		if self.selected_icon is None:
			lblItemIconName.set_label(_("(no icon)"))
			self.menu_icon.set_visible(False)
		else:
			lblItemIconName.set_label(self.selected_icon)
			"""
			try:
				filename, trash = find_icon(self.selected_icon)
				self.menu_icon.set_filename(filename)
				self.menu_icon.set_visible(True)
			except Exception, e:
				log.error(e)
				log.error(traceback.format_exc())
				self.menu_icon.set_visible(False)
			"""
			self.menu_icon.set_visible(False)
	
	
	def on_icon_choosen(self, name):
		self.selected_icon = name
		self.update_menu_icon()
	
	
	def on_btChangeItemIcon_clicked(self, *a):
		c = IconChooser(self.app, self.on_icon_choosen)
		c.show(self.window)
	
	
	def on_btClearItemIcon_clicked(self, *a):
		self.selected_icon = None
		self.update_menu_icon()

