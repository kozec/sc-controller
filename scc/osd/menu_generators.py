#!/usr/bin/env python3
"""
SC-Controller - OSD Menu Generators

Auto-generated menus with stuff like list of all available profiles...
"""

from scc.tools import _, set_logging_level

from gi.repository import Gdk, Gio, GdkX11
from scc.menu_data import MenuGenerator, MenuItem, MENU_GENERATORS
from scc.paths import get_profiles_path, get_default_profiles_path
from scc.tools import find_profile
from scc.lib import xwrappers as X

from ctypes import POINTER, cast
import os, sys, json, traceback, logging
log = logging.getLogger("osd.menu_gen")


class ProfileListMenuGenerator(MenuGenerator):
	""" Generates list of all available profiles """
	GENERATOR_NAME = "profiles"
	
	@staticmethod
	def callback(menu, daemon, controller, menuitem):
		controller.set_profile(menuitem.filename)
		menu.hide()
		def on_response(*a):
			menu.quit(-2)
		daemon.request(b"OSD: " + menuitem.label.encode("utf-8") + b"\n",
			on_response, on_response)
	
	
	def describe(self):
		return _("[ All Profiles ]")
	
	
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
		MenuGenerator.__init__(self)
		self.rows = rows
	
	
	def generate(self, menuhandler):
		return _("[ %s Recent Profiles ]") % (self.rows,)
	
	
	def encode(self):
		return { "generator" : self.GENERATOR_NAME, "rows" : self.rows }
	
	
	def callback(self, menu, daemon, controller, menuitem):
		controller.set_profile(menuitem.filename)
		menu.hide()
		def on_response(*a):
			menu.quit(-2)
		daemon.request(b"OSD: " + menuitem.label.encode("utf-8") + b"\n",
			on_response, on_response)
	
	
	def generate(self, menuhandler):
		rv = []
		for p in menuhandler.config['recent_profiles']:
			filename = find_profile(p)
			if filename:
				menuitem = MenuItem("generated", p)
				menuitem.filename = filename
				menuitem.callback = ProfileListMenuGenerator.callback
				rv.append(menuitem)
			if len(rv) >= self.rows:
				break
		return rv


class WindowListMenuGenerator(MenuGenerator):
	""" Generates list of all windows """
	GENERATOR_NAME = "windowlist"
	MAX_LENGHT = 50
	
	def generate(self, menuhandler):
		return _("[ Window Lists ]")

	
	def encode(self):
		return { "generator" : self.GENERATOR_NAME }
	
	
	@staticmethod
	def callback(menu, daemon, controller, menuitem):
		try:
			xid = int(menuitem.id)
			display = Gdk.Display.get_default()
			window = GdkX11.X11Window.foreign_new_for_display(display, xid)
			window.focus(0)
		except Exception as e:
			log.error("Failed to activate window")
			log.error(traceback.format_exc())
		menu.quit(-2)
	
	
	def generate(self, menuhandler):
		rv = []
		dpy = X.Display(hash(GdkX11.x11_get_default_xdisplay()))	# Magic
		root = X.get_default_root_window(dpy)
		
		count, wlist = X.get_window_prop(dpy, root, "_NET_CLIENT_LIST", 1024)
		skip_taskbar = X.intern_atom(dpy, "_NET_WM_STATE_SKIP_TASKBAR", True)
		wlist = cast(wlist, POINTER(X.XID))[0:count]
		for win in wlist:
			if not skip_taskbar in X.get_wm_state(dpy, win):
				title = X.get_window_title(dpy, win)[0:self.MAX_LENGHT]
				menuitem = MenuItem(str(win), title)
				menuitem.callback = WindowListMenuGenerator.callback
				rv.append(menuitem)
		return rv


class GameListMenuGenerator(MenuGenerator):
	"""
	Generates list of applications known to XDG menu
	and belonging to 'Game' category
	"""
	GENERATOR_NAME = "games"
	MAX_LENGHT = 50
	
	_games = None		# Static list of know games
	
	def generate(self, menuhandler):
		return _("[ Games ]")

	
	def encode(self):
		return { "generator" : self.GENERATOR_NAME }
	
	
	@staticmethod
	def callback(menu, daemon, controller, menuitem):
		menuitem._desktop_file.launch()
		menu.quit(-2)
	
	
	def generate(self, menuhandler):
		if GameListMenuGenerator._games is None:
			GameListMenuGenerator._games = []
			id = 0
			for x in Gio.AppInfo.get_all():
				if x.get_categories():
					if "Game" in x.get_categories().split(";"):
						menuitem = MenuItem(str(id), x.get_display_name(),
							icon = x.get_icon())
						menuitem.callback = GameListMenuGenerator.callback
						menuitem._desktop_file = x
						GameListMenuGenerator._games.append(menuitem)
		return GameListMenuGenerator._games


# Add classes to MENU_GENERATORS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'GENERATOR_NAME') ]:
	if i.GENERATOR_NAME is not None:
		MENU_GENERATORS[i.GENERATOR_NAME] = i
