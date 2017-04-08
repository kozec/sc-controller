#!/usr/bin/env python2
"""
SC-Controller - Horisontal OSD Menu

Works as OSD menu, but displays all items in one row.

Designed mainly as RPG numeric pad display and looks
awfull with larger number of items.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk
from scc.constants import STICK_PAD_MIN
from scc.osd.grid_menu import GridMenu

import logging
log = logging.getLogger("osd.hmenu")


class HorizontalMenu(GridMenu):
	def __init__(self, cls="osd-menu"):
		GridMenu.__init__(self, cls)
	
	
	def create_parent(self):
		g = Gtk.Grid()
		g.set_name("osd-menu")
		return g
	
	
	def pack_items(self, parent, items):
		x = 0
		for item in items:
			parent.attach(item.widget, x, 0, 1, 1)
			x += 1
	
	
	def on_stick_direction(self, trash, x, y):
		if x != 0:
			self.next_item(-x)
	
	
	def on_event(self, daemon, what, data):
		# Restricts Y axis to dead center, as nothing
		# else makes sense in this kind of menu
		if self._submenu:
			return self._submenu.on_event(daemon, what, data)
		if what == self._control_with and self._use_cursor:
			data = data[0], STICK_PAD_MIN
		GridMenu.on_event(self, daemon, what, data)
