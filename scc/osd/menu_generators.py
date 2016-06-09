#!/usr/bin/env python2
"""
SC-Controller - OSD Menu Generators

Auto-generated menus with stuff like list of all available profiles...
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from scc.menu_data import MenuGenerator, MenuItem, MENU_GENERATORS

import os, sys, json, logging
log = logging.getLogger("osd.menu_gen")

class ProfileListMenuGenerator(MenuGenerator):
	GENERATOR_NAME = "profiles"
	
	def generate(self):
		return [
			MenuItem("profile:One",		"Profile: Desktop"),
			MenuItem("profile:Two",		"Profile: XBox Controller"),
			MenuItem("profile:Three",	"Profile: Whatever")
		]


# Add classes to MENU_GENERATORS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'GENERATOR_NAME') ]:
	if i.GENERATOR_NAME is not None:
		MENU_GENERATORS[i.GENERATOR_NAME] = i
