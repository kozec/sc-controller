#!/usr/bin/env python2
"""
SC-Controller - OSDAPPController

Locks gamepad inputs and allows application to be controlled by gamepad.

Instance of OSDAPPController is created by scc.app.App; Then, every window that
is supposed to be controlled by gamepad calls set_window method (closing
is handled with signals). This thing then scans entire widget hierarchy
for selectable widgets and does some css magic to change color of selected one.
"""

from gi.repository import Gtk, Gdk, GLib
from scc.gui.gdk_to_key import KEY_TO_GDK, HW_TO_KEY
from scc.constants import SCButtons, LEFT, RIGHT
from scc.osd import OSDWindow, StickController
from scc.uinput import Keys

import os, logging
log = logging.getLogger("OSDAppCtrl")

KEY_TO_HW = { HW_TO_KEY[x] : x for x in HW_TO_KEY }
BUTTON_IMAGES = { x : "%s.svg" % (x.name,) for x in SCButtons }
BUTTON_IMAGES.update({ x : "%s_color.svg" % (x.name,) for x in (SCButtons.A, SCButtons.B,
	SCButtons.X, SCButtons.Y) })
BUTTON_IMAGES.update({ x : "%s_small.svg" % (x.name,) for x in (SCButtons.BACK,) })

class OSDAppController(object):
	def __init__(self, app):
		self.dm = app.dm
		self.imagepath = app.imagepath
		self.app = app
		self.dm.lock(self.on_input_lock_success, self.on_input_lock_failed,
			*[ x.name for x in SCButtons ])
		self.scon = StickController()
		self.dm.connect('event', self.on_input_event)
		self.scon.connect("direction", self.on_stick_direction)
		self.window = None
		OSDWindow.install_css(app.config)
	
	
	def on_input_lock_failed(self, *a):
		log.error("Failed to lock input, cannot enter OSD mode")
		self.app.quit()
	
	
	def on_input_lock_success(self, *a):
		log.info("Entered OSD mode")
	
	
	def keypress(self, key, modifiers=0, type=Gdk.EventType.KEY_PRESS):
		event = Gdk.EventKey()
		event.type = type
		event.window = self.window.window.get_window()
		event.time = Gdk.CURRENT_TIME
		event.state = modifiers
		event.keyval = KEY_TO_GDK[key]
		event.hardware_keycode = KEY_TO_HW[key]
		Gdk.Display.get_default().put_event(event)
		#if type == Gdk.EventType.KEY_PRESS:
		#	GLib.idle_add(self.keypress, key, Gdk.EventType.KEY_RELEASE)
	
	
	def on_stick_direction(self, trash, x, y):
		# Hard-coded numbers are taken from gdk_to_key.py
		if y < 0:
			if isinstance(self.window.window.get_focus(), (Gtk.ComboBox, Gtk.ToggleButton, Gtk.Scale)):
				self.keypress(Keys.KEY_TAB, modifiers=Gdk.ModifierType.SHIFT_MASK)
			else:
				self.keypress(Keys.KEY_UP)
		elif y > 0:
			if isinstance(self.window.window.get_focus(), (Gtk.ComboBox, Gtk.ToggleButton, Gtk.Scale)):
				self.keypress(Keys.KEY_TAB)
			else:
				self.keypress(Keys.KEY_DOWN)
		if x > 0:
			self.keypress(Keys.KEY_LEFT)
		elif x < 0:
			self.keypress(Keys.KEY_RIGHT)
	
	
	def set_window(self, window, *buttons):
		self.window = window
		self.window.window.set_name("osd-app")
		header = window.builder.get_object("header")
		if header:
			for w in [] + header.get_children():
				header.remove(w)
				header.set_show_close_button(False)
				header.set_title(None)
				header.set_has_subtitle(False)
				header.set_decoration_layout("")
			
			for b, side, label in buttons:
				image = Gtk.Image.new_from_file(os.path.join(self.imagepath, BUTTON_IMAGES[b]))
				markup = "<b>%s</b>" % label
				label = Gtk.Label()
				label.set_markup(markup)
				if side == LEFT:
					header.pack_start(image)
					header.pack_start(label)
				else:
					header.pack_end(label)
					header.pack_end(image)
			header.show_all()
	
	
	def on_input_event(self, daemon, what, data):
		if what == "STICK":
			self.scon.set_stick(*data)
		elif what == "A" and data[0] == 1:
			w = self.window.window.get_focus()
			if isinstance(w, Gtk.Button):
				self.keypress(Keys.KEY_SPACE)
		elif what in ("RB", "LB") and data[0] == 1:
			if hasattr(self.window, "on_shoulder"):
				self.window.on_shoulder(what)
		elif what == "B":
			self.keypress(Keys.KEY_ESC)
