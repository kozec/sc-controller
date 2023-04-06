#!/usr/bin/env python2
"""
SC-Controller - OSD Mode Mapper

Very special case of mapper used when main application is launched in "odd mode".
That means it's drawn in OSD layer, cannot be clicked and cannot react to
keyboard. This mapper emulates input events on it using GTK methods.

Mouse movement (but not buttons) are passed to uinput as usuall.
"""

from gi.repository import Gtk, Gdk, GLib

from scc.gui.gdk_to_key import KEY_TO_GDK, KEY_TO_KEYCODE
from scc.gui.daemon_manager import ControllerManager
from scc.osd.slave_mapper import SlaveMapper
from scc.constants import SCButtons
from scc.uinput import Keys, Scans

import os, logging
log = logging.getLogger("OSDModMapper")


class OSDModeMapper(SlaveMapper):
	def __init__(self, app, profile):
		SlaveMapper.__init__(self, profile, None, keyboard="osd", mouse="osd")
		self.app = app
		self.set_special_actions_handler(self)
		self.target_window = None
	
	def on_sa_restart(self, *a):
		""" restart / exit handler """
		self.app.quit()
	
	
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
		window, event.x, event.y = Gdk.Window.at_pointer()
		screen, x, y, mask = Gdk.Display.get_default().get_pointer()
		event.x_root, event.y_root = x, y
		
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


class OSDModeMappings(object):
	
	ICONS = {
		'imgOsdmodeAct'    : SCButtons.A,
		'imgOsdmodeClose'  : SCButtons.B,
		'imgOsdmodeExit'   : SCButtons.C,
		'imgOsdmodeSave'   : SCButtons.Y,
		'imgOsdmodeOK'     : SCButtons.Y,
	}
	
	MAIN_WINDOW_BUTTONS = { "vbOsdmodeExit", "vbOsdmodeSave" }
	OTHER_WINDOW_BUTTONS = { "vbOsdmodeExit", "vbOsdmodeAct", "vbOsdmodeClose", "vbOsdmodeOK" }
	
	def __init__(self, app, mapper, window):
		self.app = app
		self.mapper = mapper
		self.window = window
		self.parent = app.window
		self.first_window = None
		GLib.timeout_add(10, self.move_around)
		self.app.window.connect("focus-in-event", self.on_main_window_focus_in_event)
		self.app.window.connect("focus-out-event", self.on_main_window_focus_out_event)
		self.on_main_window_focus_in_event()
	
	
	def set_controller(self, c):
		config = c.load_gui_config(self.app.imagepath or {})
		for name in OSDModeMappings.ICONS:
			w = self.app.builder.get_object(name)
			icon, trash = c.get_button_icon(config, OSDModeMappings.ICONS[name])
			w.set_from_file(icon)
	
	
	def on_main_window_focus_in_event(self, *a):
		for x in self.OTHER_WINDOW_BUTTONS:
			self.app.builder.get_object(x).set_visible(False)
		for x in self.MAIN_WINDOW_BUTTONS:
			self.app.builder.get_object(x).set_visible(True)
	
	
	def on_main_window_focus_out_event(self, *a):
		for x in self.MAIN_WINDOW_BUTTONS:
			self.app.builder.get_object(x).set_visible(False)
		for x in self.OTHER_WINDOW_BUTTONS:
			self.app.builder.get_object(x).set_visible(True)
	
	
	def get_target_position(self):
		pos = self.first_window.get_position()
		size = self.first_window.get_geometry()
		my_size = self.window.get_window().get_geometry()
		tx = (pos.x + 0.5 * (size.width - my_size.width))
		ty = pos.y + size.height + 100
		return tx, ty
	
	
	def show(self):
		self.window.show()
		self.window.get_window().set_override_redirect(True)
	
	
	def move_around(self, *a):
		if self.first_window is None:
			active = self.window.get_window().get_screen().get_active_window()
			if active is None:
				return
			else:
				self.first_window = active
		
		tx, ty = self.get_target_position()
		self.window.get_window().move(tx, ty)
		return True


def direction(x):
	if x >= 1:
		return 1
	elif x <= -1:
		return -1
	return 0
