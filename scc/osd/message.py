#!/usr/bin/env python2
"""
SC-Controller - OSD Message

Display message that just sits there
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from scc.tools import find_lib

from gi.repository import Gtk, Gdk, GLib, GdkX11
import os, sys, json, ctypes, logging
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
		self.set_skip_taskbar_hint(True)
		self.set_skip_pager_hint(True)
		self.set_keep_above(True)
		self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
		
		self.l = Gtk.Label()
		self.l.set_name("osd-label")
		self.l.set_markup("<span font_size='xx-large'>%s</span>" % (text,))
		
		self.add(self.l)
	
	
	def make_window_clicktrough(self):
		lib, search_paths = find_lib("libx11osd", os.path.dirname(__file__))
		if not lib:
			raise OSError('Cant find libx11osd. searched at:\n {}'.format(
				'\n'.join(search_paths)
			)
		)
		lib = ctypes.CDLL(lib)
		dpy = ctypes.c_void_p(hash(GdkX11.x11_get_default_xdisplay()))		# I have no idea why this works...
		win = ctypes.c_ulong(self.get_window().get_xid())					# Window -> XID -> unsigned long
		lib.make_window_clicktrough(dpy, win)
	
	
	def show(self):
		self.l.show_all()
		self.realize()
		self.get_window().set_override_redirect(True)
		Gtk.Window.show(self)
		self.make_window_clicktrough()
	
	
	def run(self, argv):
		self.show()
		GLib.MainLoop().run()
