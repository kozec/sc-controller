#!/usr/bin/env python2
"""
SC-Controller - Profile Manager

Simple class that manages stuff related to creating, loading, listing (...) profiles.
Main App class interits from this.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gio, GLib
from scc.gui.paths import get_profiles_path, get_default_profiles_path

import os, logging
log = logging.getLogger("ProfileManager")

class ProfileManager(object):
	
	def __init__(self):
		path = get_profiles_path()
		print path
		if not os.path.exists(path):
			log.info("Creting profile directory '%s'" % (path,))
			os.makedirs(path)
	
	
	def load_profile_list(self):
		""" Loads lists of profiles. Uses GLib to do it on background. """
		# First list is for default profiles, 2nd for user profiles
		# Number is increased when list is loaded until it reaches 2
		data = [ None, None ]
		paths = [ get_default_profiles_path(), get_profiles_path() ]
		
		for i in (0, 1):
			f = Gio.File.new_for_path(paths[i])
			f.enumerate_children_async(
				"*.sccprofile",
				Gio.FileQueryInfoFlags.NONE,
				1, None,
				self._on_profile_list_loaded,
				data, i
			)
	
	
	def _on_profile_list_loaded(self, pdir, res, data, i):
		"""
		Called when enumerate_children_async gets lists of profiles.
		Called twice for default and user profiles dirs.
		"""
		data[i] = pdir, pdir.enumerate_children_finish(res)
		if not None in data:
			profiles = []
			by_name = {}	# Used to remove overrided file
			for pdir, enumerator in data:
				for finfo in enumerator:
					f = pdir.get_child(finfo.get_name())
					if finfo.get_name() in by_name:
						profiles.remove(by_name[finfo.get_name()])
					by_name[finfo.get_name()] = f
					profiles.append(f)
			
			self.on_profiles_loaded(profiles)
	
	
	def on_profiles_loaded(self, profiles):
		# Overrided in App
		pass
