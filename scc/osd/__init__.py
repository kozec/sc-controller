#!/usr/bin/env python2
"""
SC-Controller - OSD

Common methods for OSD-related stuff
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GLib, GObject, GdkX11
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX
from scc.osd.timermanager import TimerManager
from scc.lib import xwrappers as X
from scc.config import Config

import os, sys, argparse, logging
log = logging.getLogger("osd")


class OSDWindow(Gtk.Window):
	CSS = """
		#osd-message, #osd-menu, #osd-keyboard {
			background-color: #%(background)s;
			border: 6px #%(border)s double;
		}
		
		#osd-area {
			background-color: #%(border)s;
		}
		
		#osd-label {
			color: #%(text)s;
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
		
		#osd-menu-item, #osd-menu-item-selected, #osd-menu-dummy {
			color: #%(text)s;
			border-radius: 0;
			font-size: x-large;
			background-image: none;
			background-color: #%(background)s;
			margin: 0px 0px 2px 0px;
		}
		
		#osd-menu-item {
			border: 1px #%(menuitem_border)s solid;
		}
		
		#osd-menu-separator {
			color: #%(menuseparator)s;
			font-size: large;
			background-image: none;
			background-color: #%(background)s;
			margin: 5px 0px 0px 0px;
			padding: 0px 0px 0px 0px;
		}
		
		#osd-menu-item-selected {
			color: #%(menuitem_hilight_text)s;
			background-color: #%(menuitem_hilight)s;
			border: 1px #%(menuitem_hilight_border)s solid;
		}
		
		#osd-menu-cursor, #osd-keyboard-cursor {
		}
	"""
	EPILOG = ""
	css_provider = None			# Used by staticmethods
	
	def __init__(self, wmclass):
		Gtk.Window.__init__(self)
		OSDWindow._apply_css(Config())
		
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
	def _apply_css(config):
		if OSDWindow.css_provider:
			Gtk.StyleContext.remove_provider_for_screen(
				Gdk.Screen.get_default(), OSDWindow.css_provider)
		
		try:
			OSDWindow.css_provider = Gtk.CssProvider()
			OSDWindow.css_provider.load_from_data(str(OSDWindow.CSS % config['osd_colors']))
			Gtk.StyleContext.add_provider_for_screen(
					Gdk.Screen.get_default(),
					OSDWindow.css_provider,
					Gtk.STYLE_PROVIDER_PRIORITY_USER)
		except GLib.Error, e:
			log.error("Failed to apply css with user settings:")
			log.error(e)
			log.error("Retrying with default values")
			
			OSDWindow.css_provider = Gtk.CssProvider()
			OSDWindow.css_provider.load_from_data(str(OSDWindow.CSS % Config.DEFAULTS['osd_colors']))
			Gtk.StyleContext.add_provider_for_screen(
					Gdk.Screen.get_default(),
					OSDWindow.css_provider,
					Gtk.STYLE_PROVIDER_PRIORITY_USER)
	
	
	def _add_arguments(self):
		""" Should be overriden AND called by child class """
		self.argparser.add_argument('-x', type=int, metavar="pixels", default=20,
			help="""horizontal position in pixels, from left side of screen.
			Use negative value to specify as distance from right side (default: 20)""")
		self.argparser.add_argument('-y', type=int, metavar="pixels", default=-20,
			help="""vertical position in pixels, from top side of screen.
			Use negative value to specify as distance from bottom side (default: -20)""")
		self.argparser.add_argument('-d', action='store_true',
			help="""display debug messages""")
	
	
	def parse_argumets(self, argv):
		""" Returns True on success """
		try:
			self.args = self.argparser.parse_args(argv[1:])
		except BaseException, e:	# Includes SystemExit
			return False
		del self.argparser
		self.position = (self.args.x, self.args.y)
		if self.args.d:
			set_logging_level(True, True)
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
		screen = self.get_window().get_screen()
		geometry = screen.get_monitor_geometry(screen.get_monitor_at_window(screen.get_active_window()))
		x = x + geometry.x
		y = y + geometry.y + geometry.height - self.get_window().get_height()
		if x < 0:	# Negative X position is counted from right border
			x = Gdk.Screen.width() - self.get_allocated_width() + x + 1
		if y < 0:	# Negative Y position is counted from bottom border
			y = Gdk.Screen.height() - self.get_allocated_height() + y + 1
		
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


class StickController(GObject.GObject, TimerManager):
	"""
	Simple utility class that gets fed by with position and emits
	'direction' signal that can be used as input for menu navigation.
	
	Signals:
	  direction(horisontal, vertical)
	  
	  Both values are one of -1, 0, 1 for left/none/right.
	"""
	__gsignals__ = {
			b"direction"			: (GObject.SIGNAL_RUN_FIRST, None, (int, int)),
	}
	REPEAT_DELAY = 0.3
	
	def __init__(self):
		GObject.GObject.__init__(self)
		TimerManager.__init__(self)
		self._d = [ 0, 0 ]
	
	
	def _move(self, *a):
		self.emit("direction", *self._d)
		if any(self._d):
			self.timer("move", self.REPEAT_DELAY, self._move)
		else:
			self.cancel_timer("move")
	
	
	def set_stick(self, *data):
		changed = False
		for i in (0, 1):
			if data[i] < STICK_PAD_MIN / 3 and self._d[i] != 1:
				self._d[i] = 1
				changed = True
			elif data[i] > STICK_PAD_MAX / 3 and self._d[i] != -1:
				self._d[i] = -1
				changed = True
			elif data[i] < STICK_PAD_MAX / 3 and data[i] > STICK_PAD_MIN / 3 and self._d[i] != 0:
				self._d[i] = 0
				changed = True
		
		if changed:
			self._move()
