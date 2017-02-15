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
	def __init__(self, cls="osd-menu"):
		Menu.__init__(self, cls)
		self.ipr = 1	# items per row
	
	
	def create_parent(self):
		g = Gtk.Grid()
		g.set_name("osd-menu")
		return g
	
	
	def pack_items(self, parent, items):
		if self._max_size > 0:
			self.ipr = self._max_size
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
			for i in xrange(0, self.ipr):
				self.next_item(y)
