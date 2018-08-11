#!/usr/bin/env python2
"""
SC-Controller - Profile Manager

Simple class that manages stuff related to creating, loading, listing (...) of
user-editable data - that are profiles, menus and controller-icons.

Main App class interits from this.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gio, GLib
from scc.paths import get_menuicons_path, get_default_menuicons_path
from scc.paths import get_profiles_path, get_default_profiles_path
from scc.paths import get_menus_path, get_default_menus_path
from scc.profile import Profile
from scc.gui.parser import GuiActionParser

import os, logging
log = logging.getLogger("UDataManager")

class UserDataManager(object):
	
	def __init__(self):
		profiles_path = get_profiles_path()
		if not os.path.exists(profiles_path):
			log.info("Creting profile directory '%s'" % (profiles_path,))
			os.makedirs(profiles_path)
		menus_path = get_menus_path()
		if not os.path.exists(menus_path):
			log.info("Creting menu directory '%s'" % (menus_path,))
			os.makedirs(menus_path)
	
	
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
	
	
	def load_profile_list(self, category=None):
		paths = [ get_default_profiles_path(), get_profiles_path() ]
		self.load_user_data(paths, "*.sccprofile", category, self.on_profiles_loaded)
	
	
	def load_menu_list(self, category=None):
		paths = [ get_default_menus_path(), get_menus_path() ]
		self.load_user_data(paths, "*.menu", category, self.on_menus_loaded)
	
	
	def load_menu_icons(self, category=None):
		paths = [ get_default_menuicons_path(), get_menuicons_path() ]
		self.load_user_data(paths, "*.png", category, self.on_menuicons_loaded)
	
	
	def load_user_data(self, paths, pattern, category, callback):
		"""
		Loads data such as of profiles. Uses GLib to do it on background.
		"""
		if category:
			paths = [ os.path.join(p, category) for p in paths ]
		
		# First list is for default stuff, then for user-defined
		# Number is increased when list is loaded until it reaches 2
		data = [ None ] * len(paths)
		
		for i in xrange(0, len(paths)):
			f = Gio.File.new_for_path(paths[i])
			f.enumerate_children_async(
				pattern,
				Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
				1, None, self._on_user_data_loaded,
				data, i, callback
			)
	
	
	def _on_user_data_loaded(self, pdir, res, data, i, callback):
		"""
		Called when enumerate_children_async gets lists of files.
		Usually called twice for default (system) and user directory.
		"""
		try:
			data[i] = pdir, pdir.enumerate_children_finish(res)
		except Exception, e:
			# Usually when directory doesn't exists
			log.warning("enumerate_children_finish for %s failed: %s",  pdir.get_path(), e)
			data[i] = None, []
		if not None in data:
			files = {}
			try:
				for pdir, enumerator in data:
					if pdir is not None:
						for finfo in enumerator:
							name = finfo.get_name()
							if name:
								files[name] = pdir.get_child(name)
			except Exception, e:
				# https://github.com/kozec/sc-controller/issues/50
				log.warning("enumerate_children_async failed: %s", e)
				files = self._sync_load([ pdir for pdir, enumerator in data
											if pdir is not None])
			if len(files) < 1:
				# https://github.com/kozec/sc-controller/issues/327
				log.warning("enumerate_children_async returned no files")
				files = self._sync_load([ pdir for pdir, enumerator in data
											if pdir is not None])
			
			callback(files.values())
	
	
	def _sync_load(self, pdirs):
		"""
		Synchronous (= UI lagging) fallback method for those (hopefully) rare
		cases when enumerate_children_finish returns nonsense.
		"""
		files = {}
		for pdir in pdirs:
			for name in os.listdir(pdir.get_path()):
				files[name] = pdir.get_child(name)
		return files
	
	
	def on_menus_loaded(self, menus): # Overriden by subclass
		pass
	
	
	def on_profiles_loaded(self, profiles): # Overriden by subclass
		pass
	
	
	def on_menuicons_loaded(self, icons): # Overriden by subclass
		pass
	
	
	def on_profile_saved(self, giofile): # Overriden in App
		pass
	
	
	def on_profile_loaded(self, profile, giofile): # Overriden in App
		pass
