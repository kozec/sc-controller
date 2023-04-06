#!/usr/bin/env python2
"""
SC-Controller - OSD Launcher

Display launcher with phone-like keyboard that user can use to select
application (list is generated using xdg) and start it.

Reuses styles from OSD Menu and OSD Dialog
"""

from scc.tools import _

from gi.repository import Gtk, Gio, GdkX11, Pango
from scc.constants import STICK_PAD_MAX, DEFAULT, LEFT, RIGHT, STICK
from scc.tools import point_in_gtkrect, circle_to_square, clamp
from scc.gui.daemon_manager import DaemonManager
from scc.osd import OSDWindow, StickController
from scc.paths import get_share_path
from scc.lib import xwrappers as X
from scc.config import Config

import os, logging
log = logging.getLogger("osd.menu")


class Launcher(OSDWindow):
	EPILOG="""Exit codes:
   0  - clean exit, user selected option
  -1  - clean exit, user canceled dialog
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon, sc-daemon reported error or died while dialog is displayed.
   3  - erorr, failed to lock input stick, pad or button(s)
	"""
	
	BUTTONS = [
		"1",	 	"2 ABC",	"3 DEF",
		"5 GHI", 	"5 JKL",	"6 MNO",
		"7 PQRS",	"8 TUV",	"9 WXYZ",
		"", 		"0"
	]
	
	VALID_CHARS = "12ABC3DEF5GHI5JKL6MNO7PQRS8TUV9WXYZ0"
	CHAR_TO_NUMBER = { }	# Generated on runtime
	
	MAX_ROWS = 5
	
	_app_db = None	# Static list of all know applications
	
	def __init__(self, cls="osd-menu"):
		self._buttons = None
		self._string = ""
		
		OSDWindow.__init__(self, cls)
		self.daemon = None
		self.config = None
		self.feedback = None
		self.controller = None
		self.xdisplay = X.Display(hash(GdkX11.x11_get_default_xdisplay()))	# Magic
		
		self.create_parent()
		self.create_app_list()
		self.create_buttons()
		
		cursor = os.path.join(get_share_path(), "images", 'menu-cursor.svg')
		self.cursors = [ Gtk.Image.new_from_file(cursor), Gtk.Image.new_from_file(cursor) ]
		for c in self.cursors:
			c.set_name("osd-menu-cursor")
			c.selected = None
			self.f.add(c)
		self.f.show_all()
		
		self._scon = StickController()
		self._scon.connect("direction", self.on_stick_direction)
		self._selected = None
		self._menuid = None
		self._eh_ids = []
		self._confirm_with = 'A'
		self._cancel_with = 'B'
		
		if Launcher._app_db is None:
			Launcher._app_db = []
			for x in Launcher.BUTTONS:
				for c in x:
					Launcher.CHAR_TO_NUMBER[c] = x[0]
			
			for x in Gio.AppInfo.get_all():
				try:
					Launcher._app_db.append(( Launcher.name_to_keys(x), x ))
				except UnicodeDecodeError:
					# Just fuck them...
					pass
	
	
	@staticmethod
	def name_to_keys(appinfo):
		name = "".join([
			Launcher.CHAR_TO_NUMBER[x]
			for x in appinfo.get_display_name().upper()
			if x in Launcher.VALID_CHARS
		])
		return name
	
	
	@staticmethod
	def string_to_keys_and_spaces(string):
		name = "".join([
			Launcher.CHAR_TO_NUMBER[x] if x in Launcher.VALID_CHARS else " "
			for x in string.upper()
		])
		return name
	
	
	def create_parent(self):
		self.parent = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.parent.set_name("osd-dialog")
		self.f = Gtk.Fixed()
		self.f.add(self.parent)
		self.add(self.f)
	
	
	def create_app_list(self):
		lst = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		lst.set_name("osd-application-list")
		self.items = [ self.generate_widget("") for x in range(self.MAX_ROWS) ]
		for a in self.items:
			lst.pack_start(a, False, True, 0)
		self.parent.pack_start(lst, True, True, 0)
		self._set_launchers([  ])
		lst.show_all()
	
	
	def create_buttons(self):
		self.grid = Gtk.Grid()
		self.parent.pack_start(self.grid, True, True, 0)
		self._buttons = []
		
		x, y = 0, 0
		for label in self.BUTTONS:
			if label:
				w = self.generate_widget(label)
				w.set_name("osd-key-buton")
				self.grid.attach(w, x, y, 1, 1)
				self._buttons.append(w)
			x += 1
			if x > 2:
				x = 0
				y += 1
		
		
		w = self.generate_widget(_("Run"))
		self.grid.attach(w, x, y, 1, 1)
		
		
		self.grid.set_name("osd-dialog-buttons")
	
	
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
		"""
		Returns ID of used menu.
		"""
		return None
	
	
	def get_selected_item_id(self):
		"""
		Returns ID of selected item or None if nothing is selected.
		"""
		return None
	
	
	def _launch(self):
		self._selected.launcher.launch()
	
	
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
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		if not self.config:
			self.config = Config()
		
		if self.args.feedback_amplitude:
			side = "LEFT"
			self.feedback = side, int(self.args.feedback_amplitude)
		
		# Create buttons that are displayed on screen
		return True
	
	
	def _set_launchers(self, launchers):
		launchers = launchers[0:self.MAX_ROWS]
		for x in self.items:
			x.set_label("")
			x.set_name("osd-hidden-item")
			x.launcher = None
		for i in range(0, len(launchers)):
			self.items[i].set_name("osd-launcher-item")
			self.items[i].launcher = launchers[i]
			label = self.items[i].get_children()[0]
			label.set_markup(self._format_label_markup(launchers[i]))
			label.set_max_width_chars(1)
			label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
			label.set_xalign(0)
	
	
	def _format_label_markup(self, label):
		if hasattr(label, "get_display_name"):
			label = label.get_display_name()
		else:
			label = str(label)
		
		def _check(substr):
			i, ch = 0, self._string
			while len(substr) > 0 and substr[0] == ch[0]:
				ch = ch[1:]
				substr = substr[1:]
				i += 1
				if len(ch) == 0: return i
			while len(substr) > 0 and substr[0] == " ":
				substr = substr[1:]
				i += 1
			return -1
			
		keys = Launcher.string_to_keys_and_spaces(label)
		index1, index2 = -1, -1
		for i in range(0, len(keys)):
			if keys[i] == self._string[0]:
				index2 = _check(keys[i:])
				if index2 > 0:
					index1 = i
					index2 = i + index2
					break
		
		label = "%s<span color='#%s'>%s</span>%s" % (
			label[0:index1],
			self.config["osd_colors"]["menuitem_hilight_text"],
			label[index1:index2],
			label[index2:]
		)
		return label
	
	
	def _update_items(self):
		if len(self._string) > 0:
			gen = ( item for (keys, item) in self._app_db if self._string in keys )
			launchers = []
			for i in gen:
				launchers.append(i)
				if len(launchers) > self.MAX_ROWS: break
			self._set_launchers(launchers)
			self.select(0)
		else:
			self._set_launchers([])
	
	
	def generate_widget(self, label):
		""" Generates gtk widget for specified menutitem """
		if hasattr(label, "label"): label = label.label
		widget = Gtk.Button.new_with_label(label)
		widget.set_relief(Gtk.ReliefStyle.NONE)
		if hasattr(widget.get_children()[0], "set_xalign"):
			widget.get_children()[0].set_xalign(0)
		else:
			widget.get_children()[0].set_halign(Gtk.Align.START)
		widget.set_name("osd-menu-item")
		
		return widget
	
	
	def select(self, index):
		if self._selected:
			self._selected.set_name(self._selected.get_name()
				.replace("-selected", ""))
			self._selected = None
		if self.items[index].launcher is not None:
			self._selected = self.items[index]
			self._selected.set_name(
					self._selected.get_name() + "-selected")
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
		for c in self.cursors:
			c.set_visible(False)
	
	
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
		self._confirm_with = ccfg["menu_confirm"] if self.args.confirm_with == DEFAULT else self.args.confirm_with
		self._cancel_with = ccfg["menu_cancel"] if self.args.cancel_with == DEFAULT else self.args.cancel_with
		
		self._eh_ids += [
			(self.controller, self.controller.connect('event', self.on_event)),
			(self.controller, self.controller.connect('lost', self.on_controller_lost)),
		]
		locks = [ LEFT, RIGHT, STICK, "LPAD", "RPAD", "LB",
			self._confirm_with, self._cancel_with ]
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
		if y != 0:
			self.next_item(y)
	
	
	def _move_cursor(self, cursor, x, y):
		if (x, y) == (0, 0):
			cursor.set_visible(False)
			return
		cursor.set_visible(True)
		pad_w = cursor.get_allocation().width * 0.5
		pad_h = cursor.get_allocation().height * 0.5
		max_w = self.grid.get_allocation().width - 2 * pad_w
		max_h = self.grid.get_allocation().height - 2 * pad_h
		
		x, y = circle_to_square(x / (STICK_PAD_MAX * 2.0), y / (STICK_PAD_MAX * 2.0))
		x = clamp(pad_w, (pad_w + max_w) * 0.5 + x * max_w, max_w - pad_w)
		y = clamp(pad_h, (pad_h + max_h) * 0.5 + y * max_h * -1, max_h - pad_h)
		x += self.grid.get_allocation().x
		y += self.grid.get_allocation().y
		self.f.move(cursor, int(x), int(y))
		
		for i in self._buttons:
			if point_in_gtkrect(i.get_allocation(), x, y):
				if cursor.selected:
					cursor.selected.set_name("osd-key-buton")
				cursor.selected = i
				cursor.selected.set_name("osd-key-buton-hilight")
				break
	
	
	def _get_under_cursor(self, cursor):
		x, y = self.f.child_get(cursor, "x", "y")
		for i in self._buttons:
			if point_in_gtkrect(i.get_allocation(), x, y):
				return i
		return None
	
	
	def on_event(self, daemon, what, data):
		if what == LEFT:
			self._move_cursor(self.cursors[0], *data)
		elif what == "LPAD" and data[0] == 1:
			b = self._get_under_cursor(self.cursors[0])
			if b: self._string += b.get_label()[0]
			self._update_items()
		elif what == RIGHT:
			self._move_cursor(self.cursors[1], *data)
		elif what == "RPAD" and data[0] == 1:
			b = self._get_under_cursor(self.cursors[1])
			if b: self._string += b.get_label()[0]
			self._update_items()
		elif what == "LB":
			if len(self._string) > 0:
				self._string = self._string[:-1]
				self._update_items()
		elif what == STICK:
			self._scon.set_stick(*data)
		elif what == self._cancel_with:
			if data[0] == 0:	# Button released
				self.quit(-1)
		elif what == self._confirm_with:
			if data[0] == 0:	# Button released
				if self._selected:
					self._launch()
					self.quit(0)
				else:
					self.quit(-1)
