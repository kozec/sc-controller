#!/usr/bin/env python2
"""
SC-Controller - OSD Message

Display message that just sits there
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, GLib
from scc.osd import OSDWindow

import os, sys, logging
log = logging.getLogger("osd.message")


class Message(OSDWindow):
	def __init__(self):
		OSDWindow.__init__(self, "osd-message")
		
		self.timeout = 5
		self.text = "text"
		self._timeout_id = None
	
	
	def show(self):
		self.l = Gtk.Label()
		self.l.set_name("osd-label")
		self.l.set_label(self.text)
		
		self.add(self.l)
		
		OSDWindow.show(self)
		self._timeout_id = GLib.timeout_add_seconds(self.timeout, self.quit)
	
	
	def extend(self):
		if self._timeout_id:
			self.set_state(Gtk.StateType.ACTIVE)
			self.l.set_state(Gtk.StateType.ACTIVE)
			GLib.timeout_add_seconds(0.5, self.cancel_active_state)
			GLib.source_remove(self._timeout_id)
			self._timeout_id = GLib.timeout_add_seconds(self.timeout, self.quit)
	
	
	def cancel_active_state(self):
		self.set_state(Gtk.StateType.NORMAL)
		self.l.set_state(Gtk.StateType.NORMAL)
	
	
	def hash(self):
		return hash(self.text) + self.timeout
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('-t', type=float, metavar="seconds",
				default=5, help="time before message is hidden (default: 5)")
		self.argparser.add_argument('text', type=str, help="text to display")
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		self.text = self.args.text
		self.timeout = self.args.t
		return True	
