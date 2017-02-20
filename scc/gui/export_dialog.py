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
	
	def __init__(self, app, preselected):
		self.app = app
		self.setup_widgets()
		self._current = preselected
	
	
	def on_prepare(self, trash, child):
		tvProfiles = self.builder.get_object("tvProfiles")
		if child == self.builder.get_object("grSelectProfile"):
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
		return True
	
	
	def _add_refereced_menu(self, model, giofile, used):
		"""
		As _add_refereced_profile, but reads and parses menu file.
		
		Returns True on success or False if something cannot be parsed.
		"""
		# Load & parse selected profile and check every action in it
		try:
			data = json.loads(open(giofile.get_path(), "r").read())
			menu = MenuData.from_json_data(data, ActionParser())
		except Exception, e:
			# Menu that cannot be parsed shouldn't be exported
			log.error(e)
			return False
		for item in menu:
			if hasattr(item, "action"):
				self._parse_action(model, item.action, used)
	
	
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
			if "." in action.menu_id:
				# Dot in id means filename
				if action.menu_id not in used:
					filename = find_menu(action.menu_id)
					used.add(action.menu_id)
					if filename:
						model.append((not menu_is_default(action.menu_id),
							_("Menu"), action.menu_id.split(".")[0], filename, True))
						self._add_refereced_menu(model,
							Gio.File.new_for_path(filename), used)
					else:
						model.append((False, _("Menu"), _("%s (not found)") % (
							action.menu_id.split(".")[0],), "", False))
	
	
	def on_tvProfiles_cursor_changed(self, *a):
		"""
		Called when user selects profile.
		"""
		tvProfiles = self.builder.get_object("tvProfiles")
		tvPackage = self.builder.get_object("tvPackage")
		page = self.window.get_nth_page(self.window.get_current_page())
		
		package = tvPackage.get_model()
		package.clear()
		used = set()
		
		model, iter = tvProfiles.get_selection().get_selected()
		giofile = model[iter][1]
		s = self._add_refereced_profile(package, giofile, used)
		self.window.set_page_complete(page, s)
		
	
	
	def on_cancel(self, *a):
		self.window.destroy()
	
	
	def on_apply(self, *a):
		print "on_apply"
