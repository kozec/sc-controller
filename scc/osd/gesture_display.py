#!/usr/bin/env python2
"""
SC-Controller - Grid OSD Menu

Works as OSD menu, but displays item in (as rectangluar as possible - and
that's usually not very much) grid.
"""

from scc.tools import _, set_logging_level

from gi.repository import Gtk, GObject
from scc.gui.daemon_manager import DaemonManager
from scc.gui.gestures import GestureDraw
from scc.constants import LEFT, RIGHT, CPAD
from scc.config import Config
from scc.osd import OSDWindow
from scc.gestures import GestureDetector
BOTH = "BOTH"

import logging
log = logging.getLogger("osd.gesture")


class GestureDisplay(OSDWindow):
	"""
	OSD Window that displays gesture as it is being generated.
	
	Signals:
	  gesture-updated(gesture)		Emited repeadedly while gesture is being drawn.
	  								May be emited multiple times with same gesture.
	"""
	
	EPILOG="""Exit codes:
   0  - clean exit, user created gesture
  -1  - clean exit, user canceled gesture
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon, sc-daemon reported error or died while menu is displayed.
   3  - erorr, failed to lock input
	"""
	__gsignals__ = {
		b"gesture-updated"                    : (GObject.SignalFlags.RUN_FIRST, None, (str,)),
	}

	SIZE = 128	# times two horizontaly + borders
	
	def __init__(self, config=None):
		OSDWindow.__init__(self, "osd-gesture")
		self.daemon = None
		self._left_detector  = GestureDetector(0, self._on_gesture_finished)
		# self._right_detector = GestureDetector(0, self._on_gesture_finished)
		self._control_with = LEFT
		self._eh_ids = []
		self._gesture = None
		
		self.setup_widgets()
		self.use_config(config or Config())
	
	
	def setup_widgets(self):
		self.parent = Gtk.Grid()
		self.parent.set_name("osd-gesture")
		
		self._left_draw  = GestureDraw(self.SIZE, self._left_detector)
		# self._right_draw = GestureDraw(self.SIZE, self._right_detector)
		sep = Gtk.VSeparator()
		sep.set_name("osd-gesture-separator")
		
		self.parent.attach(self._left_draw,  0, 0, 1, 1)
		# self.parent.attach(sep,              1, 0, 1, 1)
		# self.parent.attach(self._right_draw, 2, 0, 1, 1)
		
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
		# for x in (self._left_draw, self._right_draw):
		for x in (self._left_draw, ):
			x.set_colors(**self.config["gesture_colors"])
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('--control-with', '-c', type=str,
			metavar="option", default=LEFT, choices=(LEFT, RIGHT, CPAD),
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
	
	
	def on_daemon_connected(self, *a):
		def success(*a):
			log.error("Sucessfully locked %s pad", self._control_with)
			self._left_detector.enable()
			# self._right_detector.enable()
		
		if not self.config:
			self.config = Config()
		locks = [ self._control_with ]
		c = self.choose_controller(self.daemon)
		if c is None or not c.is_connected():
			# There is no controller connected to daemon
			self.on_failed_to_lock("Controller not connected")
			return
		
		self._eh_ids += [
			(c, c.connect('event', self.on_event)),
			(c, c.connect('lost', self.on_controller_lost)),
		]
		c.lock(success, self.on_failed_to_lock, *locks)
	
	
	def quit(self, code=-2):
		if self.get_controller():
			self.get_controller().unlock_all()
		for source, eid in self._eh_ids:
			source.disconnect(eid)
		self._eh_ids = []
		OSDWindow.quit(self, code)
	
	
	def on_event(self, daemon, what, data):
		if what == self._control_with:
			x, y = data
			self._left_draw.add(x, y)
			self._left_detector.whole(None, x, y, what)
			# TODO: self._right_detector, if there is any use for it later
			self.emit('gesture-updated', self._left_detector.get_string())
	
	
	def get_gesture(self):
		""" Returns recognized gesture or None if there is not any """
		if self._gesture:
			return self._gesture
		# self._gesture is None or empty
		return None
	
	
	def _on_gesture_finished(self, detector, gesture):
		self._gesture = gesture
		log.debug("Recognized gesture: %s", gesture)
		self.quit(0)


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
		print(gd.get_gesture())
	else:
		sys.exit(gd.get_exit_code())


if __name__ == "__main__":
	import os, sys, signal

	def sigint(*a):
		print("\n*break*")
		sys.exit(-1)
	
	signal.signal(signal.SIGINT, sigint)
	main()
