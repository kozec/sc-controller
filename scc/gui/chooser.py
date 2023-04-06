#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""

from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import ButtonAction, AxisAction, MouseAction, MultiAction
from scc.actions import HatLeftAction, HatRightAction
from scc.actions import HatUpAction, HatDownAction
from scc.gui.area_to_action import AREA_TO_ACTION
from scc.gui.svg_widget import SVGWidget
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
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
				image = SVGWidget(os.path.join(self.app.imagepath, self.IMAGES[id]))
				image.connect('hover', self.on_background_area_hover)
				image.connect('leave', self.on_background_area_hover, None)
				image.connect('click', self.on_background_area_click)
				self.images.append(image)
				if grid_columns:
					# Grid
					parent.attach(image, 0, 0, grid_columns, 1)
				else:
					# Box
					parent.pack_start(image, True, True, 0)
				parent.show_all()
	
	
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
