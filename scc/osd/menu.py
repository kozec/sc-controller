#!/usr/bin/env python2
"""
SC-Controller - OSD Menu

Display menu that user can navigate through and print chosen item id to stdout
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, GLib
from scc.constants import LEFT, RIGHT, STICK, STICK_PAD_MIN, STICK_PAD_MAX
from scc.paths import get_share_path
from scc.osd import OSDWindow
from scc.osd.timermanager import TimerManager
from scc.gui.daemon_manager import DaemonManager

import os, sys, logging
log = logging.getLogger("osd.menu")


class Menu(OSDWindow, TimerManager):
	EPILOG="""Exit codes:
   0  - clean exit, user selected option
  -1  - clean exit, user canceled menu
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon, sc-daemon reported error or died while menu is displayed.
   3  - erorr, failed to lock input stick, pad or button(s)
	"""
	REPEAT_DELAY = 0.5
	
	def __init__(self):
		OSDWindow.__init__(self, "osd-menu")
		TimerManager.__init__(self)
		self.daemon = None
		
		self.v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.v.set_name("osd-menu")
		self.items = [( 0, Gtk.Button.new_with_label("None") )]
		
		cursor = os.path.join(get_share_path(), "images", 'menu-cursor.svg')
		self.i = Gtk.Image.new_from_file(cursor)
		self.i.set_name("osd-menu-cursor")
		
		self.f = Gtk.Fixed()
		self.f.add(self.v)
		# self.f.add(self.i)
		self.add(self.f)
		
		self._direction = 0		# Movement direction
		self._selected = None
		self._control_with = STICK
		self._confirm_with = 'A'
		self._cancel_with = 'B'
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('--control-with', '-c', type=str,
			metavar="option", default=STICK, choices=(LEFT, RIGHT, STICK),
			help="which pad or stick should be used to navigate menu (default: %s)" % (STICK,))
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
		
		# Parse simpler arguments
		self._control_with = self.args.control_with
		self._confirm_with = self.args.confirm_with
		self._cancel_with = self.args.cancel_with
		
		# Parse item list to (id, title) tuples
		menuitems = [
			(self.args.items[i * 2], self.args.items[(i * 2) + 1])
			for i in xrange(0, len(self.args.items) / 2)
		]
		self.items = []
		
		# Create buttons that are displayed on screen
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
	
	
	def run(self):
		self.daemon = DaemonManager()
		self.daemon.connect('dead', self.on_daemon_died)
		self.daemon.connect('error', self.on_daemon_died)
		self.daemon.connect('event', self.on_event)
		self.daemon.connect('alive', self.on_daemon_connected)
		self.select(0)
		OSDWindow.run(self)
	
	
	def on_daemon_died(self, *a):
		self.quit(2)
	
	
	def on_failed_to_lock(self, error):
		log.error("Failed to lock input: %s", error)
		self.quit(3)
	
	
	def on_daemon_connected(self, *a):
		def success(*a):
			log.error("Sucessfully locked input")
			pass
		
		locks = [ self._control_with, self._confirm_with, self._cancel_with ]
		self.daemon.lock(success, self.on_failed_to_lock, *locks)
	
	
	def on_move(self):
		i = self.items.index(self._selected) + self._direction
		if i >= len(self.items):
			i = 0
		elif i < 0:
			i = len(self.items) - 1
		self.select(i)
		self.timer("move", self.REPEAT_DELAY, self.on_move)
	
	
	def on_event(self, daemon, what, data):
		if what == self._control_with:
			x, y = data
			if y < STICK_PAD_MIN / 3 and self._direction != 1:
				self._direction = 1
				self.on_move()
			if y > STICK_PAD_MAX / 3 and self._direction != -1:
				self._direction = -1
				self.on_move()
			if y < STICK_PAD_MAX / 3 and y > STICK_PAD_MIN / 3 and self._direction != 0:
				self._direction = 0
				self.cancel_timer("move")
		elif what == self._cancel_with:
			if data[0] == 0:	# Button released
				self.quit(-1)
		elif what == self._confirm_with:
			if data[0] == 0:	# Button released
				print self._selected[0]
				self.quit(0)
		else:
			print ">>>", what
