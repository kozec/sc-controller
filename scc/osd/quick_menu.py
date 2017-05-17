#!/usr/bin/env python2
"""
SC-Controller - Quick OSD Menu

Controled by buttons instead of stick. Fast to use, but can display only
limited number of items
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk
from scc.menu_data import MenuItem, Submenu
from scc.tools import find_icon
from scc.config import Config
from scc.osd.menu import Menu, MenuIcon
from scc.osd import OSDWindow

import os, sys, logging
log = logging.getLogger("osd.quickmenu")


class QuickMenu(Menu):
	BUTTONS = [ "A", "B", "X", "Y", "LB", "RB"]
	
	
	def __init__(self, cls="osd-menu"):
		Menu.__init__(self, cls)
		self._cancel_with = 'START'
		self._pressed = []
	
	
	def generate_widget(self, item):
		"""
		In QuickMenu, everything but submenus and simple
		menuitems is ignored.
		"""
		if self._button_index >= len(self.BUTTONS):
			return None
		if isinstance(item, (MenuItem, Submenu)):
			widget = Gtk.Button.new_with_label(item.label)
			widget.set_relief(Gtk.ReliefStyle.NONE)
			if hasattr(widget.get_children()[0], "set_xalign"):
				widget.get_children()[0].set_xalign(0)
			else:
				widget.get_children()[0].set_halign(Gtk.Align.START)
			if isinstance(item, Submenu):
				item.callback = self.show_submenu
				label1 = widget.get_children()[0]
				label2 = Gtk.Label(_(">>"))
				label2.set_property("margin-left", 30)
				box = Gtk.Box(Gtk.Orientation.HORIZONTAL)
				widget.remove(label1)
				box.pack_start(label1, True, True, 1)
				box.pack_start(label2, False, True, 1)
				widget.add(box)
				widget.set_name("osd-menu-item")
			elif item.id is None:
				# Ignored as well
				return None
			else:
				widget.set_name("osd-menu-item")
			
			item.button = self.BUTTONS[self._button_index]
			self._button_index += 1
			
			icon_file, has_colors = find_icon("buttons/%s" % item.button, False)
			icon = MenuIcon(icon_file, has_colors)
			label = widget.get_children()[0]
			for c in [] + widget.get_children():
				widget.remove(c)
			box = Gtk.Box()
			box.pack_start(icon,  False, True, 0)
			box.pack_start(label, True, True, 10)
			widget.add(box)
			return widget
		return None
	
	
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
	
	
	def lock_inputs(self):
		def success(*a):
			log.error("Sucessfully locked input")
		locks = [ x for x in self.BUTTONS ] + [ self._cancel_with ]
		self.controller.lock(success, self.on_failed_to_lock, *locks)
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		if not self.config: self.config = Config()
		
		self._cancel_with = self.args.cancel_with
		self.parse_menu()
		
		# Create buttons that are displayed on screen
		items = self.items.generate(self)
		self.items = []
		self._button_index = 0
		for item in items:
			item.widget = self.generate_widget(item)
			if item.widget is not None:
				self.items.append(item)
		self.pack_items(self.parent, self.items)
		if len(self.items) == 0:
			print >>sys.stderr, '%s: error: no items in menu' % (sys.argv[0])
			return False
		
		return True
	
	
	def select(self, index):
		pass
	
	
	def pressed(self, what):
		"""
		Called when button is pressed. If menu with that button assigned
		exists, it is hilighted.
		"""
		for item in self.items:
			if item.button == what:
				self._pressed.append(item)
				item.widget.set_name("osd-menu-item-selected")
	
	
	def released(self, what):
		"""
		Called when button is pressed. If menu with that button assigned
		exists, it is hilighted.
		"""
		last = None
		for item in self.items:
			if item.button == what:
				while item in self._pressed:
					self._pressed.remove(item)
				item.widget.set_name("osd-menu-item")
				last = item
		
		if len(self._pressed) == 0 and last is not None:
			if last.callback:
				last.callback(self, self.daemon, self._pressed)
			else:
				self._selected = last
				self.quit(0)
	
	
	def on_event(self, daemon, what, data):
		if self._submenu:
			return self._submenu.on_event(daemon, what, data)
		elif what == self._cancel_with:
			if data[0] == 0:	# Button released
				self.quit(-1)
		elif what in self.BUTTONS:
			if data[0] == 1:	# Button pressed
				self.pressed(what)
			else:				# Released
				self.released(what)


if __name__ == "__main__":
	import gi
	gi.require_version('Gtk', '3.0')
	gi.require_version('Rsvg', '2.0')
	gi.require_version('GdkX11', '3.0')
	
	from scc.tools import init_logging
	from scc.paths import get_share_path
	init_logging()
	
	m = QuickMenu()
	if not m.parse_argumets(sys.argv):
		sys.exit(1)
	m.run()
	if m.get_exit_code() == 0:
		print m.get_selected_item_id()
	sys.exit(m.get_exit_code())
