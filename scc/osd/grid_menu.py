#!/usr/bin/env python2
"""
SC-Controller - Grid OSD Menu

Works as OSD menu, but displays item in (as rectangluar as possible - and
that's usually not very much) grid.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk
from scc.osd.menu import Menu
from scc.osd import OSDWindow

import math, logging
log = logging.getLogger("osd.gridmenu")


class GridMenu(Menu):
	def create_parent(self):
		g = Gtk.Grid()
		g.set_name("osd-menu")
		return g
	
	
	def pack_items(self, parent, items):
		ipr = int(math.sqrt(max(1, len(items)-1))+1)	# items per row
		x, y = 0, 0
		for item in items:
			parent.attach(item.widget, x, y, 1, 1)
			x += 1
			if x >= ipr:
				x = 0
				y += 1
