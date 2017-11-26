#!/usr/bin/env python2
"""
SC-Controller - OSD Mode Mapper

Very special case of mapper used when main application is launched in "odd mode".
That means it's drawn in OSD layer, cannot be clicked and cannot react to
keyboard. This mapper emulates input events on it using GTK methods.

Mouse movement (but not buttons) are passed to uinput as usuall.
"""
from __future__ import unicode_literals
from gi.repository import Gtk, Gdk

from scc.gui.gdk_to_key import KEY_TO_GDK, KEY_TO_KEYCODE
from scc.osd.slave_mapper import SlaveMapper
from scc.uinput import Keys, Scans


import logging, time
log = logging.getLogger("OSDModMapper")


class OSDModeMapper(SlaveMapper):
	def __init__(self, profile):
		SlaveMapper.__init__(self, profile, None, keyboard="osd", mouse="osd")
		self.target_window = None
	
	
	def set_target_window(self, w):
		self.target_window = w
	
	
	def create_keyboard(self, name):
		return OSDModeKeyboard(self)
	
	
	def create_mouse(self, name):
		return OSDModeMouse(self)


class OSDModeKeyboard(object):
	""" Emulates uinput keyboard emulator """
	
	def __init__(self, mapper):
		self.mapper = mapper
		self.display = Gdk.Display.get_default()
		self.manager = self.display.get_device_manager()
		self.device = [ x for x in
			self.manager.list_devices(Gdk.DeviceType.MASTER)
			if x.get_source() == Gdk.InputSource.KEYBOARD
		][0]	
	
	def pressEvent(self, keys):
		for k in keys:
			event = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
			event.time = Gtk.get_current_event_time()
			event.hardware_keycode = KEY_TO_KEYCODE[k]
			event.keyval = KEY_TO_GDK[k]
			event.window = self.mapper.target_window
			event.set_device(self.device)
			Gtk.main_do_event(event)
	
	
	def releaseEvent(self, keys=[]):
		for k in keys:
			event = Gdk.Event.new(Gdk.EventType.KEY_RELEASE)
			event.time = Gtk.get_current_event_time()
			event.hardware_keycode = KEY_TO_KEYCODE[k]
			event.keyval = KEY_TO_GDK[k]
			event.window = self.mapper.target_window
			event.set_device(self.device)
			Gtk.main_do_event(event)


class OSDModeMouse(object):
	""" Emulates uinput keyboard emulator too """
	
	def __init__(self, mapper):
		self.mapper = mapper
		self.display = Gdk.Display.get_default()
		self.manager = self.display.get_device_manager()
		self.device = [ x for x in
			self.manager.list_devices(Gdk.DeviceType.MASTER)
			if x.get_source() == Gdk.InputSource.MOUSE
		][0]
	
	
	def synEvent(self, *a):
		pass
	
	
	def keyEvent(self, key, val):
		tp = Gdk.EventType.BUTTON_PRESS if val else Gdk.EventType.BUTTON_RELEASE
		event = Gdk.Event.new(tp)
		event.button = int(key) - Keys.BTN_LEFT + 1
		window, wx, wy = Gdk.Window.at_pointer()
		screen, x, y, mask = Gdk.Display.get_default().get_pointer()
		event.x_root, event.y_root = x, y
		event.x, event.y = x - wx, y - wy
		gtk_window = None
		for w in Gtk.Window.list_toplevels():
			if w.get_window():
				if window.get_toplevel().get_xid() == w.get_window().get_xid():
					gtk_window = w
					break
		if gtk_window:
			if gtk_window.get_type_hint() == Gdk.WindowTypeHint.COMBO:
				# Special case, clicking on combo does nothing, so
				# pressing "space" is emulated instead.
				if not val:
					return
				event = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
				event.time = Gtk.get_current_event_time()
				event.hardware_keycode = 65
				event.keyval = Gdk.KEY_space
				event.window = self.mapper.target_window
		event.time = Gtk.get_current_event_time()
		event.window = window
		event.set_device(self.device)
		Gtk.main_do_event(event)
