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
from scc.tools import get_profiles_path


import sys, os, logging
log = logging.getLogger("ExportDialog")

class ExportDialog(Editor, UserDataManager, ComboSetter):
	GLADE = "export_dialog.glade"
	
	def __init__(self, app):
		self.app = app
		self.setup_widgets()
		self._current = None
	
	
	def on_prepare(self, trash, child):
		tvProfiles = self.builder.get_object("tvProfiles")
		if child == self.builder.get_object("grSelectProfile"):
			self.load_profile_list()
	
	
	def on_profiles_loaded(self, lst):
		tvProfiles = self.builder.get_object("tvProfiles")
		model = tvProfiles.get_model()
		i, current_index = 0, 0
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
	
	
	def on_tvProfiles_cursor_changed(self, *a):
		"""
		Called when user selects profile.
		"""
		tvProfiles = self.builder.get_object("tvProfiles")
		self.window.set_page_complete(
			self.window.get_nth_page(self.window.get_current_page()),
			True
		)
	
	
	def on_cancel(self, *a):
		self.window.destroy()
	
	
	def on_apply(self, *a):
		print "on_apply"
