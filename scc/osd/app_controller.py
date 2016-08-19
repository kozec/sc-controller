#!/usr/bin/env python2
"""
SC-Controller - OSDAPPController

Locks gamepad inputs and allows application to be controlled by gamepad.

Instance of OSDAPPController is created by scc.app.App; Then, every window that
is supposed to be controlled by gamepad calls set_window method (closing
is handled with signals). This thing then scans entire widget hierarchy
for selectable widgets and does some css magic to change color of selected one.
"""

from gi.repository import Gtk, Gdk
from scc.gui.gdk_to_key import KEY_TO_GDK, HW_TO_KEY
from scc.constants import SCButtons, LEFT, RIGHT
from scc.osd import OSDWindow, StickController
from scc.uinput import Keys

import os, logging
log = logging.getLogger("OSDAppCtrl")

KEY_TO_HW = { HW_TO_KEY[x] : x for x in HW_TO_KEY }
COLORED_BUTTONS = SCButtons.A, SCButtons.B, SCButtons.X, SCButtons.Y

class OSDAppController(object):
	def __init__(self, app):
		self.dm = app.dm
		self.imagepath = app.imagepath
		self.app = app
		self.dm.lock(self.on_input_lock_success, self.on_input_lock_failed,
			"LEFT", "RIGHT", "STICK", "A", "B", "X", "Y")
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
	
	
	def keypress(self, key):
		event = Gdk.EventKey()
		event.type = Gdk.EventType.KEY_PRESS
		event.window = self.window.get_window()
		event.time = Gdk.CURRENT_TIME
		event.state = 0
		event.keyval = KEY_TO_GDK[key]
		event.hardware_keycode = KEY_TO_HW[key]
		Gdk.Display.get_default().put_event(event)
		event.type = Gdk.EventType.KEY_RELEASE
	
	
	def on_stick_direction(self, trash, x, y):
		# Hard-coded numbers are taken from gdk_to_key.py
		if y > 0:
			self.keypress(Keys.KEY_DOWN)
		elif y < 0:
			self.keypress(Keys.KEY_UP)
		if x > 0:
			self.keypress(Keys.KEY_LEFT)
		elif x < 0:
			self.keypress(Keys.KEY_RIGHT)
	
	
	def set_window(self, window, *buttons):
		self.window = window.window
		self.window.set_name("osd-app")
		headerbar = window.builder.get_object("headerbar")
		if headerbar:
			for w in [] + headerbar.get_children():
				headerbar.remove(w)
				headerbar.set_show_close_button(False)
				headerbar.set_title(None)
				headerbar.set_has_subtitle(False)
				headerbar.set_decoration_layout("")
			
			for b, side, label in buttons:
				if b in COLORED_BUTTONS:
					image = Gtk.Image.new_from_file(os.path.join(self.imagepath,
						"%s_color.svg" % (b.name,)))
					markup = "<b>%s</b>" % label
					label = Gtk.Label()
					label.set_markup(markup)
					if side == LEFT:
						headerbar.pack_start(image)
						headerbar.pack_start(label)
					else:
						headerbar.pack_end(label)
						headerbar.pack_end(image)
			headerbar.show_all()
	
	
	def on_input_event(self, daemon, what, data):
		if what == "STICK":
			self.scon.set_stick(*data)
		elif what == "A":
			self.keypress(Keys.KEY_SPACE)
		elif what == "B":
			self.keypress(Keys.KEY_ESC)
