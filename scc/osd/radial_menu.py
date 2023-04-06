#!/usr/bin/env python2
"""
SC-Controller - OSD Menu

Display menu that user can navigate through
"""

from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GLib, GdkX11
from scc.constants import LEFT, RIGHT, STICK, STICK_PAD_MIN, STICK_PAD_MAX
from scc.menu_data import MenuData, Separator, Submenu
from scc.gui.svg_widget import SVGWidget, SVGEditor
from scc.osd.menu import Menu, MenuIcon
from scc.osd import OSDWindow
from scc.tools import degdiff, find_icon
from scc.paths import get_share_path
from scc.lib import xwrappers as X
from scc.config import Config
from math import pi as PI, atan2, sin, cos

import os, sys, json, logging
log = logging.getLogger("osd.menu")


class RadialMenu(Menu):
	RECOLOR_BACKGROUNDS = ( "background", "menuitem_hilight_border", "text" )
	RECOLOR_STROKES = ( "border", "menuitem_border" )
	MIN_DISTANCE = 3000		# Minimal cursor distance from center (in px^2)
	ICON_SIZE = 96
	
	def __init__(self,):
		Menu.__init__(self, "osd-radial-menu")
		self.angle = 0
		self.rotation = 0
		self.scale = 1.0
		self.items_with_icon = []
	
	
	def create_parent(self):
		background = os.path.join(get_share_path(), "images", 'radial-menu.svg')
		self.b = SVGWidget(background)
		self.b.connect('size-allocate', self.on_size_allocate)
		self.recolor()
		return self.b
	
	
	def recolor(self):
		config = Config()
		source_colors = {}
		try:
			# Try to read json file and bail out if it fails
			desc = os.path.join(get_share_path(), "images", 'radial-menu.svg.json')
			source_colors = json.loads(open(desc, "r").read())['colors']
		except Exception as e:
			log.warning("Failed to load keyboard description")
			log.warning(e)
			return
		editor = self.b.edit()
		
		for k in RadialMenu.RECOLOR_BACKGROUNDS:
			if k in config['osd_colors'] and k in source_colors:
				editor.recolor_background(source_colors[k], config['osd_colors'][k])
		editor.recolor_background(source_colors["background"], config['osd_colors']["background"])
		
		for k in RadialMenu.RECOLOR_STROKES:
			if k in config['osd_colors'] and k in source_colors:
				print("REC", source_colors[k], config['osd_colors'][k])
				editor.recolor_strokes(source_colors[k], config['osd_colors'][k])
		
		editor.commit()
	
	
	def on_size_allocate(self, trash, allocation):
		""" (Re)centers all icons when menu is displayed or size is changed """
		cx = allocation.width * self.scale * 0.5
		cy = allocation.height * self.scale * 0.5
		radius = min(cx, cy) * 2 / 3
		for i in self.items_with_icon:
			angle, icon = float(i.a) * PI / 180.0, i.icon_widget
			x, y = cx + sin(angle) * radius, cy - cos(angle) * radius
			x = x - (self.ICON_SIZE * self.scale * 0.5)
			y = y - (self.ICON_SIZE * self.scale * 0.5)
			i.icon_widget.get_parent().move(i.icon_widget, x, y)
	
	
	def get_window_size(self):
		w, h = Menu.get_window_size(self)
		if self.scale != 1.0:
			w = int(w * self.scale)
			h = int(h * self.scale)
		return w, h
	
	
	def _add_arguments(self):
		Menu._add_arguments(self)
		self.argparser.add_argument('--rotation', type=float, default=0,
			help="rotates input by angle (default: 0)")
	
	
	def parse_argumets(self, argv):
		self.editor = self.b.edit()
		rv = Menu.parse_argumets(self, argv)
		self.rotation = self.args.rotation
		if rv:
			self.enable_cursor()
		return rv
	
	
	def generate_widget(self, item):
		if isinstance(item, (Separator, Submenu)) or item.id is None:
			# Labels and separators, radial menu can't show these
			return None
		e = self.editor.clone_element("menuitem_template")
		SVGEditor.set_text(e, item.label)
		e.attrib['id'] = "menuitem_" + item.id
		return e
	
	
	def pack_items(self, trash, items):
		if self._size > 0 and self._size < 100:
			self.scale = self._size / 100.0
			root = SVGEditor.get_element(self.editor, "root")
			SVGEditor.scale(root, self.scale)
		pb = self.b.get_pixbuf()
		# Image width is not scaled as everything bellow operates
		# in 'root' object coordinate space
		image_width = pb.get_width()
		
		index = 0
		item_offset = 360.0 / len(self.items)
		a1 = (-90.0 - item_offset * 0.5) * PI / 180.0
		a2 = (-90.0 + item_offset * 0.5) * PI / 180.0
		for i in self.items_with_icon:
			i.icon_widget.get_parent().remove_child(i.icon_widget)
		self.items_with_icon = []
		for i in items:
			# Set size of each arc
			if SVGEditor.get_element(i.widget, "arc") is not None:
				l = SVGEditor.get_element(i.widget, "arc")
				radius = float(l.attrib["radius"])	# TODO: Find how to get value of 'sodipodi:rx'
				l.attrib["d"] = l.attrib["d-template"] % (
					radius * cos(a1) + image_width / 2,
					radius * sin(a1) + image_width / 2,
					radius * cos(a2) + image_width / 2,
					radius * sin(a2) + image_width / 2,
				)
			# Rotate arc to correct position
			i.a = (360.0 / float(len(self.items))) * float(index)
			SVGEditor.rotate(i.widget, i.a, image_width * 0.5, image_width * 0.5)
			# Check if there is any icon
			icon_file, has_colors = find_icon(i.icon, False) if hasattr(i, "icon") else (None, False)
			if icon_file:
				# Icon - hide all text and place MenuIcon widget on top of image
				self.editor.remove_element(SVGEditor.get_element(i.widget, "menuitem_text"))
				self.editor.remove_element(SVGEditor.get_element(i.widget, "line0"))
				self.editor.remove_element(SVGEditor.get_element(i.widget, "line2"))
				i.icon_widget = MenuIcon(icon_file, has_colors)
				i.icon_widget.set_name("osd-radial-menu-icon")
				i.icon_widget.set_size_request(self.ICON_SIZE * self.scale, self.ICON_SIZE * self.scale)
				self.b.get_parent().put(i.icon_widget, 200, 200)
				self.items_with_icon.append(i)
			else:
				# No icon - rotate text in arc to other direction to keep it horisontal
				if SVGEditor.get_element(i.widget, "menuitem_text") is not None:
					l = SVGEditor.get_element(i.widget, "menuitem_text")
					l.attrib['id'] = "text_" + i.id
					l.attrib['transform'] = "%s rotate(%s)" % (l.attrib['transform'], -i.a)
				# Place up to 3 lines of item label
				label = i.label.split("\n")
				first_line = 0
				if len(label) == 1:
					self.editor.remove_element(SVGEditor.get_element(i.widget, "line0"))
					self.editor.remove_element(SVGEditor.get_element(i.widget, "line2"))
					first_line = 1
				elif len(label) == 2:
					self.editor.remove_element(SVGEditor.get_element(i.widget, "line0"))
					first_line = 1
				for line in range(0, len(label)):
					l = SVGEditor.get_element(i.widget, "line%s" % (first_line + line,))
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
		
		width = int(pb.get_width() * self.scale * self.get_scale_factor())
		height = int(pb.get_height() * self.scale * self.get_scale_factor())
		pixmap = X.create_pixmap(self.xdisplay, win, width, height, 1)
		self.f.move(self.cursor, int(width / 2), int(height / 2))
		
		gc = X.create_gc(self.xdisplay, pixmap, 0, None)
		X.set_foreground(self.xdisplay, gc, 0)
		X.fill_rectangle(self.xdisplay, pixmap, gc, 0, 0, width, height)
		X.set_foreground(self.xdisplay, gc, 1)
		X.set_background(self.xdisplay, gc, 1)
		
		r = int(width * 0.985)
		x = (width - r) / 2
		
		X.fill_arc(self.xdisplay, pixmap, gc,
			x, x, r, r, 0, 360*64)
		
		X.flush_gc(self.xdisplay, gc)
		X.flush(self.xdisplay)
		
		X.shape_combine_mask(self.xdisplay, win, X.SHAPE_BOUNDING, 0, 0, pixmap, X.SHAPE_SET)
		
		X.flush(self.xdisplay)
	
	
	def select(self, i):
		if type(i) == int:
			i = self.items[i]
		if self._selected and hasattr(self._selected, "icon_widget"):
			if self._selected.icon_widget:
				self._selected.icon_widget.set_name("osd-radial-menu-icon")
		self._selected = i
		if hasattr(self._selected, "icon_widget") and self._selected.icon_widget:
			self._selected.icon_widget.set_name("osd-radial-menu-icon-selected")
		self.b.hilight({
			"menuitem_" + i.id : "#" + self.config["osd_colors"]["menuitem_hilight"],
			"text_" + i.id :  "#" + self.config["osd_colors"]["menuitem_hilight_text"],
		})
	
	
	def on_event(self, daemon, what, data):
		if self._submenu:
			return self._submenu.on_event(daemon, what, data)
		if what == self._control_with:
			x, y = data
			# Special case, both confirm_with and cancel_with can be set to STICK
			if self._cancel_with == STICK and self._control_with == STICK:
				if self._control_equals_cancel(daemon, x, y):
					return
			
			if self.rotation:
				rx = x * cos(self.rotation) - y * sin(self.rotation)
				ry = x * sin(self.rotation) + y * cos(self.rotation)
				x, y = rx, ry
			
			max_w = self.get_allocation().width * self.scale - (self.cursor.get_allocation().width * 1.0)
			max_h = self.get_allocation().height * self.scale - (self.cursor.get_allocation().height * 1.0)
			cx = ((x * 0.75 / (STICK_PAD_MAX * 2.0)) + 0.5) * max_w
			cy = (0.5 - (y * 0.75 / (STICK_PAD_MAX * 2.0))) * max_h
			
			cx -= self.cursor.get_allocation().width *  0.5
			cy -= self.cursor.get_allocation().height *  0.5
			self.f.move(self.cursor, int(cx), int(cy))
			
			if abs(x) + abs(y) > RadialMenu.MIN_DISTANCE:
				angle = atan2(x, y) * 180.0 / PI
				half_width = 180.0 / len(self.items)
				for i in self.items:
					if abs(degdiff(i.a, angle)) < half_width:
						if self._selected != i:
							if self.feedback and self.controller:
								self.controller.feedback(*self.feedback)
							self.select(i)
		else:
			return Menu.on_event(self, daemon, what, data)


if __name__ == "__main__":
	import gi
	gi.require_version('Gtk', '3.0')
	gi.require_version('Rsvg', '2.0')
	gi.require_version('GdkX11', '3.0')
	
	from scc.tools import init_logging
	from scc.paths import get_share_path
	init_logging()
	
	m = RadialMenu()
	if not m.parse_argumets(sys.argv):
		sys.exit(1)
	m.run()
	if m.get_exit_code() == 0:
		print(m.get_selected_item_id())
	sys.exit(m.get_exit_code())

