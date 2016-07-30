#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gdk, GObject, GLib
from scc.gui.editor import Editor, ComboSetter
from scc.lib.vdf import parse_vdf
from scc.foreign.vdf import VDFProfile
from cStringIO import StringIO

import re, sys, os, collections, threading, logging
log = logging.getLogger("ImportDialog")

class ImportDialog(Editor, ComboSetter):
	GLADE = "import_dialog.glade"
	PROFILE_LIST = "7/remote/sharedconfig.vdf"
	STEAMPATH = '~/.steam/steam/'
	
	def __init__(self, app):
		self.app = app
		self.setup_widgets()
		self.profile = None
		self.lstProfiles = self.builder.get_object("tvProfiles").get_model()
		self.q_games    = collections.deque()
		self.q_profiles = collections.deque()
		self.s_games    = threading.Semaphore(0)
		self.s_profiles = threading.Semaphore(0)
		threading.Thread(target=self._load_profiles).start()
		threading.Thread(target=self._load_game_names).start()
		threading.Thread(target=self._load_profile_names).start()
	
	
	def _load_profiles(self):
		"""
		Search for file containign list of profiles and reads it.
		
		This is done in thread, with crazy hope that it will NOT crash GTK
		in the process.
		"""
		p = os.path.join(os.path.expanduser(ImportDialog.STEAMPATH), "userdata")
		i = 0
		if os.path.exists(p):
			for user in os.listdir(p):
				sharedconfig = os.path.join(p, user, ImportDialog.PROFILE_LIST)
				if os.path.isfile(sharedconfig):
					log.debug("Loading sharedconfig from '%s'", sharedconfig)
					try:
						i = self._parse_profile_list(i, sharedconfig)
					except Exception, e:
						log.exception(e)
		
		GLib.idle_add(self._load_finished)
	
	
	def _parse_profile_list(self, i, filename):
		"""
		Parses sharedconfig.vdf and loads game and profile IDs. That is later
		decoded into name of game and profile name.
		
		Called from _load_profiles, in thread. Exceptions are catched and logged
		from there.
		Calls GLib.idle_add to send loaded data into UI.
		"""
		data = parse_vdf(open(filename, "r"))
		cc = data["userroamingconfigstore"]["controller_config"]
		listitems = []
		for gameid in cc:
			if "selected" in cc[gameid] and cc[gameid]["selected"].startswith("workshop"):
				profile_id = cc[gameid]["selected"].split("/")[-1]
				listitems.append(( i, gameid, profile_id, None ))
				i += 1
				if len(listitems) > 10:
					GLib.idle_add(self.fill_list, listitems)
					listitems = []
		
		GLib.idle_add(self.fill_list, listitems)
		return i
	
	
	def _load_game_names(self):
		"""
		Loads names for game ids in q_games.
		
		This is done in thread (not in same thread as _load_profiles),
		because it involves searching for apropriate file and parsing it
		entirely.
		
		Calls GLib.idle_add to send loaded data into UI.
		"""
		sa_path = self._find_steamapps()
		while True:
			self.s_games.acquire(True)	# Wait until something is added to the queue
			try:
				index, gameid = self.q_games.popleft()
			except IndexError:
				break
			if gameid.isdigit():
				name = _("Unknown App ID %s") % (gameid)
				filename = os.path.join(sa_path, "appmanifest_%s.acf" % (gameid,))
				if os.path.exists(filename):
					try:
						data = parse_vdf(open(filename, "r"))
						name = data['appstate']['name']
					except Exception, e:
						log.error("Failed to load app manifest for '%s'", gameid)
						log.exception(e)
				else:
					log.warning("Skiping non-existing app manifest '%s'", filename)
			else:
				name = gameid
			GLib.idle_add(self._set_game_name, index, name)
	
	
	def _load_profile_names(self):
		"""
		Loads names for profiles ids in q_profiles.
		
		This is same as _load_game_names, but for profiles.
		"""
		content_path = os.path.join(self._find_steamapps(), "workshop/content")
		if not os.path.exists(content_path):
			log.warning("Cannot find '%s'; Cannot import anything without it", content_path)
			return
		while True:
			self.s_profiles.acquire(True)	# Wait until something is added to the queue
			try:
				index, gameid, profile_id = self.q_profiles.popleft()
			except IndexError:
				break
			for user in os.listdir(content_path):
				filename = os.path.join(content_path, user, profile_id, "controller_configuration.vdf")
				if os.path.exists(filename):
					log.warning("Reading '%s'", filename)
					try:
						data = parse_vdf(open(filename, "r"))
						name = data['controller_mappings']['title']
						GLib.idle_add(self._set_profile_name, index, name, filename)
						break
					except Exception, e:
						log.error("Failed to read profile name from '%s'", filename)
						log.exception(e)
			else:
				name = _("(not found)")
				GLib.idle_add(self._set_profile_name, index, name, None)
	
	
	def _load_finished(self):
		""" Called in main thread after _load_profiles is finished """
		self.builder.get_object("rvLoading").set_reveal_child(False)
		self.loading = False
		self.s_games.release()
		self.s_profiles.release()
	
	
	def _find_steamapps(self):
		"""
		Returns path to SteamApps folder or None if it cannot be found.
		This is done because Steam apparently supports both SteamApps and
		steamapps as name for this folder.
		"""
		for x in ("SteamApps", "steamapps", "Steamapps", "steamApps"):
			path = os.path.join(os.path.expanduser(ImportDialog.STEAMPATH), x)
			if os.path.exists(path):
				return path
		log.warning("Cannot find SteamApps directory")
		return None
	
	
	def _set_game_name(self, index, name):
		self.lstProfiles[index][1] = name
	
	def _set_profile_name(self, index, name, filename):
		self.lstProfiles[index][2] = name
		self.lstProfiles[index][3] = filename
	
	
	def fill_list(self, items):
		"""
		Adds items to profile list. Has to run in main thread, 
		otherwise, GTK will crash.
		"""
		for i in items:
			self.lstProfiles.append(i)
			self.q_games.append(( i[0], i[1] ))
			self.s_games.release()
			self.q_profiles.append(( i[0], i[1], i[2] ))
			self.s_profiles.release()
	
	
	def on_tvProfiles_cursor_changed(self, *a):
		"""
		Called when user selects profile.
		Check if file for that profile is known and if yes, enables next page.
		"""
		tvProfiles = self.builder.get_object("tvProfiles")
		model, iter = tvProfiles.get_selection().get_selected()
		filename = model.get_value(iter, 3)
		self.window.set_page_complete(
			self.window.get_nth_page(self.window.get_current_page()),
			filename is not None
		)
	
	
	def on_txName_changed(self, ent):
		"""
		Called when text in profile name field is changed.
		Basically enables 'Save' button if name is not empty string.
		"""
		self.window.set_page_complete(
			self.window.get_nth_page(self.window.get_current_page()),
			len(ent.get_text().strip()) > 0 and "/" not in ent.get_text()
		)
	
	
	def on_prepare(self, trash, child):
		if child == self.builder.get_object("grImportFinished"):
			tvProfiles = self.builder.get_object("tvProfiles")
			lblImportFinished = self.builder.get_object("lblImportFinished")
			lblError = self.builder.get_object("lblError")
			tvError = self.builder.get_object("tvError")
			swError = self.builder.get_object("swError")
			lblName = self.builder.get_object("lblName")
			txName = self.builder.get_object("txName")
			
			model, iter = tvProfiles.get_selection().get_selected()
			filename = model.get_value(iter, 3)
			self.profile = VDFProfile()
			failed = False
			error_log = StringIO()
			handler = logging.StreamHandler(error_log)
			logging.getLogger().addHandler(handler)
			swError.set_visible(False)
			lblError.set_visible(False)
			lblName.set_visible(True)
			txName.set_visible(True)
			
			try:
				self.profile.load(filename)
			except Exception, e:
				log.exception(e)
				lblName.set_visible(False)
				txName.set_visible(False)
				txName.set_text("")
				self.profile = None
				failed = True
			
			logging.getLogger().removeHandler(handler)
			
			if failed:
				swError.set_visible(True)
				lblError.set_visible(True)
				
				lblImportFinished.set_text(_("Import failed"))
				
				error_log.write("\nProfile dump:\n")
				try:
					error_log.write(open(filename, "r").read())
				except Exception, e:
					error_log.write("(failed to write: %s)" % (e,))
				
				tvError.get_buffer().set_text(error_log.getvalue())
			elif len(error_log.getvalue()) > 0:
				# Some warnings were displayed
				swError.set_visible(True)
				lblError.set_visible(True)
				
				lblImportFinished.set_text(_("Profile imported with warnings"))
				
				tvError.get_buffer().set_text(error_log.getvalue())
				txName.set_text(self.profile.name)

			else:
				lblImportFinished.set_text(_("Profile sucessfully imported"))
				txName.set_text(self.profile.name)
	
	
	def on_cancel(self, *a):
		self.window.destroy()
	
	
	def on_apply(self, *a):
		txName = self.builder.get_object("txName")
		self.app.new_profile(self.profile, txName.get_text())
		GLib.idle_add(self.window.destroy)
