#!/usr/bin/env python2
"""
SC-Controller - OSD Launcher

Display launcher with phone-like keyboard that user can use to select
application (list is generated using xdg) and start it.

Reuses styles from OSD Menu and OSD Dialog
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gio, Gdk, GdkX11, GdkPixbuf, Pango
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX, SCButtons
from scc.constants import LEFT, RIGHT, SAME, STICK
from scc.paths import get_share_path, get_config_path
from scc.menu_data import MenuData, MenuItem
from scc.tools import point_in_gtkrect
from scc.lib import xwrappers as X
from scc.config import Config
from scc.gui.svg_widget import SVGWidget, SVGEditor
from scc.gui.daemon_manager import DaemonManager
from scc.osd.timermanager import TimerManager
from scc.osd import OSDWindow
import os, sys, re, logging
log = logging.getLogger("osd.binds")


class BindingDisplay(OSDWindow, TimerManager):
	
	def __init__(self, config=None):
		self.bdisplay = os.path.join(get_config_path(), 'binding-display.svg')
		if not os.path.exists(self.bdisplay):
			# Prefer image in ~/.config/scc, but load default one as fallback
			self.bdisplay = os.path.join(get_share_path(), "images", 'binding-display.svg')
		
		OSDWindow.__init__(self, "osd-keyboard")
		TimerManager.__init__(self)
		self.daemon = None
		self.config = config or Config()
		self.group = None
		self.limits = {}
		self.background = None
		
		self._eh_ids = []
		self._stick = 0, 0
		
		self.c = Gtk.Box()
		self.c.set_name("osd-keyboard-container")
	
	
	def use_daemon(self, d):
		"""
		Allows (re)using already existing DaemonManager instance in same process
		"""
		self.daemon = d
		self._cononect_handlers()
		self.on_daemon_connected(self.daemon)
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('image', type=str, nargs="?",
			default = self.bdisplay, help="keyboard image to use")
	
	
	def compute_position(self):
		"""
		Unlike other OSD windows, this one is scaled to 80% of screen size
		and centered in on active screen.
		"""
		x, y = 10, 10
		iw, ih = self.background.image_width, self.background.image_height
		geometry = self.get_active_screen_geometry()
		if geometry:
			width, height = iw, ih
			if width > geometry.width * 0.8:
				width = geometry.width * 0.8
				height = int(float(ih) / float(iw) * float(width))
				self.background.resize(width, height)
				self.background.hilight({})
			x = geometry.x + ((geometry.width - width) / 2)
			y = geometry.y + ((geometry.height - height) / 2)
		return x, y	
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		return True
	
	
	def _cononect_handlers(self):
		self._eh_ids += [
			( self.daemon, self.daemon.connect('dead', self.on_daemon_died) ),
			( self.daemon, self.daemon.connect('error', self.on_daemon_died) ),
			( self.daemon, self.daemon.connect('alive', self.on_daemon_connected) ),
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
			log.info("Sucessfully locked input")
			pass
		
		c = self.choose_controller(self.daemon)
		if c is None or not c.is_connected():
			# There is no controller connected to daemon
			self.on_failed_to_lock("Controller not connected")
			return
		
		self._eh_ids += [ (c, c.connect('event', self.on_event)) ]
		# Lock everything
		locks = [ LEFT, RIGHT, STICK, "STICKPRESS" ] + [ b.name for b in SCButtons ]
		c.lock(success, self.on_failed_to_lock, *locks)
	
	
	def quit(self, code=-1):
		if self.get_controller():
			self.get_controller().unlock_all()
		for source, eid in self._eh_ids:
			source.disconnect(eid)
		self._eh_ids = []
		OSDWindow.quit(self, code)
	
	
	def show(self, *a):
		if self.background is None:
			self.realize()
			self.background = SVGWidget(self, self.args.image, init_hilighted=True)
			self.c.add(self.background)
			self.add(self.c)
		OSDWindow.show(self, *a)
		self.move(*self.compute_position())
	
	
	def on_event(self, daemon, what, data):
		"""
		Called when button press, button release or stick / pad update is
		send by daemon.
		"""
		pass


def main():
	m = BindingDisplay()
	if not m.parse_argumets(sys.argv):
		sys.exit(1)
	m.run()
	sys.exit(m.get_exit_code())


if __name__ == "__main__":
	from scc.tools import init_logging
	init_logging()
	main()
