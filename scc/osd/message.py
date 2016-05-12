#!/usr/bin/env python2
"""
SC-Controller - OSD Message

Display message that just sits there
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GLib, GdkX11
from scc.lib import xfixes

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
	
	def __init__(self, text, timeout=5, x=20, y=-20):
		Gtk.Window.__init__(self)
		css = Gtk.CssProvider()
		css.load_from_data(str(Message.CSS))
		Gtk.StyleContext.add_provider_for_screen(
				Gdk.Screen.get_default(), css,
				Gtk.STYLE_PROVIDER_PRIORITY_USER)
		
		self.timeout = timeout
		self.mainloop = GLib.MainLoop()
		self.position = (x, y)
		self.set_name("osd-message")
		self.set_wmclass("sc-osd-message", "sc-osd-message")
		self.set_decorated(False)
		self.stick()
		self.set_skip_taskbar_hint(True)
		self.set_skip_pager_hint(True)
		self.set_keep_above(True)
		self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
		
		self.l = Gtk.Label()
		self.l.set_name("osd-label")
		self.l.set_markup("<span font_size='xx-large'>%s</span>" % (text,))
		
		self.add(self.l)
	
	
	def make_window_clicktrough(self):
		dpy = xfixes.Display(hash(GdkX11.x11_get_default_xdisplay()))		# I have no idea why this works...
		win = xfixes.XID(self.get_window().get_xid())
		reg = xfixes.create_region(dpy, None, 0)
		xfixes.set_window_shape_region (dpy, win, xfixes.SHAPE_BOUNDING, 0, 0, 0)
		xfixes.set_window_shape_region (dpy, win, xfixes.SHAPE_INPUT, 0, 0, reg)
		xfixes.destroy_region (dpy, reg)
	
	
	def show(self):
		self.l.show_all()
		self.realize()
		self.get_window().set_override_redirect(True)
		x, y = self.position
		if x < 0:	# Negative X position is counted from right border
			x = Gdk.Screen.width() - self.get_allocated_size()[0].width + x + 1
		if y < 0:	# Negative Y position is counted from bottom border
			y = Gdk.Screen.height() - self.get_allocated_size()[0].height + y + 1
		
		self.move(x, y)
		Gtk.Window.show(self)
		self.make_window_clicktrough()
		
		GLib.timeout_add_seconds(self.timeout, self.quit)
	
	
	def run(self, argv):
		self.show()
		self.mainloop.run()
	
	
	def quit(self):
		self.mainloop.quit()
