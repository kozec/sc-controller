#!/usr/bin/env python2
"""
SC-Controller - OSD

Common methods for OSD-related stuff
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GLib, GdkX11
from scc.lib import xwrappers as X

import os, sys, argparse, logging
log = logging.getLogger("osd")


class OSDWindow(Gtk.Window):
	# TODO: Configurable css
	CSS = """
		#osd-message, #osd-menu, #osd-keyboard {
			background-color: black;
			border: 6px lime double;
		}
		
		#osd-label {
			color: lime;
			border: none;
			font-size: xx-large;
			margin: 15px 15px 15px 15px;
		}
		
		#osd-menu {
			padding: 7px 7px 7px 7px;
		}
		
		#osd-keyboard-container {
			padding: 6px 6px 6px 6px;
		}
		
		#osd-menu-item, #osd-menu-item-selected {
			color: #00E000;
			border-radius: 0;
			font-size: x-large;
			background-image: none;
			background-color: black;
			margin: 0px 0px 2px 0px;
			border: 1px #004000 solid;
		}
		
		#osd-menu-item-selected {
			color: #00FF00;
			background-color: #000070;
			border: 1px #00FF00 solid;
		}
		
		#osd-menu-cursor, #osd-keyboard-cursor {
		}
	"""
	EPILOG = ""
	
	def __init__(self, wmclass):
		Gtk.Window.__init__(self)
		OSDWindow._apply_css()
		
		self.argparser = argparse.ArgumentParser(description=__doc__,
			formatter_class=argparse.RawDescriptionHelpFormatter,
			epilog=self.EPILOG)
		self._add_arguments()
		self.exit_code = -1
		self.position = (20, -20)
		self.mainloop = None
		self.set_name(wmclass)
		self.set_wmclass(wmclass, wmclass)
		self.set_decorated(False)
		self.stick()
		self.set_skip_taskbar_hint(True)
		self.set_skip_pager_hint(True)
		self.set_keep_above(True)
		self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
	
	
	@staticmethod
	def _apply_css():
		css = Gtk.CssProvider()
		css.load_from_data(str(OSDWindow.CSS))
		Gtk.StyleContext.add_provider_for_screen(
				Gdk.Screen.get_default(), css,
				Gtk.STYLE_PROVIDER_PRIORITY_USER)
	
	
	def _add_arguments(self):
		""" Should be overriden AND called by child class """
		self.argparser.add_argument('-x', type=int, metavar="pixels", default=20,
			help="""horizontal position in pixels, from left side of screen.
			Use negative value to specify as distance from right side (default: 20)""")
		self.argparser.add_argument('-y', type=int, metavar="pixels", default=-20,
			help="""vertical position in pixels, from top side of screen.
			Use negative value to specify as distance from bottom side (default: -20)""")
	
	
	def parse_argumets(self, argv):
		""" Returns True on success """
		try:
			self.args = self.argparser.parse_args(argv[1:])
		except BaseException, e:	# Includes SystemExit
			return False
		del self.argparser
		self.position = (self.args.x, self.args.y)
		return True
	
	def make_window_clicktrough(self):
		dpy = X.Display(hash(GdkX11.x11_get_default_xdisplay()))		# I have no idea why this works...
		win = X.XID(self.get_window().get_xid())
		reg = X.create_region(dpy, None, 0)
		X.set_window_shape_region (dpy, win, X.SHAPE_BOUNDING, 0, 0, 0)
		X.set_window_shape_region (dpy, win, X.SHAPE_INPUT, 0, 0, reg)
		X.destroy_region (dpy, reg)
	
	
	def show(self):
		self.get_children()[0].show_all()
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
	
	
	def get_exit_code(self):
		return self.exit_code
	
	
	def run(self):
		self.mainloop = GLib.MainLoop()
		self.show()
		self.mainloop.run()
	
	
	def quit(self, code=-1):
		self.exit_code = code
		if self.mainloop:
			self.mainloop.quit()
		else:
			self.destroy()
