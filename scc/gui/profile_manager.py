#!/usr/bin/env python2
"""
SC-Controller - Profile Manager

Simple class that manages stuff related to creating, loading, listing (...) profiles.
Main App class interits from this.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gio, GLib
from scc.paths import get_profiles_path, get_default_profiles_path
from scc.profile import Profile
from scc.gui.parser import GuiActionParser

import os, logging
log = logging.getLogger("ProfileManager")

class ProfileManager(object):
	
	def __init__(self):
		path = get_profiles_path()
		if not os.path.exists(path):
			log.info("Creting profile directory '%s'" % (path,))
			os.makedirs(path)
	
	
	def load_profile(self, giofile):
		"""
		Loads profile from 'giofile' into 'profile' object
		Calls on_profiles_loaded when done
		"""
		# This may get asynchronous later, but that load runs under 1ms...
		profile = Profile(GuiActionParser())
		profile.load(giofile.get_path())
		self.on_profile_loaded(profile, giofile)
	
	
	def save_profile(self, giofile, profile):
		"""
		Saves profile from 'profile' object into 'giofile'.
		Calls on_profile_saved when done
		"""
		# 1st check, if file is not in /usr/share.
		# When user tries to save over built-in profile in /usr/share,
		# new file with same name is created in ~/.config/scc/profiles and profile
		# is shaved into it.
		
		if giofile.get_path().startswith(get_default_profiles_path()):
			return self._save_profile_local(giofile, profile)
		
		profile.save(giofile.get_path())
		self.on_profile_saved(giofile)
	
	def _save_profile_local(self, giofile, profile):
		filename = os.path.split(giofile.get_path())[-1]
		localpath = os.path.join(get_profiles_path(), filename)
		giofile = Gio.File.new_for_path(localpath)
		self.save_profile(giofile, profile)
	
	
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
	
	
	def on_profiles_loaded(self, profiles): # Overrided in App
		pass
	
	
	def on_profile_saved(self, giofile): # Overrided in App
		pass
	
	
	def on_profile_loaded(self, profile, giofile): # Overrided in App
		pass
