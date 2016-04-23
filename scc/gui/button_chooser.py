#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.uinput import Keys
from scc.actions import ButtonAction, AxisAction, MouseAction, MultiAction
from scc.actions import HatLeftAction, HatRightAction
from scc.actions import HatUpAction, HatDownAction
from scc.gui.svg_widget import SVGWidget
from scc.gui.gdk_to_key import keyevent_to_key
from scc.gui.area_to_action import AREA_TO_ACTION
import os, logging
log = logging.getLogger("ButtonChooser")

AXIS_ACTION_CLASSES = (AxisAction, MouseAction, HatLeftAction, HatRightAction, HatUpAction, HatDownAction)
MODIFIERS = [ Keys.KEY_LEFTCTRL, Keys.KEY_LEFTMETA, Keys.KEY_LEFTALT,
	Keys.KEY_RIGHTALT, Keys.KEY_RIGHTMETA, Keys.KEY_RIGHTCTRL,
	Keys.KEY_LEFTSHIFT, Keys.KEY_RIGHTSHIFT
]


def merge_modifiers(mods):
	return "+".join([ key.name.split("_")[-1] for key in mods ])

class ButtonChooser(object):
	GLADE = "button_chooser.glade"
	GLADE_KG = "key_grabber.glade"
	IMAGES = { "vbButChooser" : "buttons.svg" }
	
	ACTIVE_COLOR = "#FF00FF00"	# ARGB
	HILIGHT_COLOR = "#FFFF0000"	# ARGB
	
	def __init__(self, app, callback=None):
		self.app = app
		self.axes_allowed = False
		self.active_mods = []
		self.active_area = None		# Area that is permanently hilighted on the image
		self.images = []
		self.setup_widgets()
		self.callback = callback
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE_KG))
		self.window = self.builder.get_object("Dialog")
		self.keygrab = self.builder.get_object("KeyGrab")
		self.builder.connect_signals(self)
		
		for id in self.IMAGES:
			parent = self.builder.get_object(id)
			if parent is not None:
				image = SVGWidget(self.app, os.path.join(self.app.imagepath, self.IMAGES[id]))
				image.connect('hover', self.on_background_area_hover)
				image.connect('leave', self.on_background_area_hover, None)
				image.connect('click', self.on_background_area_click)
				self.images.append(image)
				parent.pack_start(image, True, True, 0)
				parent.show_all()
	
	
	def allow_axes(self):
		""" Allows axes to be selectable """
		self.axes_allowed = True
	
	
	def set_active_area(self, a):
		"""
		Sets area that is permanently hilighted on image.
		"""
		self.active_area = a
		for i in self.images:
			i.hilight({ self.active_area : ButtonChooser.ACTIVE_COLOR })
	
	
	def on_background_area_hover(self, background, area):
		if area in AREA_TO_ACTION:
			if AREA_TO_ACTION[area][0] in AXIS_ACTION_CLASSES:
				if not self.axes_allowed:
					return
		background.hilight({
			self.active_area : ButtonChooser.ACTIVE_COLOR,
			area : ButtonChooser.HILIGHT_COLOR
		})
	
	
	def on_window_key_press_event(self, trash, event):
		""" Checks if pressed key was escape and if yes, closes window """
		if event.keyval == Gdk.KEY_Escape:
			self.close()
	
	
	def on_keyGrab_key_press_event(self, trash, event):
		"""
		Handles keypress on "Grab Key" dialog.
		
		Remembers modifiers and displays text in middle of dialog.
		Dialog is dismissed (and key is accepted) by key_release handler bellow.
		"""
		key = keyevent_to_key(event)
		if key is None:
			log.warning("Unknown keycode %s/%s" % (event.keyval, event.hardware_keycode))
			return
		
		if key in MODIFIERS:
			self.active_mods.append(key)
			self.builder.get_object("tg" + key.name).set_active(True)
			self.builder.get_object("lblKey").set_label(merge_modifiers(self.active_mods))
			return
		
		label = merge_modifiers(self.active_mods)
		if len(self.active_mods) > 0:
			label = label + "+" + key.name
		else:
			label = key.name
		self.builder.get_object("lblKey").set_label(label)
	
	
	def on_keyGrab_key_release_event(self, trash, event):
		"""
		Handles keyrelease on "Grab Key" dialog.
		
		Key is accepted if either:
		- released key is not modifier
		- released key is modifier, but there is no other modifier key pressed
		
		Calls on_key_grabbed if key is accepted
		"""
		key = keyevent_to_key(event)
		if key is not None:
			if key in MODIFIERS:
				if key in self.active_mods:
					if len(self.active_mods) == 1:
						# Releasing last modifier
						self.on_key_grabbed([key])
						return
					self.active_mods.remove(key)
					self.builder.get_object("tg" + key.name).set_active(False)
				self.builder.get_object("lblKey").set_label("+".join([key.name.split("_")[-1] for key in self.active_mods]))
				return
			
			self.on_key_grabbed(self.active_mods + [key])
	
	
	def on_tgkey_toggled(self, obj, *a):
		"""
		Handles when user clicks on modifier buttons in "Grab Key" dialog
		"""
		for key in MODIFIERS:
			if self.builder.get_object("tg" + key.name) == obj:
				if obj.get_active() and not key in self.active_mods:
					self.active_mods.append(key)
					self.builder.get_object("lblKey").set_label(merge_modifiers(self.active_mods))
				elif not obj.get_active() and key in self.active_mods:
					self.active_mods.remove(key)
					self.builder.get_object("lblKey").set_label(merge_modifiers(self.active_mods))
				return
	
	
	def on_btnGrabKey_clicked(self, *a):
		"""
		Called when user clicks on 'Grab a Key' button.
		Displays additional dialog.
		"""
		self.active_mods = []
		self.keygrab.set_transient_for(self.window)
		self.keygrab.set_modal(True)
		self.builder.get_object("lblKey").set_label("...")
		for key in MODIFIERS:
			self.builder.get_object("tg" + key.name).set_active(False)
		self.keygrab.show()
		self.keygrab.set_focus()
	
	
	def on_background_area_click(self, trash, area):
		"""
		Called when user clicks on defined area on gamepad image.
		"""
		if self.callback is not None:
			if area in AREA_TO_ACTION:
				cls, params = AREA_TO_ACTION[area][0], AREA_TO_ACTION[area][1:]
				if not self.axes_allowed and cls in AXIS_ACTION_CLASSES:
					return
				self.callback(cls(params))
			else:
				log.warning("Click on unknown area: %s" % (area,))
	
	
	def on_key_grabbed(self, keys):
		""" Handles selecting key using "Grab the Key" dialog """
		if self.callback is not None:
			if len(keys) == 1:
				self.callback(ButtonAction([keys[0]]))
			else:
				actions = [ ButtonAction([k]) for k in keys ]
				self.callback(MultiAction(*actions))
		self.keygrab.hide()
	
	
	def set_title(self, title):
		self.window.set_title(title)
		self.builder.get_object("header").set_title(title)
	
	
	def close(self, *a):
		self.window.destroy()
	
	
	def show(self, modal_for):
		self.window.set_transient_for(modal_for)
		self.window.set_modal(True)
		self.window.show()
