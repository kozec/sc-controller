#!/usr/bin/env python2
"""
SC-Controller - Gesture-related GUI stuff.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GLib, GObject
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX
from collections import deque

import math, logging
log = logging.getLogger("Gestures")


class GestureDraw(Gtk.DrawingArea):
	GRID_PAD = 10
	MAX_STEPS = 5
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
		# hilights = [ [0] * resolution for x in xrange(0, resolution) ]

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
		for x, y in reversed(self._detector.get_positions()):
			if step > self.MAX_STEPS:
				break
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


class GestureCellRenderer(Gtk.CellRenderer):
	__gproperties__ = {
		b'gesture': (GObject.TYPE_STRING, b"Gesture", b"Gesture", b"", GObject.PARAM_READWRITE),
	}
	
	SIZE = 64, 64
	PADDING = 0.1
	def __init__(self):
		Gtk.CellRenderer.__init__(self)
		self.gesture = ""
		self.resolution = 3
	
	
	def do_get_size(self, widget, cell_area):
		return 0, 0, self.SIZE[0], self.SIZE[1]
	
	
	def do_set_property(self, prop, value):
		self.gesture = value
	
	
	def do_render(self, cr, widget, background_area, ca, flags):
		ctx = widget.get_style_context()
		Gtk.render_background(ctx, cr, ca.x, ca.y, ca.width, ca.height)
		
		# Determine stroke (one segment of gesture) size
		sw = float(ca.width)  / self.resolution
		sh = float(ca.height) / self.resolution
		
		# Determine total gesture size
		x, y = 0, 0
		mx, my, xx, xy = 0, 0, 0, 0
		for c in self.gesture:
			if c == 'L': x -= 1
			elif c == 'R': x += 1
			elif c == 'U': y -= 1
			elif c == 'D': y += 1
			mx = min(x, mx)
			my = min(y, my)
			xx = max(x, xx)
			xy = max(y, xy)
		gw = xx - mx
		gh = xy - my
		
		# Determine starting point
		x = ca.x + ca.width  * 0.5 - gw * sw * 0.5
		y = ca.y + ca.height * 0.5 + gh * sh * 0.5
		
		# Draw gesture
		ox, oy = x, y
		for c in self.gesture:
			if c == 'U':
				y -= sh
				x += 2
				Gtk.render_arrow(ctx, cr, 0, x - 3.5, y - 2, 8)
				Gtk.render_line(ctx, cr, ox, oy, x, y)
			elif c == 'D':
				y += sh
				x += 2
				Gtk.render_arrow(ctx, cr, GLib.PI, x - 3.5, y - 2, 8)
				Gtk.render_line(ctx, cr, ox, oy, x, y)
			elif c == 'R':
				x += sw
				y += 2
				Gtk.render_arrow(ctx, cr, GLib.PI * 0.5, x - 4, y - 3.5, 8)
				Gtk.render_line(ctx, cr, ox, oy, x, y)
			elif c == 'L':
				x -= sw
				y += 2
				Gtk.render_arrow(ctx, cr, GLib.PI * 1.5, x - 4, y - 3.5, 8)
				Gtk.render_line(ctx, cr, ox, oy, x, y)
			ox, oy = x, y
