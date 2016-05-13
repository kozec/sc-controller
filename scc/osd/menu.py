#!/usr/bin/env python2
"""
SC-Controller - OSD Menu

Display menu that user can navigate through
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, GLib
from scc.osd import OSDWindow

import os, sys, logging
log = logging.getLogger("osd.menu")


class Menu(OSDWindow):
	def __init__(self, items, x=20, y=-20):
		OSDWindow.__init__(self, "osd-menu", x=x, y=y)
		
		self.v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.v.set_name("osd-menu")
		self.items = []
		for id, label in items:
			b = Gtk.Button.new_with_label(label)
			self.v.pack_start(b, True, True, 0)
			b.set_name("osd-menu-item")
			b.set_relief(Gtk.ReliefStyle.NONE)
			self.items.append(( id, b ))
		
		self.add(self.v)
		self._selected = None
		self.select(0)
	
	def select(self, index):
		if self._selected:
			self._selected[1].set_name("osd-menu-item")
		self._selected = self.items[index]
		self._selected[1].set_name("osd-menu-item-selected")
