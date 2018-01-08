#!/usr/bin/env python2
"""
SC-Controller - OSD Menu

Display menu that user can navigate through and prints chosen item id to stdout
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, GLib, Gio, Gdk, GdkX11, GdkPixbuf
from scc.tools import point_in_gtkrect, find_menu, find_icon
from scc.tools import circle_to_square, clamp
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX, SCButtons
from scc.constants import LEFT, RIGHT, SAME, STICK
from scc.menu_data import MenuData, Separator, Submenu
from scc.gui.daemon_manager import DaemonManager
from scc.osd import OSDWindow, StickController
from scc.paths import get_share_path
from scc.lib import xwrappers as X
from scc.config import Config
from math import sqrt

import os, sys, json, logging
log = logging.getLogger("osd.menu")

# Fill MENU_GENERATORS dict
import scc.osd.menu_generators
import scc.x11.autoswitcher


class Menu(OSDWindow):
	EPILOG="""Exit codes:
   0  - clean exit, user selected option
  -1  - clean exit, user canceled menu
  -2  - clean exit, menu closed from callback method
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon, sc-daemon reported error or died while menu is displayed.
   3  - erorr, failed to lock input stick, pad or button(s)
	"""
	SUBMENU_OFFSET = 50
	PREFER_BW_ICONS = True
	
	
	def __init__(self, cls="osd-menu"):
		OSDWindow.__init__(self, cls)
		self.daemon = None
		self.config = None
		self.feedback = None
		self.controller = None
		self.xdisplay = X.Display(hash(GdkX11.x11_get_default_xdisplay()))	# Magic
		
		cursor = os.path.join(get_share_path(), "images", 'menu-cursor.svg')
		self.cursor = Gtk.Image.new_from_file(cursor)
		self.cursor.set_name("osd-menu-cursor")
		
		self.parent = self.create_parent()
		self.f = Gtk.Fixed()
		self.f.add(self.parent)
		self.add(self.f)
		
		self._submenu = None
		self._scon = StickController()
		self._scon.connect("direction", self.on_stick_direction)
		self._is_submenu = False
		self._selected = None
		self._menuid = None
		self._use_cursor = False
		self._eh_ids = []
		self._control_with = STICK
		self._confirm_with = 'A'
		self._cancel_with = 'B'
	
	
	def set_is_submenu(self):
		"""
		Marks menu as submenu. This changes behaviour of some methods,
		especially disables (un)locking of input stick and buttons.
		"""
		self._is_submenu = True
	
	
	def create_parent(self):
		v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		v.set_name("osd-menu")
		return v
	
	
	def pack_items(self, parent, items):
		for item in items:
			parent.pack_start(item.widget, True, True, 0)
	
	
	def use_daemon(self, d):
		"""
		Allows (re)using already existing DaemonManager instance in same process.
		use_config() should be be called before parse_argumets() if this is used.
		"""
		self.daemon = d
		if not self._is_submenu:
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
		return self._menuid
	
	
	def get_selected_item_id(self):
		"""
		Returns ID of selected item or None if nothing is selected.
		"""
		if self._selected:
			return self._selected.id
		return None
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('--control-with', '-c', type=str,
			metavar="option", default=STICK, choices=(LEFT, RIGHT, STICK),
			help="which pad or stick should be used to navigate menu (default: %s)" % (STICK,))
		self.argparser.add_argument('--confirm-with', type=str,
			metavar="button", default='A',
			help="button used to confirm choice (default: A)")
		self.argparser.add_argument('--cancel-with', type=str,
			metavar="button", default='B',
			help="button used to cancel menu (default: B)")
		self.argparser.add_argument('--confirm-with-release', action='store_true',
			help="confirm choice with button release instead of button press")
		self.argparser.add_argument('--cancel-with-release', action='store_true',
			help="cancel menu with button release instead of button press")
		self.argparser.add_argument('--use-cursor', '-u', action='store_true',
			help="display and use cursor")
		self.argparser.add_argument('--size', type=int,
			help="sets prefered width or height")
		self.argparser.add_argument('--feedback-amplitude', type=int,
			help="enables and sets power of feedback effect generated when active menu option is changed")
		self.argparser.add_argument('--from-profile', '-p', type=str,
			metavar="profile_file menu_name",
			help="load menu items from profile file")
		self.argparser.add_argument('--from-file', '-f', type=str,
			metavar="filename",
			help="load menu items from json file")
		self.argparser.add_argument('--print-items', action='store_true',
			help="prints menu items to stdout")
		self.argparser.add_argument('items', type=str, nargs='*', metavar='id title',
			help="Menu items")
	
	
	@staticmethod
	def _get_on_screen_position(w):
		a = w.get_allocation()
		parent = w.get_parent()
		if parent:
			if isinstance(parent, Menu) and parent.get_window() is not None:
				x, y = parent.get_window().get_position()
			else:
				x, y = Menu._get_on_screen_position(parent)
			return a.x + x, a.y + y
		else:
			return a.x, a.y
	
	
	def parse_menu(self):
		if self.args.from_profile:
			try:
				self._menuid = self.args.items[0]
				self.items = MenuData.from_profile(self.args.from_profile, self._menuid)
			except IOError:
				print >>sys.stderr, '%s: error: profile file not found' % (sys.argv[0])
				return False
			except ValueError:
				print >>sys.stderr, '%s: error: menu not found' % (sys.argv[0])
				return False
		elif self.args.from_file:
			try:
				self._menuid = self.args.from_file
				self.items = MenuData.from_file(self.args.from_file)
			except:
				print >>sys.stderr, '%s: error: failed to load menu file' % (sys.argv[0])
				return False
		else:
			try:
				self.items = MenuData.from_args(self.args.items)
				self._menuid = None
			except ValueError:
				print >>sys.stderr, '%s: error: invalid number of arguments' % (sys.argv[0])
				return False
		return True
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		if not self.parse_menu():
			return False
		if not self.config:
			self.config = Config()
		
		# Parse simpler arguments
		self._control_with = self.args.control_with
		self._confirm_with = self.args.confirm_with
		self._cancel_with = self.args.cancel_with
		self._size = self.args.size
		
		if self.args.use_cursor:
			self.enable_cursor()
		
		if self.args.feedback_amplitude:
			side = "LEFT"
			if self._control_with == "RIGHT":
				side = "RIGHT"
			elif self._control_with == "STICK":
				side = "BOTH"
			self.feedback = side, int(self.args.feedback_amplitude)
		
		if self._confirm_with == SAME:
			if self._control_with == RIGHT:
				self._confirm_with = SCButtons.RPADTOUCH.name
			else:
				self._confirm_with = SCButtons.LPADTOUCH.name
		
		# Create buttons that are displayed on screen
		items = self.items.generate(self)
		self.items = []
		for item in items:
			item.widget = self.generate_widget(item)
			if item.widget is not None:
				self.items.append(item)
		self.pack_items(self.parent, self.items)
		if len(self.items) == 0:
			print >>sys.stderr, '%s: error: no items in menu' % (sys.argv[0])
			return False
		
		if self.args.print_items:
			max_id_len = max(*[ len(x.id) for x in self.items ])
			row_format ="{:>%s}:\t{}" % (max_id_len,)
			for item in self.items:
				print row_format.format(item.id, item.label)
		return True
	
	
	def enable_cursor(self):
		if not self._use_cursor:
			self.f.add(self.cursor)
			self.f.show_all()
			self._use_cursor = True
	
	
	def generate_widget(self, item):
		""" Generates gtk widget for specified menutitem """
		if isinstance(item, Separator) and item.label:
			widget = Gtk.Button.new_with_label(item.label)
			widget.set_relief(Gtk.ReliefStyle.NONE)
			widget.set_name("osd-menu-separator")
			return widget
		elif isinstance(item, Separator):
			widget = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
			widget.set_name("osd-menu-separator")
			return widget
		else:
			widget = Gtk.Button.new_with_label(item.label)
			widget.set_relief(Gtk.ReliefStyle.NONE)
			if hasattr(widget.get_children()[0], "set_xalign"):
				widget.get_children()[0].set_xalign(0)
			else:
				widget.get_children()[0].set_halign(Gtk.Align.START)
			if isinstance(item, Submenu):
				item.callback = self.show_submenu
				label1 = widget.get_children()[0]
				label2 = Gtk.Label(_(">>"))
				label2.set_property("margin-left", 30)
				box = Gtk.Box(Gtk.Orientation.HORIZONTAL)
				widget.remove(label1)
				box.pack_start(label1, True, True, 1)
				box.pack_start(label2, False, True, 1)
				widget.add(box)
				widget.set_name("osd-menu-item")
			elif item.id is None:
				widget.set_name("osd-menu-dummy")
			else:
				widget.set_name("osd-menu-item")
			
			if isinstance(item.icon, Gio.FileIcon):
				icon_file = item.icon.get_file().get_path()
				has_colors = True
			elif isinstance(item.icon, Gio.ThemedIcon):
				icon = Gtk.IconTheme.get_default().choose_icon(
					item.icon.get_names(), 64, 0)
				icon_file = icon.get_filename() if icon else None
				has_colors = True
			else:
				icon_file, has_colors = find_icon(item.icon, self.PREFER_BW_ICONS)
			
			if icon_file:
				icon = MenuIcon(icon_file, has_colors)
				label = widget.get_children()[0]
				for c in [] + widget.get_children():
					widget.remove(c)
				box = Gtk.Box()
				box.pack_start(icon,  False, True, 0)
				box.pack_start(label, True, True, 10)
				widget.add(box)
				
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
			GLib.timeout_add(2, self._check_on_screen_position)
			return True
		return False
	
	
	def _check_on_screen_position(self):
		x, y = Menu._get_on_screen_position(self._selected.widget)
		screen_height = self.get_window().get_screen().get_height()
		if y < 50:
			wx, wy = self.get_window().get_position()
			wy += 5
			self.get_window().move(wx, wy)
			GLib.timeout_add(2, self._check_on_screen_position)
		if y > screen_height - 100:
			wx, wy = self.get_window().get_position()
			wy -= 5
			self.get_window().move(wx, wy)
			GLib.timeout_add(2, self._check_on_screen_position)
	
	
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
	
	
	def on_daemon_connected(self, *a):
		if not self.config:
			self.config = Config()
		self.controller = self.choose_controller(self.daemon)
		if self.controller is None or not self.controller.is_connected():
			# There is no controller connected to daemon
			self.on_failed_to_lock("Controller not connected")
			return
		
		self._eh_ids += [
			(self.controller, self.controller.connect('event', self.on_event)),
			(self.controller, self.controller.connect('lost', self.on_controller_lost)),
		]
		self.lock_inputs()
	
	
	def lock_inputs(self):
		def success(*a):
			log.error("Sucessfully locked input")
		locks = [ self._control_with, self._confirm_with, self._cancel_with ]
		self.controller.lock(success, self.on_failed_to_lock, *locks)
	
	
	def quit(self, code=-2):
		if not self._is_submenu:
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
			if self.select(i):
				# Not a separator
				break
			i += direction
			if start < 0: start = 0
	
	
	def on_submenu_closed(self, *a):
		self.set_name("osd-menu")
		if self._submenu.get_exit_code() in (0, -2):
			self._menuid = self._submenu._menuid
			self._selected = self._submenu._selected
			self.quit(self._submenu.get_exit_code())
		self._submenu = None
	
	
	def show_submenu(self, trash, trash2, trash3, menuitem):
		""" Called when user chooses menu item pointing to submenu """
		filename = find_menu(menuitem.filename)
		if filename:
			self._submenu = self.__class__()
			sub_pos = list(self.position)
			for i in (0, 1):
				sub_pos[i] = (sub_pos[i] - self.SUBMENU_OFFSET
						if sub_pos[i] < 0 else sub_pos[i] + self.SUBMENU_OFFSET)
					
			self._submenu.use_config(self.config)
			self._submenu.parse_argumets(["menu.py",
				"-x", str(sub_pos[0]), "-y", str(sub_pos[1]),
			 	"--from-file", filename,
				"--control-with", self._control_with,
				"--confirm-with", self._confirm_with,
				"--cancel-with", self._cancel_with
			])
			self._submenu.set_is_submenu()
			self._submenu.use_daemon(self.daemon)
			self._submenu.controller = self.controller
			self._submenu.connect('destroy', self.on_submenu_closed)
			self._submenu.show()
			self.set_name("osd-menu-inactive")
	
	
	def _control_equals_cancel(self, daemon, x, y):
		"""
		Called by on_event in that very special case when both confirm_with
		and cancel_with are set to STICK.
		
		Separated because RadialMenu overrides on_event and still
		needs to call this.
		
		Returns True if menu was canceled.
		"""
		distance = sqrt(x*x + y*y)
		if distance < STICK_PAD_MAX / 8:
			self.quit(-1)
			return True
		return False
	
	
	def on_stick_direction(self, trash, x, y):
		if y != 0:
			self.next_item(y)
	
	
	def on_event(self, daemon, what, data):
		if self._submenu:
			return self._submenu.on_event(daemon, what, data)
		if what == self._control_with:
			x, y = data
			if self._use_cursor:
				# Special case, both confirm_with and cancel_with
				# can be set to STICK
				if self._cancel_with == STICK and self._control_with == STICK:
					if self._control_equals_cancel(daemon, x, y):
						return
				
				pad_w = self.cursor.get_allocation().width * 0.5
				pad_h = self.cursor.get_allocation().height * 0.5
				max_w = self.get_allocation().width - 2 * pad_w
				max_h = self.get_allocation().height - 2 * pad_h
				
				x, y = circle_to_square(x / (STICK_PAD_MAX * 2.0), y / (STICK_PAD_MAX * 2.0))
				x = clamp(pad_w, (pad_w + max_w) * 0.5 + x * max_w, max_w - pad_w)
				y = clamp(pad_h, (pad_h + max_h) * 0.5 + y * max_h * -1, max_h - pad_h)
				self.f.move(self.cursor, int(x), int(y))
				
				for i in self.items:
					if point_in_gtkrect(i.widget.get_allocation(), x, y):
						self.select(self.items.index(i))
			else:
				self._scon.set_stick(x, y)
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
	
	
class MenuIcon(Gtk.DrawingArea):
	""" Auti-sized, auto-recolored icon for menus """
	
	def __init__(self, filename, has_colors = False):
		Gtk.DrawingArea.__init__(self)
		self.connect('size_allocate', self.on_size_allocate)
		self.has_colors = has_colors
		self.set_filename(filename)
	
	
	def set_filename(self, filename):
		if filename is None:
			self.pb = None
		else:
			self.pb = GdkPixbuf.Pixbuf.new_from_file(filename)
	
	
	def on_size_allocate(self, trash, allocation):
		if allocation.width < allocation.height:
			self.set_size_request(allocation.height, -1)
	
	
	def do_draw(self, cr):
		allocation = self.get_allocation()
		if allocation.width >= allocation.height:
			context = Gtk.Widget.get_style_context(self)
			Gtk.render_background(context, cr, 0, 0,
					allocation.width, allocation.height)
			if self.pb is None:
				# No icon set
				return
			scaled = self.pb.scale_simple(
				allocation.height, allocation.height,
				GdkPixbuf.InterpType.BILINEAR
			)
			surf = Gdk.cairo_surface_create_from_pixbuf(scaled, 1)
			if self.has_colors:
				cr.set_source_surface(surf, 1.0, 1.0)
						#allocation.height, allocation.height)
				cr.rectangle(0, 0, allocation.height, allocation.height)
			else:
				Gdk.cairo_set_source_rgba(cr,
						context.get_color(Gtk.StateFlags.NORMAL))
				cr.mask_surface(surf, 0, 0)
			cr.fill()
