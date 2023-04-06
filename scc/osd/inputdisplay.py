#!/usr/bin/env python2
"""
SC-Controller - Input Display
"""

from scc.tools import _, set_logging_level

from gi.repository import Gtk, GLib
from scc.constants import SCButtons, STICK, LEFT, RIGHT, STICK_PAD_MAX
from scc.gui.daemon_manager import DaemonManager
from scc.gui.svg_widget import SVGWidget
from scc.osd import OSDWindow

import os, sys, logging, signal, argparse
log = logging.getLogger("osd.InputDisplay")


class InputDisplay(OSDWindow):
	IMAGE = "inputdisplay.svg"
	HILIGHT_COLOR = "#FF00FF00"		# ARGB
	OBSERVE_COLOR = "#00007FFF"		# ARGB
	
	def __init__(self, imagepath="/usr/share/scc/images"):
		OSDWindow.__init__(self, "osd-menu")
		self.daemon = None
		self.config = None
		self.hilights = { self.HILIGHT_COLOR : set(), self.OBSERVE_COLOR : set() }
		self.imagepath = imagepath
		
		self._eh_ids = []
	
	
	def show(self):
		self.main_area = Gtk.Fixed()
		self.background = SVGWidget(os.path.join(self.imagepath, self.IMAGE))
		self.lpadTest = Gtk.Image.new_from_file(os.path.join(self.imagepath, "inputdisplay-cursor.svg"))
		self.rpadTest = Gtk.Image.new_from_file(os.path.join(self.imagepath, "inputdisplay-cursor.svg"))
		self.stickTest = Gtk.Image.new_from_file(os.path.join(self.imagepath, "inputdisplay-cursor.svg"))
		
		self.main_area.set_property("margin-left", 10)
		self.main_area.set_property("margin-right", 10)
		self.main_area.set_property("margin-top", 10)
		self.main_area.set_property("margin-bottom", 10)
		
		self.main_area.put(self.background, 0, 0)
		self.main_area.put(self.lpadTest, 40, 40)
		self.main_area.put(self.rpadTest, 290, 90)
		self.main_area.put(self.stickTest, 150, 40)
		
		self.add(self.main_area)
		
		OSDWindow.show(self)
		self.lpadTest.hide()
		self.rpadTest.hide()
		self.stickTest.hide()
	
	
	def run(self):
		self.daemon = DaemonManager()
		self._connect_handlers()
		OSDWindow.run(self)
	
	
	def use_daemon(self, d):
		"""
		Allows (re)using already existing DaemonManager instance in same process.
		use_config() should be be called before parse_argumets() if this is used.
		"""
		self.daemon = d
		self._connect_handlers()
		self.on_daemon_connected(self.daemon)	
	
	
	def _connect_handlers(self):
		self._eh_ids += [
			(self.daemon, self.daemon.connect('dead', self.on_daemon_died)),
			(self.daemon, self.daemon.connect('error', self.on_daemon_died)),
			(self.daemon, self.daemon.connect('alive', self.on_daemon_connected)),
		]
	
	
	def on_daemon_connected(self, *a):
		c = self.daemon.get_controllers()[0]
		c.unlock_all()
		c.observe(DaemonManager.nocallback, self.on_observe_failed,
			'A', 'B', 'C', 'X', 'Y', 'START', 'BACK', 'LB', 'RB',
			'LPAD', 'RPAD', 'LGRIP', 'RGRIP', 'LT', 'RT', 'LEFT',
			'RIGHT', 'STICK', 'STICKPRESS')	
		c.connect('event', self.on_daemon_event_observer)
		c.connect('lost', self.on_controller_lost)
	
	
	def on_observe_failed(self, error):
		log.error("Failed to enable test mode: %s", error)
		if "Sniffing" in error:
			log.error("")
			log.error("=================================================================================")
			log.error("[!!] Please, enable 'Input Test Mode' on 'Advanced' tab in SC-Controller settings")
			log.error("=================================================================================")
		self.quit(3)
	
	
	def on_daemon_event_observer(self, daemon, what, data):
		if what in (LEFT, RIGHT, STICK):
			widget, area = {
				LEFT  : (self.lpadTest,  "LPADTEST"),
				RIGHT : (self.rpadTest,  "RPADTEST"),
				STICK : (self.stickTest, "STICKTEST"),
			}[what]
			# Check if stick or pad is released
			if data[0] == data[1] == 0:
				widget.hide()
				return
			if not widget.is_visible():
				widget.show()
			# Grab values
			ax, ay, aw, trash = self.background.get_area_position(area)
			cw = widget.get_allocation().width
			# Compute center
			x, y = ax + aw * 0.5 - cw * 0.5, ay + 1.0 - cw * 0.5
			# Add pad position
			x += data[0] * aw / STICK_PAD_MAX * 0.5
			y -= data[1] * aw / STICK_PAD_MAX * 0.5
			# Move circle
			self.main_area.move(widget, x, y)
		elif what in ("LT", "RT", "STICKPRESS"):
			what = {
				"LT" : "LEFT",
				"RT" : "RIGHT",
				"STICKPRESS" : "STICK"
			}[what]
			if data[0]:
				self.hilights[self.OBSERVE_COLOR].add(what)
			else:
				self.hilights[self.OBSERVE_COLOR].remove(what)
			self._update_background()
		elif hasattr(SCButtons, what):
			try:
				if data[0]:
					self.hilights[self.OBSERVE_COLOR].add(what)
				else:
					self.hilights[self.OBSERVE_COLOR].remove(what)
				self._update_background()
			except KeyError as e:
				# Non fatal
				pass
		else:
			print("event", what)
	
	
	def _update_background(self):
		h = {}
		for color in self.hilights:
			for i in self.hilights[color]:
				h[i] = color
		self.background.hilight(h)



def sigint(*a):
	print("\n*break*")
	sys.exit(0)


if __name__ == "__main__":
	signal.signal(signal.SIGINT, sigint)

	import gi
	gi.require_version('Gtk', '3.0')
	gi.require_version('Rsvg', '2.0')
	gi.require_version('GdkX11', '3.0')
	
	from scc.tools import init_logging
	from scc.paths import get_share_path
	init_logging()
	
	m = InputDisplay()
	if not m.parse_argumets(sys.argv):
		sys.exit(1)
	m.run()
	sys.exit(m.get_exit_code())
