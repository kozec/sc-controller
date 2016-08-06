#!/usr/bin/env python2
"""
SC-Controller - OSDAPPController

Locks gamepad inputs and allows application to be controlled by gamepad.

Instance of OSDAPPController is created by App; Then, every window that is
supposed to be controlled by gamepad calls set_window method (closing
is handled with signals.) This thing then scans entire widget hierarchy
for selectable widgets and does some css magic to change color of selected one.
"""

from gi.repository import Gtk
from scc.osd import OSDWindow, StickController

import logging
log = logging.getLogger("OSDAppCtrl")

class OSDAppController(object):
	def __init__(self, app):
		self.dm = app.dm
		self.dm.lock(self.on_input_lock_success, self.on_input_lock_failed,
			"LEFT", "RIGHT", "STICK")
		self.scon = StickController()
		self.dm.connect('event', self.on_input_event)
		self.scon.connect("direction", self.on_stick_direction)
		self.map = {}
	
	
	def on_input_event(self, daemon, what, data):
		if what == "STICK":
			self.scon.set_stick(*data)
	
	
	def on_input_lock_failed(self, *a):
		log.error("Failed to lock input, cannot enter OSD mode")
		self.app.quit()
	
	
	def on_input_lock_success(self, *a):
		log.info("Entered OSD mode")
	
	
	def on_stick_direction(self, trash, x, y):
		print self.window.get_focus()
	
	
	def set_window(self, window):
		def scan_grid(x, y, grid):
			children = {
				(grid.child_get_property(child, 'left-attach'),
				grid.child_get_property(child, 'top-attach'))
				: child
				for child in grid.get_children() }
			maxw = max(*[ w for w, h in children])
			maxh = max(*[ h for w, h in children])
			for j in xrange(0, maxh + 1):
				for i in xrange(0, maxw + 1):
					if (i, j) in children:
						trash, y = scan(x + i, y, children[(i, j)])
				y += 1
			return x, y
		
		def scan_vbox(x, y, children):
			for child in children:
				x, y = scan(x, y, child)
				y += 1
			return x, y
		
		
		def scan_hbox(x, y, children):
			for child in children:
				x, y = scan(x, y, child)
				x += 1
			return x, y
		
		
		def scan(x, y, widget):
			if not widget.is_visible():
				return x, y
			elif isinstance(widget, Gtk.Window):
				x, y = scan_vbox(x, y, sorted(widget.get_children(),
					key = lambda x : not isinstance(x, Gtk.HeaderBar)))
			elif isinstance(widget, Gtk.Box):
				if widget.get_orientation() == Gtk.Orientation.HORIZONTAL:
					x, y = scan_hbox(x, y, widget.get_children())
				else:
					x, y = scan_vbox(x, y, widget.get_children())
			elif isinstance(widget, Gtk.Grid):
				x, y = scan_grid(x, y, widget)
			elif isinstance(widget, Gtk.Button):
				print x, y, widget
			else:
				print "(ignored)", widget
			return x, y
		
		self.map = {}
		scan(0, 0, window)
