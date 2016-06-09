#!/usr/bin/env python2
"""
SC-Controller - OSD Menu Generators

Auto-generated menus with stuff like list of all available profiles...
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from scc.paths import get_profiles_path, get_default_profiles_path
from scc.menu_data import MenuGenerator, MenuItem, MENU_GENERATORS

import os, sys, json, logging
log = logging.getLogger("osd.menu_gen")

class ProfileListMenuGenerator(MenuGenerator):
	GENERATOR_NAME = "profiles"
	
	def callback(self, menu, daemon, menuitem):
		daemon.set_profile(menuitem.filename)
		menu.hide()
		def on_response(*a):
			menu.quit(-2)
		daemon.request(b"OSD: " + menuitem.label.encode("utf-8") + b"\n",
			on_response, on_response)
	
	def generate(self):
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


# Add classes to MENU_GENERATORS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'GENERATOR_NAME') ]:
	if i.GENERATOR_NAME is not None:
		MENU_GENERATORS[i.GENERATOR_NAME] = i
