#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gdk, GObject, GLib
from scc.gui.userdata_manager import UserDataManager
from scc.gui.editor import Editor, ComboSetter
from scc.tools import get_profiles_path, find_profile, find_menu
from scc.tools import profile_is_default, menu_is_default
from scc.special_actions import ChangeProfileAction, MenuAction
from scc.parser import ActionParser
from scc.profile import Profile


import sys, os, logging
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
	
	
	def on_tvProfiles_cursor_changed(self, *a):
		"""
		Called when user selects profile.
		"""
		tvProfiles = self.builder.get_object("tvProfiles")
		tvPackage = self.builder.get_object("tvPackage")
		page = self.window.get_nth_page(self.window.get_current_page())
		model, iter = tvProfiles.get_selection().get_selected()
		giofile = model[iter][1]
		
		# Load & parse selected profile and check every action in it
		profile = Profile(ActionParser())
		try:
			profile.load(giofile.get_path())
		except Exception, e:
			# Profile that cannot be parsed shouldn't be exported
			self.window.set_page_complete(page, False)
			log.error(e)
			return
		
		package = tvPackage.get_model()
		package.clear()
		used = set()
		for a in profile.get_actions():
			# TODO: Probably recursively scan referenced profiles as well?
			if isinstance(a, ChangeProfileAction):
				if a.profile not in used:
					filename = find_profile(a.profile)
					used.add(a.profile)
					if filename:
						package.append((not profile_is_default(a.profile),
							_("Profile"), a.profile, filename, True))
					else:
						package.append((False, _("Profile"),
							_("%s (not found)") % (a.profile,), "", False))
			elif isinstance(a, MenuAction):
				if "." in a.menu_id:
					# Dot in id means filename
					if a.menu_id not in used:
						filename = find_menu(a.menu_id)
						used.add(a.menu_id)
						if filename:
							package.append((not menu_is_default(a.menu_id),
								_("Menu"), a.menu_id.split(".")[0], filename, True))
						else:
							package.append((False, _("Menu"), _("%s (not found)") % (a.menu_id.split(".")[0],), "", False))
					
		
		self.window.set_page_complete(page, True)
		
	
	
	def on_cancel(self, *a):
		self.window.destroy()
	
	
	def on_apply(self, *a):
		print "on_apply"
