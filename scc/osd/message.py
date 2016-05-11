#!/usr/bin/env python2
"""
SC-Controller - OSD Message

Display message that just sits there
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GLib

import os, sys, json, logging
log = logging.getLogger("osd.message")

class Message(Gtk.Window):
	# TODO: Configurable
	CSS = """
		#osd-message {
			background-color: black;
			border: 6px lime double;
		}
		
		#osd-label {
			color: lime;
			border: 0px black none;
			margin: 15px 15px 15px 15px;
		}
	"""
	
	def __init__(self, text):
		Gtk.Window.__init__(self)
		css = Gtk.CssProvider()
		css.load_from_data(str(Message.CSS))
		Gtk.StyleContext.add_provider_for_screen(
				Gdk.Screen.get_default(), css,
				Gtk.STYLE_PROVIDER_PRIORITY_USER)
		
		
		self.set_name("osd-message")
		self.set_wmclass("sc-osd-message", "sc-osd-message")
		self.set_decorated(False)
		self.stick()
		self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
		
		self.l = Gtk.Label()
		self.l.set_name("osd-label")
		self.l.set_markup("<span font_size='xx-large'>%s</span>" % (text,))
		
		self.add(self.l)
	
	
	def show(self):
		self.show_all()
	
	def run(self, argv):
		self.show()
		GLib.MainLoop().run()
