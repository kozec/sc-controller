#!/usr/bin/env python2
"""
SC-Controller - Quick OSD Menu

Controled by buttons instead of stick. Fast to use, but can display only
limited number of items
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk
from scc.menu_data import Separator, Submenu
from scc.gui.svg_widget import SVGWidget
from scc.osd.menu import Menu, MenuIcon
from scc.osd import OSDWindow
from scc.tools import find_icon

import os, sys, logging
log = logging.getLogger("osd.quickmenu")


class QuickMenu(OSDWindow):
	IMAGE = "quickmenu.svg"
	
	def __init__(self, imagepath="/usr/share/scc/images", cls="osd-menu"):
		OSDWindow.__init__(self, cls)
		self.imagepath = imagepath
	
	
	def show(self):
		self.main_area = Gtk.Fixed()
		self.background = SVGWidget(self, os.path.join(self.imagepath, self.IMAGE))
		
		self.main_area.set_property("margin-left", 10)
		self.main_area.set_property("margin-right", 10)
		self.main_area.set_property("margin-top", 10)
		self.main_area.set_property("margin-bottom", 10)
		
		self.main_area.put(self.background, 0, 0)
		
		self.add(self.main_area)
		
		OSDWindow.show(self)
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('--cancel-with', type=str,
			metavar="button", default='START',
			help="button used to cancel menu (default: START)")
		self.argparser.add_argument('--cancel-with-release', action='store_true',
			help="cancel menu with button release instead of button press")
		self.argparser.add_argument('--from-profile', '-p', type=str,
			metavar="profile_file menu_name",
			help="load menu items from profile file")
		self.argparser.add_argument('--from-file', '-f', type=str,
			metavar="filename",
			help="load menu items from json file")
		self.argparser.add_argument('--print-items', action='store_true',
			help="prints menu items to stdout")
		self.argparser.add_argument('items', type=str, nargs='*', metavar='id title',
			help="Menu items")
	
	
	def generate_widget(self, item):
		if isinstance(item, Separator):
			# Ignored here
			return None
		elif item.id is None:
			# Dummies are ignored as well
			return None
		else:
			icon_file, has_colors = find_icon(item.icon, False)
			if icon_file:
				# Gridmenu hides label when icon is displayed
				widget = Gtk.Button()
				widget.set_relief(Gtk.ReliefStyle.NONE)
				widget.set_name("osd-menu-item-big-icon")
				if isinstance(item, Submenu):
					item.callback = self.show_submenu
				icon = MenuIcon(icon_file, has_colors)
				widget.add(icon)
				return widget
			else:
				return Menu.generate_widget(self, item)



if __name__ == "__main__":
	import gi
	gi.require_version('Gtk', '3.0')
	gi.require_version('Rsvg', '2.0')
	gi.require_version('GdkX11', '3.0')
	
	from scc.tools import init_logging
	from scc.paths import get_share_path
	init_logging()
	
	m = QuickMenu(imagepath="./images")
	if not m.parse_argumets(sys.argv):
		sys.exit(1)
	m.run()
	sys.exit(m.get_exit_code())
