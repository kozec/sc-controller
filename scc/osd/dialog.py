#!/usr/bin/env python2
"""
SC-Controller - OSD Dialog

Display dialog with text and set of items that user can navigate through and
prints chosen item id to stdout
"""


from gi.repository import Gtk, GdkX11
from scc.gui.daemon_manager import DaemonManager
from scc.osd import OSDWindow, StickController
from scc.lib import xwrappers as X
from scc.constants import DEFAULT, STICK
from scc.menu_data import MenuData
from scc.config import Config

import sys, logging
log = logging.getLogger("osd.dialog")


class Dialog(OSDWindow):
	EPILOG="""Exit codes:
   0  - clean exit, user selected option
  -1  - clean exit, user canceled dialog
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon, sc-daemon reported error or died while dialog is displayed.
   3  - erorr, failed to lock input stick, pad or button(s)
	"""
	
	def __init__(self, cls="osd-menu"):
		self._buttons = None
		self._text = None
		
		OSDWindow.__init__(self, cls)
		self.daemon = None
		self.config = None
		self.feedback = None
		self.controller = None
		self.xdisplay = X.Display(hash(GdkX11.x11_get_default_xdisplay()))	# Magic
		
		self.parent = self.create_parent()
		self.f = Gtk.Fixed()
		self.f.add(self.parent)
		self.add(self.f)
		
		self._scon = StickController()
		self._scon.connect("direction", self.on_stick_direction)
		self._selected = None
		self._eh_ids = []
	
	
	def create_parent(self):
		self._text = Gtk.Label()
		self._buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		dialog = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		dialog.pack_start(self._text, True, True, 0)
		dialog.pack_start(self._buttons, True, True, 0)
		
		dialog.set_name("osd-dialog")
		self._buttons.set_name("osd-dialog-buttons")
		self._text.set_name("osd-dialog-text")
		return dialog
	
	
	def pack_items(self, parent, items):
		for item in items:
			if hasattr(item.widget, "set_alignment"):
				item.widget.set_alignment(0.5, 0.5)
			self._buttons.pack_end(item.widget, True, True, 0)
	
	
	def use_daemon(self, d):
		"""
		Allows (re)using already existing DaemonManager instance in same process.
		use_config() should be be called before parse_argumets() if this is used.
		"""
		self.daemon = d
		self._connect_handlers()
		self.on_daemon_connected(self.daemon)
	
	
	def use_config(self, c):
		"""
		Allows reusing already existin Config instance in same process.
		Has to be called before parse_argumets()
		"""
		self.config = c
	
	
	def get_menuid(self):
		# Just to be compatibile with menus when called from scc-osd-daemon
		return None
	
	
	def get_selected_item_id(self):
		"""
		Returns ID of selected item or None if nothing is selected.
		"""
		if self._selected:
			return self._selected.id
		return None
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('--confirm-with', type=str,
			metavar="button", default=DEFAULT,
			help="button used to confirm choice")
		self.argparser.add_argument('--cancel-with', type=str,
			metavar="button", default=DEFAULT,
			help="button used to cancel dialog")
		self.argparser.add_argument('--feedback-amplitude', type=int,
			help="enables and sets power of feedback effect generated when active menu option is changed")
		self.argparser.add_argument('--text', type=str, metavar='text',
			help="Dialog text")
		self.argparser.add_argument('items', type=str, nargs='*', metavar='id text',
			help="Dialog buttons")
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		if not self.config:
			self.config = Config()
		
		try:
			self.items = MenuData.from_args(self.args.items)
			self._menuid = None
		except ValueError:
			print('%s: error: invalid number of arguments' % (sys.argv[0]), file=sys.stderr)
			return False
		
		self._text.set_label(self.args.text)
		
		if self.args.feedback_amplitude:
			side = "LEFT"
			self.feedback = side, int(self.args.feedback_amplitude)
		
		# Create buttons that are displayed on screen
		items = self.items.generate(self)
		self.items = []
		for item in items:
			item.widget = self.generate_widget(item)
			if item.widget is not None:
				self.items.append(item)
		self.pack_items(self.parent, self.items)
		if len(self.items) == 0:
			print('%s: error: no items in menu' % (sys.argv[0]), file=sys.stderr)
			return False
		
		return True
	
	
	def generate_widget(self, item):
		""" Generates gtk widget for specified menutitem """
		widget = Gtk.Button.new_with_label(item.label)
		widget.set_relief(Gtk.ReliefStyle.NONE)
		if hasattr(widget.get_children()[0], "set_xalign"):
			widget.get_children()[0].set_xalign(0)
		else:
			widget.get_children()[0].set_halign(Gtk.Align.START)
		widget.set_name("osd-menu-item")
		
		return widget
	
	
	def select(self, index):
		if self._selected:
			self._selected.widget.set_name(self._selected.widget.get_name()
				.replace("-selected", ""))
		if self.items[index].id:
			if self._selected != self.items[index]:
				if self.feedback and self.controller:
					self.controller.feedback(*self.feedback)
			self._selected = self.items[index]
			self._selected.widget.set_name(
					self._selected.widget.get_name() + "-selected")
			return True
		return False
	
	
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
		if not self.select(0):
			self.next_item(1)
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
		
		if not self.config:
			self.config = Config()
		self.controller = self.choose_controller(self.daemon)
		if self.controller is None or not self.controller.is_connected():
			# There is no controller connected to daemon
			self.on_failed_to_lock("Controller not connected")
			return
		
		ccfg = self.config.get_controller_config(self.controller.get_id())
		self._control_with = ccfg["menu_control"]
		self._confirm_with = ccfg["menu_confirm"] if self.args.confirm_with == DEFAULT else self.args.confirm_with
		self._cancel_with = ccfg["menu_cancel"] if self.args.cancel_with == DEFAULT else self.args.cancel_with
		
		self._eh_ids += [ (self.controller, self.controller.connect('event', self.on_event)) ]
		locks = [ self._control_with, self._confirm_with, self._cancel_with ]
		self.controller.lock(success, self.on_failed_to_lock, *locks)
	
	
	def quit(self, code=-2):
		if self.get_controller():
			self.get_controller().unlock_all()
		for source, eid in self._eh_ids:
			source.disconnect(eid)
		self._eh_ids = []
		OSDWindow.quit(self, code)
	
	
	def next_item(self, direction):
		""" Selects next menu item, based on self._direction """
		start, i = -1, 0
		try:
			start = self.items.index(self._selected)
			i = start + direction
		except: pass
		while True:
			if i == start:
				# Cannot find valid menu item
				self.select(start)
				break
			if i >= len(self.items):
				i = 0
				continue
			if i < 0:
				i = len(self.items) - 1
				continue
			if self.select(i): break
			i += direction
			if start < 0: start = 0
	
	
	def on_stick_direction(self, trash, x, y):
		if x != 0:
			self.next_item(x)
	
	
	def on_event(self, daemon, what, data):
		if what == self._control_with:
			self._scon.set_stick(*data)
		elif what == self._cancel_with:
			if data[0] == 0:	# Button released
				self.quit(-1)
		elif what == self._confirm_with:
			if data[0] == 0:	# Button released
				if self._selected and self._selected.callback:
					self._selected.callback(self, self.daemon, self.controller, self._selected)
				elif self._selected:
					self.quit(0)
				else:
					self.quit(-1)
