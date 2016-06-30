#!/usr/bin/env python2
"""
SC-Controller - OSD Menu

Display menu that user can navigate through
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GLib, GdkX11
from scc.constants import LEFT, RIGHT, STICK, STICK_PAD_MIN, STICK_PAD_MAX
from scc.menu_data import MenuData, Separator, Submenu
from scc.gui.svg_widget import SVGWidget, SVGEditor
from scc.paths import get_share_path
from scc.lib import xwrappers as X
from scc.config import Config
from scc.osd import OSDWindow
from math import pi as PI

import os, sys, logging
log = logging.getLogger("osd.menu")


class RadialMenu(OSDWindow):
	def __init__(self,):
		OSDWindow.__init__(self, "osd-radial-menu")
		self.daemon = None
		self.config = None
		
		cursor = os.path.join(get_share_path(), "images", 'menu-cursor.svg')
		background = os.path.join(get_share_path(), "images", 'radial-menu.svg')
		self.xdisplay = X.Display(hash(GdkX11.x11_get_default_xdisplay()))	# Magic
		
		self.b = SVGWidget(self, background)
		
		self.i = Gtk.Image.new_from_file(cursor)
		self.i.set_name("osd-menu-cursor")
		
		self.f = Gtk.Fixed()
		self.f.add(self.b)
		self.f.add(self.i)
		self.add(self.f)
		self._selected = None
		self.select(0)
	
	
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
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		if not self.config:
			self.config = Config()
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
			#try:
			data = json.loads(open(self.args.from_file, "r").read())
			self._menuid = self.args.from_file
			self.items = MenuData.from_json_data(data)
			#except:
			#	print >>sys.stderr, '%s: error: failed to load menu file' % (sys.argv[0])
			#	return False
		else:
			try:
				self.items = MenuData.from_args(self.args.items)
				self._menuid = None
			except ValueError:
				print >>sys.stderr, '%s: error: invalid number of arguments' % (sys.argv[0])
				return False
		
		# Parse simpler arguments
		self._control_with = self.args.control_with
		self._confirm_with = self.args.confirm_with
		self._cancel_with = self.args.cancel_with
		
		# Create buttons that are displayed on screen
		self.items = self.items.generate(self)
		a, addition = 0, 360 / len(self.items)
		editor = self.b.edit()
		for item in self.items:
			e = editor.clone_element("menuitem_template")
			SVGEditor.set_text(e, item.label)
			e.attrib['transform'] = "translate(384, -192) rotate(%s, 0, 0)" % (a,)
			e.attrib['id'] = "menuitem_" + item.id
			a += addition
		editor.remove_element("menuitem_template")
		editor.commit()
			
		#	item.widget = self.generate_widget(item)
		#self.pack_items(self.parent, self.items)
		if len(self.items) == 0:
			print >>sys.stderr, '%s: error: no items in menu' % (sys.argv[0])
			return False
		
		if self.args.print_items:
			max_id_len = max(*[ len(x.id) for x in self.items ])
			row_format ="{:>%s}:\t{}" % (max_id_len,)
			for item in self.items:
				print row_format.format(item.id, item.label)
		return True	
	
	
	def select(self, index):
		pass
		"""
		if self._selected:
			self._selected[1].set_name("osd-menu-item")
		self._selected = self.items[index]
		self._selected[1].set_name("osd-menu-item-selected")
		"""
	
	
	def show(self):
		OSDWindow.show(self)

		from ctypes import byref

		pb = self.b.get_pixbuf()
		win = X.XID(self.get_window().get_xid())
		
		pixmap = X.create_pixmap(self.xdisplay, win,
			pb.get_width(), pb.get_height(), 1)
		gc = X.create_gc(self.xdisplay, pixmap, 0, None)
		X.set_foreground(self.xdisplay, gc, 0)
		X.fill_rectangle(self.xdisplay, pixmap, gc, 0, 0, pb.get_width(), pb.get_height())
		X.set_foreground(self.xdisplay, gc, 1)
		X.set_background(self.xdisplay, gc, 1)
		
		r = int(pb.get_width() * 0.98)
		x = (pb.get_width() - r) / 2
		
		X.fill_arc(self.xdisplay, pixmap, gc,
			x, x, r, r, 0, 360*64)
		
		X.flush_gc(self.xdisplay, gc)
		X.flush(self.xdisplay)
		print "gc = ", gc
		
		
		print X.write_bitmap(self.xdisplay, b"kua.bmp", pixmap,
			pb.get_width(), pb.get_height(),
			-1, -1)
		
		X.shape_combine_mask(self.xdisplay, win, X.SHAPE_BOUNDING, 0, 0, pixmap, X.SHAPE_SET)
		
		X.flush(self.xdisplay)
