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
	
	def __init__(self, text, timeout=5, x=20, y=-20):
		OSDWindow.__init__(self, "osd-message", x=x, y=y)
		
		self.timeout = timeout
		
		self.l = Gtk.Label()
		self.l.set_name("osd-label")
		self.l.set_markup("<span font_size='xx-large'>%s</span>" % (text,))
		
		self.add(self.l)
	
	
	def show(self):
		OSDWindow.show(self)
		GLib.timeout_add_seconds(self.timeout, self.quit)
