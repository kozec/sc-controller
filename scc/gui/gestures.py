#!/usr/bin/env python2
"""
SC-Controller - Gesture-related GUI stuff.
"""

from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GLib, GObject
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX
from scc.osd import parse_rgba
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
	
	
	def set_colors(self, background="000000FF", line="FF00FFFF",
			grid="7A7A7AFF", hilight="0030AAFF", **a):
		""" Expects colors in RRGGBB, as stored in config file """
		self.colors = {
			'background' :	parse_rgba(background),
			'line' : 		parse_rgba(line),
			'grid' : 		parse_rgba(grid),
			'hilight':		parse_rgba(hilight),
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
		for i in range(1, resolution):
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
