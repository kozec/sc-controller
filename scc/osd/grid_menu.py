#!/usr/bin/env python2
"""
SC-Controller - Grid OSD Menu

Works as OSD menu, but displays item in (as rectangluar as possible - and
that's usually not very much) grid.
"""

from scc.tools import _, set_logging_level

from gi.repository import Gtk
from scc.menu_data import Separator, Submenu
from scc.osd.menu import Menu, MenuIcon
from scc.osd import OSDWindow
from scc.tools import find_icon

import math, logging
log = logging.getLogger("osd.gridmenu")


class GridMenu(Menu):
	PREFER_BW_ICONS = True
	
	def __init__(self, cls="osd-menu"):
		Menu.__init__(self, cls)
		self.ipr = 1	# items per row
	
	
	def create_parent(self):
		g = Gtk.Grid()
		g.set_name("osd-menu")
		return g
	
	
	def pack_items(self, parent, items):
		if self._size > 0:
			self.ipr = self._size
		else:
			self.ipr = int(math.sqrt(max(1, len(items)-1))+1)
			if len(items) == 6 : self.ipr = 3	# Special (common) cases
			if len(items) == 8 : self.ipr = 4	# Special (common) cases
		x, y = 0, 0
		for item in items:
			parent.attach(item.widget, x, y, 1, 1)
			x += 1
			if x >= self.ipr:
				x = 0
				y += 1
	
	
	def on_stick_direction(self, trash, x, y):
		if x != 0:
			self.next_item(-x)
		elif y != 0:
			for i in range(0, self.ipr):
				self.next_item(y)
	
	
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
