#!/usr/bin/env python2
"""
SC-Controller - OSD Message

Display message that just sits there
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, GLib
from scc.special_actions import OSDAction
from scc.tools import find_icon
from scc.osd.menu import MenuIcon
from scc.osd import OSDWindow

import os, sys, logging
log = logging.getLogger("osd.message")


class Message(OSDWindow):
	
	def __init__(self):
		OSDWindow.__init__(self, "osd-message")
		
		self.timeout = OSDAction.DEFAULT_TIMEOUT
		self.size = OSDAction.DEFAULT_SIZE
		self.text = "text"
		self.icon = "system/cog"
		self._timeout_id = None
	
	
	def show(self):
		self.l = Gtk.Label()
		self.l.set_name("osd-label-%s" % (self.size, ))
		self.l.set_label(self.text)
		
		icon_file, has_colors = find_icon(self.icon, prefer_bw=True)
		if icon_file:
			self.vbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
			self.i = MenuIcon(icon_file, has_colors)
			self.vbox.pack_start(self.i, True, False, 0)
			self.vbox.pack_start(self.l, True, True, 0)
			self.add(self.vbox)
		else:
			self.add(self.l)
		
		if self.size < 2:
			self.set_name("osd-message-1")
		OSDWindow.show(self)
		if self.timeout > 0:
			self._timeout_id = GLib.timeout_add_seconds(self.timeout, self.quit)
	
	
	def extend(self):
		self.set_state(Gtk.StateType.ACTIVE)
		self.l.set_state(Gtk.StateType.ACTIVE)
		GLib.timeout_add_seconds(0.5, self.cancel_active_state)
		if self._timeout_id:
			GLib.source_remove(self._timeout_id)
			self._timeout_id = GLib.timeout_add_seconds(self.timeout, self.quit)
	
	
	def cancel_active_state(self):
		self.set_state(Gtk.StateType.NORMAL)
		self.l.set_state(Gtk.StateType.NORMAL)
	
	
	def hash(self):
		return hash(self.text) + self.timeout - (self.size * 5)
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('-t', type=float, metavar="seconds",
				default=5, help="time before message is hidden (default: 5; 0 means forever)")
		self.argparser.add_argument('-s', type=int, metavar="size",
				default=3, help="font size, in range 1 to 3 (default: 3)")
		self.argparser.add_argument('text', type=str, help="text to display")
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		self.text = self.args.text
		self.timeout = self.args.t
		self.size = self.args.s
		return True	
