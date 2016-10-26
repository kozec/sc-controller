#!/usr/bin/env python2
"""
SC-Controller - Grid OSD Menu

Works as OSD menu, but displays item in (as rectangluar as possible - and
that's usually not very much) grid.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk
from scc.constants import LEFT, RIGHT, STICK_PAD_MIN, STICK_PAD_MAX
from scc.gui.daemon_manager import DaemonManager
from scc.config import Config
from scc.osd import OSDWindow
from scc.gestures import GestureDetector
from collections import deque
BOTH = "BOTH"

import math, logging
log = logging.getLogger("osd.gesture")


class GestureDisplay(OSDWindow):
	EPILOG="""Exit codes:
   0  - clean exit, user created gesture
  -1  - clean exit, user canceled gesture
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon, sc-daemon reported error or died while menu is displayed.
   3  - erorr, failed to lock input
	"""
	
	SIZE = 128	# times two horizontaly + borders
	
	def __init__(self, config=None):
		OSDWindow.__init__(self, "osd-gesture")
		self.daemon = None
		self._left_detector  = GestureDetector(0, self._on_gesture_finished)
		self._right_detector = GestureDetector(0, self._on_gesture_finished)
		self._control_with = LEFT
		self._eh_ids = []
		self._gesture = None
		
		self.setup_widgets()
		self.use_config(config or Config())
	
	
	def setup_widgets(self):
		self.parent = Gtk.Grid()
		self.parent.set_name("osd-gesture")
		
		self._left_draw  = GestureDraw(self.SIZE, self._left_detector)
		self._right_draw = GestureDraw(self.SIZE, self._right_detector)
		sep = Gtk.VSeparator()
		sep.set_name("osd-gesture-separator")
		
		self.parent.attach(self._left_draw,  0, 0, 1, 1)
		self.parent.attach(sep,              1, 0, 1, 1)
		self.parent.attach(self._right_draw, 2, 0, 1, 1)
		
		self.add(self.parent)
	
	
	def use_daemon(self, d):
		"""
		Allows (re)using already existing DaemonManager instance in same process.
		If this is used, parse_argumets() should be called before.
		"""
		self.daemon = d
		self.on_daemon_connected()
	
	
	def use_config(self, c):
		"""
		Allows reusing already existin Config instance in same process.
		Has to be called before parse_argumets()
		"""
		self.config = c
		for x in (self._left_draw, self._right_draw):
			x.set_colors(**self.config["gesture_colors"])
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('--control-with', '-c', type=str,
			metavar="option", default=LEFT, choices=(LEFT, RIGHT),
			help="which pad should be used to generate gesture menu (default: %s)" % (LEFT,))
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		if not self.config:
			self.use_config(Config())
		
		# Parse simpler arguments
		self._control_with = self.args.control_with
		
		return True
	
	
	def _connect_handlers(self):
		self._eh_ids += [
			(self.daemon, self.daemon.connect('dead', self.on_daemon_died)),
			(self.daemon, self.daemon.connect('error', self.on_daemon_died)),
			(self.daemon, self.daemon.connect('alive', self.on_daemon_connected)),
		]
	
	
	def run(self):
		self.daemon = DaemonManager()
		self._connect_handlers()
		OSDWindow.run(self)
	
	
	def show(self, *a):
		OSDWindow.show(self, *a)
	
	
	def on_daemon_died(self, *a):
		log.error("Daemon died")
		self.quit(2)
	
	
	def on_failed_to_lock(self, error):
		log.error("Failed to lock input: %s", error)
		self.quit(3)
	
	
	def on_daemon_connected(self, *a):
		def success(*a):
			log.error("Sucessfully locked input")
			self._left_detector.enable()
			self._right_detector.enable()
		
		if not self.config:
			self.config = Config()
		locks = [ self._control_with ]
		c = self.choose_controller(self.daemon)
		if c is None or not c.is_connected():
			# There is no controller connected to daemon
			self.on_failed_to_lock("Controller not connected")
			return
		self._eh_ids += [ (c, c.connect('event', self.on_event)) ]
		c.lock(success, self.on_failed_to_lock, *locks)
	
	
	def quit(self, code=-2):
		if self.get_controller():
			self.get_controller().unlock_all()
		for source, eid in self._eh_ids:
			source.disconnect(eid)
		self._eh_ids = []
		OSDWindow.quit(self, code)
	
	
	def on_event(self, daemon, what, data):
		if what == LEFT:
			x, y = data
			self._left_draw.add(x, y)
			self._left_detector.whole(None, x, y, LEFT)
		elif what == RIGHT:
			x, y = data
			self._right_detector.whole(None, x, y, RIGHT)
	
	
	def get_gesture(self):
		""" Returns recognized gesture or None if there is not any """
		return self._gesture
	
	
	def _on_gesture_finished(self, detector, gesture):
		self._gesture = gesture
		log.debug("Recognized gesture: %s", gesture)
		self.quit(0)


class GestureDraw(Gtk.DrawingArea):
	GRID_PAD = 10
	MAX_STEPS = 3
	LINE_ALPHA = 0.3;
	def __init__(self, size, detector):
		Gtk.DrawingArea.__init__(self)
		self._size = size
		self._detector = detector
		self._points = deque([], 256)
		self.connect('draw', self.draw)
		self.set_size_request(size, size)
		self.set_colors()
	
	
	@staticmethod
	def parse_rgba(col):
		""" Parses color specified by #RRGGBBAA string """
		# Because GTK can parse everything but theese :(
		if not col.startswith("#"):
			col = "#" + col
		if len(col) > 7:
			col, alpha = col[0:7], col[7:]
		rgba = Gdk.RGBA()
		if not rgba.parse(col):
			log.warning("Failed to parse RGBA color: %s", col)
		rgba.alpha = float(int(alpha, 16)) / 255.0
		return rgba
	
	
	def set_colors(self, background="000000FF", line="FF00FFFF",
			grid="7A7A7AFF", hilight="0030AAFF", **a):
		""" Expects colors in RRGGBB, as stored in config file """
		self.colors = {
			'background' :	GestureDraw.parse_rgba(background),
			'line' : 		GestureDraw.parse_rgba(line),
			'grid' : 		GestureDraw.parse_rgba(grid),
			'hilight':		GestureDraw.parse_rgba(hilight),
		}
	
	
	def add(self, x, y):
		factor = self._size / float(STICK_PAD_MAX - STICK_PAD_MIN)
		x -= STICK_PAD_MIN
		y = STICK_PAD_MAX - y
		self._points.append(( x * factor, y * factor ))
		self.queue_draw()
	
	
	def draw(self, another_self, cr):
		resolution = self._detector.get_resolution()
		hilights = { x : 0 for x in GestureDetector.CHARS }

		# Background
		Gdk.cairo_set_source_rgba(cr, self.colors['background'])
		cr.rectangle(0, 0, self._size, self._size)
		cr.fill()
		
		# Hilighted boxes
		# Iterates over gesture in progress hilighting apripriate boxes,
		# so user can see what's he doing.
		box_width = float(self._size) / float(resolution)
		col = self.colors['hilight']
		alpha = col.alpha
		alpha_fallout = alpha * 0.5 / self.MAX_STEPS
		step = 0
		for char in reversed(self._detector.get_string()):
			if step > self.MAX_STEPS or char == self._detector.SEPARATOR:
				break
			x, y = self._detector.char_to_xy(char)
			col.alpha = alpha - alpha_fallout * step
			Gdk.cairo_set_source_rgba(cr, col)
			cr.rectangle(box_width * x, box_width * y, box_width, box_width)
			cr.fill()
			step += 1
		col.alpha = alpha
		
		# Grid
		Gdk.cairo_set_source_rgba(cr, self.colors['grid'])
		for i in xrange(1, resolution):
			cr.move_to(i * box_width, self.GRID_PAD)
			cr.line_to(i * box_width, self._size - self.GRID_PAD)
			cr.stroke()
			cr.move_to(self.GRID_PAD, i * box_width)
			cr.line_to(self._size - self.GRID_PAD, i * box_width)
			cr.stroke()
		
		# Line
		Gdk.cairo_set_source_rgba(cr, self.colors['line'])
		drawing = False
		for x, y in self._points:
			if drawing:
				cr.line_to(x, y)
			else:
				cr.move_to(x, y)
				drawing = True
		if drawing:
			cr.stroke()


def main():
	import gi
	gi.require_version('Gtk', '3.0')
	gi.require_version('Rsvg', '2.0')
	gi.require_version('GdkX11', '3.0')
	
	from scc.tools import init_logging
	from scc.paths import get_share_path
	init_logging()
	
	gd = GestureDisplay()
	if not gd.parse_argumets(sys.argv):
		sys.exit(1)
	gd.run()
	if gd.get_exit_code() == 0:
		print gd.get_gesture()
	else:
		sys.exit(gd.get_exit_code())


if __name__ == "__main__":
	import os, sys, signal

	def sigint(*a):
		print("\n*break*")
		sys.exit(-1)
	
	signal.signal(signal.SIGINT, sigint)
	main()
