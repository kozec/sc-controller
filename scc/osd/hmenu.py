#!/usr/bin/env python2
"""
SC-Controller - Horisontal OSD Menu

Works as OSD menu, but displays all items in one row.

Designed mainly as RPG numeric pad display and looks
awfull with larger number of items.
"""

from scc.tools import _, set_logging_level

from gi.repository import Gtk
from scc.menu_data import Separator, Submenu
from scc.constants import STICK_PAD_MIN
from scc.osd.grid_menu import GridMenu
from scc.osd.menu import MenuIcon

import logging
log = logging.getLogger("osd.hmenu")


class HorizontalMenu(GridMenu):
	def __init__(self, cls="osd-menu"):
		GridMenu.__init__(self, cls)
	
	
	def create_parent(self):
		g = Gtk.Grid()
		g.set_name("osd-menu")
		return g
	
	
	def generate_widget(self, item):
		"""
		Generates gtk widget for specified menutitem
		Ignores Submenus and Separators but applies icon size
		"""
		if isinstance(item, (Separator, Submenu)) or item.id is None:
			return None
		else:
			widget = GridMenu.generate_widget(self, item)
			icon = widget.get_children()[-1]
			if self._size > 1 and isinstance(icon, MenuIcon):
				widget.set_size_request(-1, 32 + self._size * 3)
			return widget
	
	
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
