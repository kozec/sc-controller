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
from scc.osd.menu import Menu
from scc.osd import OSDWindow
from scc.config import Config
from math import pi as PI, sqrt, atan2

import os, sys, logging
log = logging.getLogger("osd.menu")


class RadialMenu(Menu):
	def __init__(self,):
		Menu.__init__(self, "osd-radial-menu")
		self.angle = 0
	
	
	def create_parent(self):
		background = os.path.join(get_share_path(), "images", 'radial-menu.svg')
		self.b = SVGWidget(self, background)
		return self.b
	
	
	def parse_argumets(self, argv):
		self.editor = self.b.edit()
		return Menu.parse_argumets(self, argv)
	
	
	def generate_widget(self, item):
		e = self.editor.clone_element("menuitem_template")
		SVGEditor.set_text(e, item.label)
		e.attrib['id'] = "menuitem_" + item.id
		return e
	
	
	def pack_items(self, trash, items):
		index = 0
		for i in items:
			a = 360 / len(self.items) * index
			i.widget.attrib['transform'] = "%s rotate(%s, 0, 0)" % (i.widget.attrib['transform'], a)
			index += 1
		
		self.editor.remove_element("menuitem_template")
		self.editor.commit()
		del self.editor
	
	
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
		
		r = int(pb.get_width() * 0.985)
		x = (pb.get_width() - r) / 2
		
		X.fill_arc(self.xdisplay, pixmap, gc,
			x, x, r, r, 0, 360*64)
		
		X.flush_gc(self.xdisplay, gc)
		X.flush(self.xdisplay)
		
		X.shape_combine_mask(self.xdisplay, win, X.SHAPE_BOUNDING, 0, 0, pixmap, X.SHAPE_SET)
		
		X.flush(self.xdisplay)
	
	
	def select(self, index):
		pass
		"""
		if self._selected:
			self._selected[1].set_name("osd-menu-item")
		self._selected = self.items[index]
		self._selected[1].set_name("osd-menu-item-selected")
		"""
	
	
	def on_event(self, daemon, what, data):
		if self._submenu:
			return self._submenu.on_event(daemon, what, data)
		if what == self._control_with:
			angle = 10 * int(atan2(*data) * 18.0 / PI)
			if self.angle != angle:
				editor = self.b.edit()
				e = editor.get_element("selector")
				e.attrib['transform'] = "rotate(%s, 0, 0)" % (angle,)
				editor.commit()
				self.angle = angle
