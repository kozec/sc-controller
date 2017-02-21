#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gdk, GObject, GLib, Gio
from scc.gui.userdata_manager import UserDataManager
from scc.gui.editor import Editor, ComboSetter
from scc.special_actions import ChangeProfileAction, MenuAction
from scc.tools import get_profiles_path, find_profile, find_menu
from scc.tools import profile_is_default, menu_is_default
from scc.menu_data import MenuData, Submenu
from scc.parser import ActionParser
from scc.profile import Profile


import sys, os, json, logging
log = logging.getLogger("ExportDialog")

class ExportDialog(Editor, UserDataManager, ComboSetter):
	GLADE = "export_dialog.glade"
	PAGE_PROFILE = 0
	PAGE_PACKAGE = 1
	
	def __init__(self, app, preselected):
		self.app = app
		self._current = preselected
		self.setup_widgets()
		self.load_profile_list()
	
	
	
	def on_profiles_loaded(self, lst):
		tvProfiles = self.builder.get_object("tvProfiles")
		model = tvProfiles.get_model()
		i, current_index = 0, -1
		for f in sorted(lst, key=lambda f: f.get_basename()):
			name = f.get_basename()
			if name.endswith(".mod"):
				continue
			if name.startswith("."):
				continue
			if name.endswith(".sccprofile"):
				name = name[0:-11]
			if name == self._current:
				current_index = i
			model.append((i, f, name))
			i += 1
		if current_index >= 0:
			tvProfiles.set_cursor((current_index,))
	
	
	def _add_refereced_profile(self, model, giofile, used):
		"""
		Loads profile file and recursively adds all profiles and menus
		referenced by it into 'package' list.
		
		Returns True on success or False if something cannot be parsed.
		"""
		# Load & parse selected profile and check every action in it
		profile = Profile(ActionParser())
		try:
			profile.load(giofile.get_path())
		except Exception, e:
			# Profile that cannot be parsed shouldn't be exported
			log.error(e)
			return False
		
		for action in profile.get_actions():
			self._parse_action(model, action, used)
		
		for menu in profile.menus:
			for item in profile.menus[menu]:
				if isinstance(item, Submenu):
					self._add_refereced_menu(model, os.path.split(item.filename)[-1], used)
				if hasattr(item, "action"):
					self._parse_action(model, item.action, used)
		return True
	
	
	def _add_refereced_menu(self, model, menu_id, used):
		"""
		As _add_refereced_profile, but reads and parses menu file.
		"""
		if "." in menu_id and menu_id not in used:
			# Dot in id means filename
			used.add(menu_id)
			filename = find_menu(menu_id)
			name = ".".join(menu_id.split(".")[0:-1])
			if name.startswith(".") and menu_is_default(menu_id):
				# Default and hidden, don't bother user with it
				return
			if filename:
				model.append((not menu_is_default(menu_id), _("Menu"), name, filename, True))
				try:
					data = json.loads(open(filename, "r").read())
					menu = MenuData.from_json_data(data, ActionParser())
				except Exception, e:
					# Menu that cannot be parsed shouldn't be exported
					log.error(e)
					return
				for item in menu:
					if isinstance(item, Submenu):
						self._add_refereced_menu(model, os.path.split(item.filename)[-1], used)
					if hasattr(item, "action"):
						self._parse_action(model, item.action, used)
			else:
				model.append((False, _("Menu"), _("%s (not found)") % (name,), "", False))
	
	
	def _parse_action(self, model, action, used):
		"""
		Common part of _add_refereced_profile and _add_refereced_menu
		"""
		if isinstance(action, ChangeProfileAction):
			if action.profile not in used:
				filename = find_profile(action.profile)
				used.add(action.profile)
				if filename:
					model.append((not profile_is_default(action.profile),
						_("Profile"), action.profile, filename, True))
					self._add_refereced_profile(model,
						Gio.File.new_for_path(filename), used)
				else:
					model.append((False, _("Profile"),
						_("%s (not found)") % (action.profile,), "", False))
		elif isinstance(action, MenuAction):
			self._add_refereced_menu(model, action.menu_id, used)
	
	
	def on_tvProfiles_cursor_changed(self, *a):
		"""
		Called when user selects profile.
		"""
		tvProfiles	= self.builder.get_object("tvProfiles")
		tvPackage	= self.builder.get_object("tvPackage")
		btSaveAs	= self.builder.get_object("btSaveAs")
		btClose		= self.builder.get_object("btClose")
		btNext		= self.builder.get_object("btNext")
		
		package = tvPackage.get_model()
		package.clear()
		used = set()
		
		model, iter = tvProfiles.get_selection().get_selected()
		giofile = model[iter][1]
		s = self._add_refereced_profile(package, giofile, used)
		needs_package = any([ row[0] for row in package ])
		if needs_package:
			# Profile references other menus or profiles
			btNext.set_visible(True)
			btSaveAs.set_visible(False)
		else:
			# Profile can be exported directly
			btNext.set_visible(False)
			btSaveAs.set_visible(True)
	
	
	def on_btNext_clicked(self, *a):
		btBack			= self.builder.get_object("btBack")
		btNext			= self.builder.get_object("btNext")
		stDialog		= self.builder.get_object("stDialog")
		btSaveAs		= self.builder.get_object("btSaveAs")
		grMakePackage	= self.builder.get_object("grMakePackage")
		stDialog.set_visible_child(grMakePackage)
		btNext.set_visible(False)
		btBack.set_visible(True)
		btSaveAs.set_visible(True)
	
	
	def on_btBack_clicked(self, *a):
		btBack			= self.builder.get_object("btBack")
		stDialog		= self.builder.get_object("stDialog")
		btSaveAs		= self.builder.get_object("btSaveAs")
		grSelectProfile	= self.builder.get_object("grSelectProfile")
		stDialog.set_visible_child(grSelectProfile)
		btBack.set_visible(False)
		btSaveAs.set_visible(False)
		self.on_tvProfiles_cursor_changed()	# To update Next/Save As button
	
	
	def on_btSelectAll_clicked(self, *a):
		tvPackage = self.builder.get_object("tvPackage")
		package = tvPackage.get_model()
		for row in package:
			if row[4]:	# if enabled
				row[0] = True	# then selected
	
	
	def on_crPackageCheckbox_toggled(self, cr, path):
		tvPackage = self.builder.get_object("tvPackage")
		package = tvPackage.get_model()
		package[path][0] = not package[path][0]
