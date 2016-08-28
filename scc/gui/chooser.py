#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import ButtonAction, AxisAction, MouseAction, MultiAction
from scc.actions import HatLeftAction, HatRightAction
from scc.actions import HatUpAction, HatDownAction
from scc.constants import LEFT, RIGHT, STICK_PAD_MAX
from scc.gui.area_to_action import AREA_TO_ACTION
from scc.gui.svg_widget import SVGWidget
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
from scc.osd import create_cursors
from scc.tools import clamp
import os, logging
log = logging.getLogger("Chooser")

AXIS_ACTION_CLASSES = (AxisAction, MouseAction, HatLeftAction, HatRightAction, HatUpAction, HatDownAction)

class Chooser(Editor):
	IMAGES = {}
	
	ACTIVE_COLOR = "#FF00FF00"	# ARGB
	HILIGHT_COLOR = "#FFFF0000"	# ARGB
	
	def __init__(self, app):
		self.app = app
		self.active_area = None		# Area that is permanently hilighted on the image
		self.images = []
		self.axes_allowed = True
		self.mouse_allowed = True
	
	
	def setup_image(self, grid_columns=0):
		for id in self.IMAGES:
			parent = self.builder.get_object(id)
			if parent is not None:
				image = SVGWidget(self.app, os.path.join(self.app.imagepath, self.IMAGES[id]))
				image.connect('hover', self.on_background_area_hover)
				image.connect('leave', self.on_background_area_hover, None)
				image.connect('click', self.on_background_area_click)
				self.images.append(image)
				att = image
				if self.app.osd_controller:
					self.fixed = att = Gtk.Fixed()
					self.fixed.add(image)
				if grid_columns:
					# Grid
					parent.attach(att, 0, 0, grid_columns, 1)
				else:
					# Box
					parent.pack_start(att, True, True, 0)
				parent.show_all()
				# TODO: Multiple images? Is that even used anywhere?
				break
	
	
	def align_image(self):
		"""
		Used only in OSD mode, when image is flaced inside of Gtk.Fixed.
		Alings said image to center of parent.
		"""
		self.align_x = (self.fixed.get_allocated_width() / 2) - (self.images[0].get_allocated_width() / 2)
		self.fixed.move(self.images[0], self.align_x, 0)
	
	
	def enable_cursors(self, controller):
		"""
		Used only in OSD mode.
		Creates and displays two cursor images.
		"""
		self.cursors = create_cursors()
		self.fixed.add(self.cursors[LEFT])
		self.fixed.add(self.cursors[RIGHT])
		controller.connect('pad-move', self.on_cursor_move)
		controller.connect('pad-click', self.on_cursor_press)
	
	
	def on_cursor_move(self, controller, what, x, y):
		x = (1.0 + (x / float(STICK_PAD_MAX))) * 0.30
		y = (1.0 + (y / float(STICK_PAD_MAX) * -1.0)) * 0.5
		# TODO: Really, remove that multiimage thing...
		x = x * self.images[0].get_allocated_width()
		y = clamp(0, y, 0.9) * self.images[0].get_allocated_height()
		if what != LEFT:
			x += (self.images[0].get_allocated_width() * 0.4)
		self.cursors[what].pos = x, y

		event = Gdk.EventKey()
		event.x, event.y = x, y
		self.images[0].on_mouse_moved(None, event)

		x += self.align_x 
		
		self.fixed.move(self.cursors[what], x, y)
	
	
	def on_cursor_press(self, controller, what):
		event = Gdk.EventKey()
		event.x, event.y = self.cursors[what].pos
		self.images[0].on_mouse_click(None, event)
	
	
	def set_active_area(self, a):
		"""
		Sets area that is permanently hilighted on image.
		"""
		self.active_area = a
		for i in self.images:
			i.hilight({ self.active_area : Chooser.ACTIVE_COLOR })
	
	
	def on_background_area_hover(self, background, area):
		if area in AREA_TO_ACTION:
			if AREA_TO_ACTION[area][0] in AXIS_ACTION_CLASSES:
				if not self.axes_allowed:
					return
			if not self.mouse_allowed and "MOUSE" in area :
				return
		background.hilight({
			self.active_area : Chooser.ACTIVE_COLOR,
			area : Chooser.HILIGHT_COLOR
		})
	
	
	def on_background_area_click(self, trash, area):
		"""
		Called when user clicks on defined area on gamepad image.
		"""
		if area in AREA_TO_ACTION:
			cls, params = AREA_TO_ACTION[area][0], AREA_TO_ACTION[area][1:]
			if not self.axes_allowed and cls in AXIS_ACTION_CLASSES:
				return
			if not self.mouse_allowed and "MOUSE" in area :
				return
			self.area_action_selected(area, cls(*params))
		else:
			log.warning("Click on unknown area: %s" % (area,))
	
	
	def area_action_selected(self, area, action):
		raise Exception("Override me!")
	
	
	def hide_axes(self):
		""" Prevents user from selecting axes """
		self.axes_allowed = False
	
	
	def hide_mouse(self):
		""" Prevents user from selecting mouse-related stuff """
		self.mouse_allowed = False
