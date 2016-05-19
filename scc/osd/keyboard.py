#!/usr/bin/env python2
"""
SC-Controller - OSD Menu

Display menu that user can navigate through and print chosen item id to stdout
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, GLib
from scc.constants import LEFT, RIGHT, STICK, STICK_PAD_MIN, STICK_PAD_MAX
from scc.constants import STICK_PAD_MIN_HALF, STICK_PAD_MAX_HALF
from scc.constants import SCButtons
from scc.tools import point_in_gtkrect
from scc.paths import get_share_path
from scc.menu_data import MenuData
from scc.gui.daemon_manager import DaemonManager
from scc.gui.svg_widget import SVGWidget
from scc.osd.timermanager import TimerManager
from scc.osd import OSDWindow

import os, sys, math, json, logging
log = logging.getLogger("osd.menu")


class Keyboard(OSDWindow, TimerManager):
	EPILOG="""Exit codes:
   0  - clean exit, user closed keyboard
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon, sc-daemon reported error or died while menu is displayed.
   3  - erorr, failed to lock input stick, pad or button(s)
	"""
	HILIGHT_COLOR = "#00688D"
	
	def __init__(self):
		OSDWindow.__init__(self, "osd-menu")
		TimerManager.__init__(self)
		self.daemon = None
		
		keyboard = os.path.join(get_share_path(), "images", 'keyboard.svg')
		self.background = SVGWidget(self, keyboard)
		
		self.limit_left  = self.background.get_rect_area(self.background.get_element("LIMIT_LEFT"))
		self.limit_right = self.background.get_rect_area(self.background.get_element("LIMIT_RIGHT"))
		
		cursor = os.path.join(get_share_path(), "images", 'menu-cursor.svg')
		self.cursor_left = Gtk.Image.new_from_file(cursor)
		self.cursor_left.set_name("osd-menu-cursor")
		self.cursor_right = Gtk.Image.new_from_file(cursor)
		self.cursor_right.set_name("osd-menu-cursor")
		
		self._eh_ids = []
		self._hovers = { self.cursor_left : None, self.cursor_right : None }
		
		self.f = Gtk.Fixed()
		self.f.add(self.background)
		self.f.add(self.cursor_left)
		self.f.add(self.cursor_right)
		self.add(self.f)
		
		self.set_cursor_position(0, 0, self.cursor_left, self.limit_left)
		self.set_cursor_position(0, 0, self.cursor_right, self.limit_right)
	
	
	def use_daemon(self, d):
		"""
		Allows (re)using already existin DaemonManager instance in same process
		"""
		self.daemon = d
		self._cononect_handlers()
		self.on_daemon_connected(self.daemon)
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		return True
	
	
	def _cononect_handlers(self):
		self._eh_ids += [
			self.daemon.connect('dead', self.on_daemon_died),
			self.daemon.connect('error', self.on_daemon_died),
			self.daemon.connect('event', self.on_event),
			self.daemon.connect('alive', self.on_daemon_connected),
		]
	
	
	def run(self):
		self.daemon = DaemonManager()
		self._cononect_handlers()
		OSDWindow.run(self)
	
	
	def on_daemon_died(self, *a):
		log.error("Daemon died")
		self.quit(2)
	
	
	def on_failed_to_lock(self, error):
		log.error("Failed to lock input: %s", error)
		self.quit(3)
	
	
	def on_daemon_connected(self, *a):
		def success(*a):
			log.error("Sucessfully locked input")
			pass
		
		locks = [ LEFT, RIGHT, STICK, 'A', 'B' ]
		self.daemon.lock(success, self.on_failed_to_lock, *locks)
	
	
	def quit(self, code=-1):
		self.daemon.unlock_all()
		for x in self._eh_ids:
			self.daemon.disconnect(x)
		self._eh_ids = []
		OSDWindow.quit(self, code)
	
	
	def on_event(self, daemon, what, data):
		if what == LEFT:
			x, y = data
			self.set_cursor_position(x, y, self.cursor_left, self.limit_left)
		elif what == RIGHT:
			x, y = data
			self.set_cursor_position(x, y, self.cursor_right, self.limit_right)
			
	
	def set_cursor_position(self, x, y, cursor, limit):
		w = limit[2] - (cursor.get_allocation().width * 0.5)
		h = limit[3] - (cursor.get_allocation().height * 0.5)
		x = x / float(STICK_PAD_MAX)
		y = y / float(STICK_PAD_MAX) * -1.0
		
		x, y = circle_to_square(x, y)
		
		x = (limit[0] + w * 0.5) + x * w * 0.5
		y = (limit[1] + h * 0.5) + y * h * 0.5
		
		self.f.move(cursor, int(x), int(y))
		for a in self.background.areas:
			if a.contains(x, y):
				if a != self._hovers[cursor]:
					self._hovers[cursor] = a
					self.background.hilight({
						"AREA_" + a.name : Keyboard.HILIGHT_COLOR
						for a in [ a for a in self._hovers.values() if a ]
					})
				break


PId4 = math.pi / 4.0
def circle_to_square(x, y):
	# Adapted from http://theinstructionlimit.com/squaring-the-thumbsticks
	
	# Determine the theta angle
	angle = math.atan2(y, x) + math.pi
	
	squared = 0, 0
	# Scale according to which wall we're clamping to
	# X+ wall
	if angle <= PId4 or angle > 7.0 * PId4:
		squared = x * (1.0 / math.cos(angle)), y * (1.0 / math.cos(angle))
	# Y+ wall
	elif angle > PId4 and angle <= 3.0 * PId4:
		squared = x * (1.0 / math.sin(angle)), y * (1.0 / math.sin(angle))
	# X- wall
	elif angle > 3.0 * PId4 and angle <= 5.0 * PId4:
		squared = x * (-1.0 / math.cos(angle)), y * (-1.0 / math.cos(angle))
	# Y- wall
	elif angle > 5.0 * PId4 and angle <= 7.0 * PId4:
		squared = x * (-1.0 / math.sin(angle)), y * (-1.0 / math.sin(angle))
	else:
		raise ValueError("Invalid angle...?")
	
	return squared
