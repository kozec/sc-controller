#!/usr/bin/env python2
"""
SC-Controller - OSD Menu Generators

Auto-generated menus with stuff like list of all available profiles...
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gdk, GdkX11
from scc.menu_data import MenuGenerator, MenuItem, Separator, MENU_GENERATORS
from scc.paths import get_profiles_path, get_default_profiles_path
from scc.x11.autoswitcher import AutoSwitcher
from scc.lib import xwrappers as X
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


class RecentListMenuGenerator(MenuGenerator):
	""" Generates list of X recently used profiles """
	GENERATOR_NAME = "recent"
	
	def __init__(self, rows=5, **b):
		self.rows = rows
	
	
	def generate(self):
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


class AutoswitchOptsMenuGenerator(MenuGenerator):
	""" Generates entire Autoswich Options submenu """
	GENERATOR_NAME = "autoswitch"
	
	def callback(self, menu, daemon, menuitem):
		print "callback", menuitem
	
	
	def generate(self):
		rv = []
		dpy = X.Display(hash(GdkX11.x11_get_default_xdisplay()))	# Magic
		win = X.get_current_window(dpy)
		if not win:
			# Bail out if active window cannot be determined
			rv.append(self.mk_item(None, _("No active window")))
			rv.append(self.mk_item("as::close", _("Close")))
			return rv
		
		title = X.get_window_title(dpy, win)
		wm_class = X.get_window_class(dpy, win)
		assigned_prof = None
		conds = AutoSwitcher.parse_conditions(Config())
		for c in conds:
			if c.matches(title, wm_class):
				assigned_prof = conds[c]
				break
		if win:
			display_title = title or _("No Title")
			rv.append(self.mk_item(None, _("Current Window: %s") % (title[0:25],)))
			if assigned_prof:
				rv.append(self.mk_item(None, _("Assigned Profile: %s") % (assigned_prof,)))
			rv.append(Separator())
			rv.append(Separator())
			rv.append(Separator())
			rv.append(self.mk_item("as::assign", _("Assign Current Profile")))
			if assigned_prof:
				rv.append(self.mk_item("as::unassign", _("Unassign Assigned")))
		return rv
	
	
	def mk_item(self, id, title):
		""" Creates menu item and assigns callback """
		menuitem = MenuItem(id, title)
		menuitem.callback = self.callback
		return menuitem


# Add classes to MENU_GENERATORS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'GENERATOR_NAME') ]:
	if i.GENERATOR_NAME is not None:
		MENU_GENERATORS[i.GENERATOR_NAME] = i
