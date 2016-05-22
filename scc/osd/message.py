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
	
	
	def show(self):
		self.l = Gtk.Label()
		self.l.set_name("osd-label")
		self.l.set_label(self.text)
		
		self.add(self.l)
		
		OSDWindow.show(self)
		GLib.timeout_add_seconds(self.timeout, self.quit)
	
	
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
