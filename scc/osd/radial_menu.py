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
from scc.tools import degdiff
from scc.osd.menu import Menu
from scc.osd import OSDWindow
from scc.config import Config
from math import pi as PI, sqrt, atan2, sin, cos

import os, sys, logging
log = logging.getLogger("osd.menu")


class RadialMenu(Menu):
	MIN_DISTANCE = 3000		# Minimal cursor distance from center (in px^2)
	
	def __init__(self,):
		Menu.__init__(self, "osd-radial-menu")
		self.angle = 0
	
	
	def create_parent(self):
		background = os.path.join(get_share_path(), "images", 'radial-menu.svg')
		self.b = SVGWidget(self, background)
		return self.b
	
	
	def parse_argumets(self, argv):
		self.editor = self.b.edit()
		rv = Menu.parse_argumets(self, argv)
		if rv:
			self.enable_cursor()
		return rv
	
	
	def generate_widget(self, item):
		if item.id is None:
			# Labels and separators, radial menu can't show these
			return None
		e = self.editor.clone_element("menuitem_template")
		SVGEditor.set_text(e, item.label)
		e.attrib['id'] = "menuitem_" + item.id
		return e
	
	
	def pack_items(self, trash, items):
		index = 0
		pb = self.b.get_pixbuf()
		image_width = pb.get_width()
		item_width = 360.0 / len(self.items)
		a1, a2 = (-90.0 - item_width * 0.5) * PI / 180.0, (-90.0 + item_width * 0.5) * PI / 180.0
		for i in items:
			# Set size of each arc
			if SVGWidget.get_element(i.widget, "arc") is not None:
				l = SVGWidget.get_element(i.widget, "arc")
				radius = float(l.attrib["radius"])	# TODO: Find how to get value of 'sodipodi:rx'
				l.attrib["d"] = l.attrib["d-template"] % (
					radius * cos(a1) + image_width / 2,
					radius * sin(a1) + image_width / 2,
					radius * cos(a2) + image_width / 2,
					radius * sin(a2) + image_width / 2,
				)
			# Rotate arc to correct position
			i.a = (360.0 / float(len(self.items))) * float(index)
			i.widget.attrib['transform'] = "%s rotate(%s, %s, %s)" % (
				i.widget.attrib['transform'], i.a, image_width / 2, image_width / 2)
			# Rotate text in arc to other direction to keep it horisontal
			if SVGWidget.get_element(i.widget, "menuitem_text") is not None:
				l = SVGWidget.get_element(i.widget, "menuitem_text")
				l.attrib['id'] = "text_" + i.id
				l.attrib['transform'] = "%s rotate(%s)" % (l.attrib['transform'], -i.a)
			# Place up to 3 lines of item label
			label = i.label.split("\n")
			first_line = 0
			if len(label) == 1:
				self.editor.remove_element(SVGWidget.get_element(i.widget, "line0"))
				self.editor.remove_element(SVGWidget.get_element(i.widget, "line2"))
				first_line = 1
			elif len(label) == 2:
				self.editor.remove_element(SVGWidget.get_element(i.widget, "line0"))
				first_line = 1
			for line in xrange(0, len(label)):
				l = SVGWidget.get_element(i.widget, "line%s" % (first_line + line,))
				if l is None:
					break
				SVGEditor.set_text(l, label[line])
			# Continue with next menu item
			i.index = index
			
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
		width = pb.get_width()
		height = pb.get_height()
		self.f.move(self.cursor, int(width / 2), int(height / 2))
		
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
		self._selected = self.items[index]
	
	
	def on_event(self, daemon, what, data):
		if self._submenu:
			return self._submenu.on_event(daemon, what, data)
		if what == self._control_with:
			x, y = data
			# Special case, both confirm_with and cancel_with can be set to STICK
			if self._cancel_with == STICK and self._control_with == STICK:
				if self._control_equals_cancel(daemon, x, y):
					return
			
			max_w = self.get_allocation().width - (self.cursor.get_allocation().width * 1.0)
			max_h = self.get_allocation().height - (self.cursor.get_allocation().height * 1.0)
			x = ((x * 0.75 / (STICK_PAD_MAX * 2.0)) + 0.5) * max_w
			y = (0.5 - (y * 0.75 / (STICK_PAD_MAX * 2.0))) * max_h
			
			x -= self.cursor.get_allocation().width * 0.5
			y -= self.cursor.get_allocation().height * 0.5
			
			self.f.move(self.cursor, int(x), int(y))
			x, y = data
			if abs(x) + abs(y) > RadialMenu.MIN_DISTANCE:
				angle = atan2(*data) * 180.0 / PI
				half_width = 180.0 / len(self.items)
				for i in self.items:
					if abs(degdiff(i.a, angle)) < half_width:
						if self._selected != i:
							self._selected = i
							self.b.hilight({
								"menuitem_" + i.id : "#" + self.config["osd_colors"]["menuitem_hilight"],
								"text_" + i.id :  "#" + self.config["osd_colors"]["menuitem_hilight_text"],
							})
		else:
			return Menu.on_event(self, daemon, what, data)
