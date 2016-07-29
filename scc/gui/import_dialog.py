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

import re, sys, os, collections, threading, logging
log = logging.getLogger("ImportDialog")

class ImportDialog(Editor, ComboSetter):
	GLADE = "import_dialog.glade"
	PROFILE_LIST = "7/remote/sharedconfig.vdf"
	STEAMPATH = '~/.steam/steam/'
	
	def __init__(self, app):
		self.app = app
		self.setup_widgets()
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
				listitems.append(( i, gameid, profile_id, profile_id ))
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
			filename = os.path.join(sa_path, "appminifest_%s.acf" % (gameid,))
			if os.path.exists(filename):
				try:
					data = parse_vdf(open(filename, "r"))
					GLib.idle_add(self._set_game_name, index, data['appstate']['name'])
				except Exception, e:
					log.error("Failed to load app manifest for '%s'", gameid)
					log.exception(e)
			else:
				log.warning("Skiping non-existing app manifest for '%s'", gameid)
	
	
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
				filename = os.path.join(content_path, user, gameid, "controller_configuration.vdf")
				if os.path.exists(filename):
					try:
						data = parse_vdf(open(filename, "r"))
						GLib.idle_add(self._set_profile_name, index, data['controller_mappings']['title'])
					except Exception, e:
						log.error("Failed to read profile name from '%s'", filename)
						log.exception(e)
				else:
					log.warning("Skiping non-existing profile '%s'", filename)
	
	
	def _load_finished(self):
		""" Called in main thread after _load_profiles is finished """
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
	
	def _set_profile_name(self, index, name):
		self.lstProfiles[index][2] = name
	
	
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
