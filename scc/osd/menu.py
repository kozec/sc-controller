#!/usr/bin/env python2
"""
SC-Controller - OSD Menu

Display menu that user can navigate through and print chosen item id to stdout
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, GLib
from scc.paths import get_share_path
from scc.osd import OSDWindow

import os, sys, logging
log = logging.getLogger("osd.menu")


class Menu(OSDWindow):
	EPILOG="""Exit codes:
   0  - clean exit, user selected option
  -1  - clean exit, user canceled menu
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon
   3  - error, sc-daemon went away.
   3  - erorr, failed to lock input stick, pad or button(s)
	"""
	
	def __init__(self):
		OSDWindow.__init__(self, "osd-menu")
		
		self.v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.v.set_name("osd-menu")
		self.items = [( 0, Gtk.Button.new_with_label("None") )]
		
		cursor = os.path.join(get_share_path(), "images", 'menu-cursor.svg')
		self.i = Gtk.Image.new_from_file(cursor)
		self.i.set_name("osd-menu-cursor")
		
		self.f = Gtk.Fixed()
		self.f.add(self.v)
		self.f.add(self.i)
		self.add(self.f)
		self._selected = None
		self.select(0)
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('--control-with', '-c', type=str,
			metavar="option", default='STICK', choices=('LEFT', 'RIGHT', 'STICK'),
			help="which pad or stick should be used to navigate menu (default: STICK)")
		self.argparser.add_argument('--confirm-with', type=str,
			metavar="button", default='A',
			help="button used to confirm choice (default: A)")
		self.argparser.add_argument('--cancel-with', type=str,
			metavar="button", default='B',
			help="button used to cancel menu (default: B)")
		self.argparser.add_argument('--confirm-with-release', action='store_true',
			help="confirm choice with button release instead of button press")
		self.argparser.add_argument('--cancel-with-release', action='store_true',
			help="cancel menu with button release instead of button press")
		self.argparser.add_argument('items', type=str, nargs='+', metavar='id title',
			help="Menu items")
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		if len(self.args.items) % 2 != 0:
			print >>sys.stderr, '%s: error: invalid number of arguments' % (sys.argv[0])
			return False
		# Parse item list to (id, title) tuples
		menuitems = [
			(self.args.items[i * 2], self.args.items[(i * 2) + 1])
			for i in xrange(0, len(self.args.items) / 2)
		]
		self.items = []
		for id, label in menuitems:
			b = Gtk.Button.new_with_label(label)
			self.v.pack_start(b, True, True, 0)
			b.set_name("osd-menu-item")
			b.set_relief(Gtk.ReliefStyle.NONE)
			self.items.append(( id, b ))
		return True
	
	
	def select(self, index):
		if self._selected:
			self._selected[1].set_name("osd-menu-item")
		self._selected = self.items[index]
		self._selected[1].set_name("osd-menu-item-selected")
