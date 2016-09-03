#!/usr/bin/env python2
"""
SC-Controller - scc-osd-display-input

Displays pressed buttons, axes values and other inputs in OSD.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Rsvg', '2.0')
gi.require_version('GdkX11', '3.0')

from gi.repository import Gtk, GLib
from scc.constants import SCButtons, STICK, STICK_PAD_MAX
from scc.config import Config
from scc.gui.daemon_manager import DaemonManager
from scc.osd.message import Message
from scc.osd import OSDWindow

import os, sys, logging, time
log = logging.getLogger("osd.daemon")

class OSDDisplayInput(object):
	SPACING = 75
	
	def __init__(self, imagepath="/usr/share/scc/images"):
		self.exit_code = -1
		self.mainloop = GLib.MainLoop()
		self.config = Config()
		self.daemon = None
		self.imagepath = imagepath
		
		self._positions = {}
		self._buttons = None
		
		OSDWindow._apply_css(self.config)
	
	
	def get_exit_code(self):
		return self.exit_code
	
	
	def on_daemon_died(self, *a):
		log.error("Connection to daemon lost")
		self.quit(2)
	
	
	def on_observe_failed(self, *a):
		# TODO: Better message with explanation?
		log.error("Failed to lock inputs")
		self.quit(1)
	
	
	def on_daemon_connected(self, *a):
		self.daemon.observe(DaemonManager.nocallback, self.on_observe_failed,
			'A', 'B', 'C', 'X', 'Y', 'START', 'BACK', 'LB', 'RB',
			'LPAD', 'RPAD', 'LGRIP', 'RGRIP', 'LT', 'RT', 'LEFT',
			'RIGHT', 'STICK', 'STICKPRESS')
	
	
	def on_event(self, daemon, what, data):
		if hasattr(SCButtons, what):
			if self._buttons is None:
				self._buttons = ButtonDisplay(self)
				self._buttons.enable(what)
				self.show_display(self._buttons)
			if data[0] == 1:	# Pressed
				self._buttons.enable(what)
			else:				# Released
				self._buttons.disable(what)
			print what, data[0]
	
	
	def show_display(self, d):
		pos = 0
		while pos in self._positions:
			pos += 1
		self._positions[pos] = d
		d.position = 20, - 20 - OSDDisplayInput.SPACING * pos
		print d.position
		d.show()
	
	
	def remove_display(self, d):
		""" Called after InputDisplay window is hidden """
		if self._buttons == d:
			self._buttons = None
		for x in self._positions:
			if self._positions[x] == d:
				del self._positions[x]
				break
	
	
	def run(self):
		self.daemon = DaemonManager()
		self.daemon.connect('alive', self.on_daemon_connected)
		self.daemon.connect('dead', self.on_daemon_died)
		self.daemon.connect("event", self.on_event)
		self.mainloop.run()


class InputDisplay(OSDWindow):
	def __init__(self, *children):
		OSDWindow.__init__(self, "osd-input-display")
		self.timeout = 5
		self.children = []
		self.box = Gtk.Box()
		OSDWindow.add(self, self.box)
		for c in children:
			self.add(c)
	
	
	def show(self):
		OSDWindow.show(self)
		GLib.timeout_add_seconds(self.timeout, self.hide)
	
	
	def add(self, c):
		self.children.append(c)
		self.box.pack_start(c, False, False, 1)
		self.box.show_all()


class ButtonDisplay(InputDisplay):
	def __init__(self, parent):
		InputDisplay.__init__(self)
		self.parent = parent
		self.buttons = {}
	
	
	def hide(self):
		for b in self.buttons:
			if self.buttons[b].get_name() != "released":
				GLib.timeout_add_seconds(self.timeout, self.hide)
				return
		self.parent.remove_display(self)
		InputDisplay.hide(self)
		self.destroy()
	
	
	def enable(self, what):
		if not what in self.buttons:
			filename = os.path.join(self.parent.imagepath, "%s_OSI.svg" % (what,))
			i = Gtk.Image.new_from_file(filename)
			self.buttons[what] = i
			self.add(i)
			self.show_all()
		self.buttons[what].set_name("")
	
	
	def disable(self, what):
		if what in self.buttons:
			self.buttons[what].set_name("released")


if __name__ == "__main__":
	from scc.tools import init_logging, set_logging_level
	from scc.paths import get_share_path
	init_logging(suffix=" OSI")
	set_logging_level('debug' in sys.argv, 'debug' in sys.argv)
	
	d = OSDDisplayInput(imagepath="./images")
	d.run()
	sys.exit(d.get_exit_code())
