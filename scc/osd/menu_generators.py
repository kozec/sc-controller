#!/usr/bin/env python2
"""
SC-Controller - OSD Menu Generators

Auto-generated menus with stuff like list of all available profiles...
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from scc.menu_data import MenuGenerator, MenuItem, MENU_GENERATORS
from scc.paths import get_profiles_path, get_default_profiles_path
from scc.tools import find_profile
from scc.config import Config

import os, sys, json, logging
log = logging.getLogger("osd.menu_gen")

class ProfileListMenuGenerator(MenuGenerator):
	""" Generates list of all available profiles """
	GENERATOR_NAME = "profiles"
	
	@staticmethod
	def callback(menu, daemon, menuitem):
		daemon.set_profile(menuitem.filename)
		menu.hide()
		def on_response(*a):
			menu.quit(-2)
		daemon.request(b"OSD: " + menuitem.label.encode("utf-8") + b"\n",
			on_response, on_response)
	
	def generate(self, menuhandler):
		# TODO: Cannot load directory content asynchronously here and I'm
		# TODO: not happy about it
		rv, all_profiles = [], {}
		for d in (get_default_profiles_path(), get_profiles_path()):
			for x in os.listdir(d):
				if x.endswith(".sccprofile") and not x.startswith("."):
					all_profiles[x] = os.path.join(d, x)
		for p in sorted(all_profiles, key=lambda s: s.lower()):
			menuitem = MenuItem("generated", p[0:-11])	# strips ".sccprofile"
			menuitem.filename = all_profiles[p]
			menuitem.callback = self.callback
			rv.append(menuitem)
		return rv


class RecentListMenuGenerator(MenuGenerator):
	""" Generates list of X recently used profiles """
	GENERATOR_NAME = "recent"
	
	def __init__(self, rows=5, **b):
		self.rows = rows
	
	
	def generate(self, menuhandler):
		rv = []
		for p in Config()['recent_profiles']:
			filename = find_profile(p)
			if filename:
				menuitem = MenuItem("generated", p)
				menuitem.filename = filename
				menuitem.callback = ProfileListMenuGenerator.callback
				rv.append(menuitem)
			if len(rv) >= self.rows:
				break
		return rv


# Add classes to MENU_GENERATORS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'GENERATOR_NAME') ]:
	if i.GENERATOR_NAME is not None:
		MENU_GENERATORS[i.GENERATOR_NAME] = i
