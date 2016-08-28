#!/usr/bin/env python2
"""
SC-Controller - OSDAPPController

Locks gamepad inputs and allows application to be controlled by gamepad.

Instance of OSDAPPController is created by scc.app.App; Then, every window that
is supposed to be controlled by gamepad calls set_window method (closing
is handled with signals). This thing then scans entire widget hierarchy
for selectable widgets and does some css magic to change color of selected one.
"""

from gi.repository import Gtk, Gdk, GLib, GObject
from scc.gui.gdk_to_key import KEY_TO_GDK, HW_TO_KEY
from scc.constants import SCButtons, LEFT, RIGHT
from scc.osd import OSDWindow, StickController
from scc.osd.slave_mapper import SlaveMapper
from scc.osd.keyboard import Keyboard
from scc.uinput import Keys

import os, logging
log = logging.getLogger("OSDAppCtrl")

KEY_TO_HW = { HW_TO_KEY[x] : x for x in HW_TO_KEY }
BUTTON_IMAGES = { x : "%s.svg" % (x.name,) for x in SCButtons }
BUTTON_IMAGES.update({ x : "%s_color.svg" % (x.name,) for x in (SCButtons.A, SCButtons.B,
	SCButtons.X, SCButtons.Y) })
BUTTON_IMAGES.update({ x : "%s_small.svg" % (x.name,) for x in (SCButtons.BACK,) })

class OSDAppController(GObject.GObject):
	__gsignals__ = {
			# Raised as user moves finger(s) on pad(s)
			b"pad-move"		: (GObject.SIGNAL_RUN_FIRST, None, (str,int,int)),
			b"pad-click"	: (GObject.SIGNAL_RUN_FIRST, None, (str,)),
	}
	
	def __init__(self, app):
		GObject.GObject.__init__(self)
		self.dm = app.dm
		self.imagepath = app.imagepath
		self.app = app
		self.dm.lock(self.on_input_lock_success, self.on_input_lock_failed,
			LEFT, RIGHT, *[ x.name for x in SCButtons ])
		self.scon = StickController()
		self.child_window = None
		self.dm.connect('event', self.on_input_event)
		self.scon.connect("direction", self.on_stick_direction)
		self.stack = []
		self.window = None
	
	
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
	
	
	def set_window(self, window, *buttons):
		self.window = window
		self.window.window.set_name("osd-app")
		self.stack.append(self.window)
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
		self.window.window.connect('destroy', self.on_window_closed)
	
	
	def on_window_closed(self, *a):
		self.stack = self.stack[0:-1]
		self.window = self.stack[-1]
		print "W CLOSED", "window is now ", self.window
	
	
	@staticmethod
	def find_cls_in_parents(cls, w):
		"""
		Returns 'w' if 'w' is instance of 'cls'.
		If not, returns nearest parent that is instance of 'cls' or None, if
		there is no such parent.
		"""
		if w is None:
			return None
		if isinstance(w, cls):
			return w
		return OSDAppController.find_cls_in_parents(cls, w.get_parent())
	
	
	@staticmethod
	def is_open_combobox(w):
		"""
		Returns Ture if 'w' is ComboBox and it's open (rolled out).
		"""
		return (
			OSDAppController.find_cls_in_parents(Gtk.ComboBox, w)
			and OSDAppController.find_cls_in_parents(Gtk.ToggleButton, w)
			and OSDAppController.find_cls_in_parents(Gtk.ToggleButton, w).get_active()
		)
	
	
	def on_stick_direction(self, trash, x, y):
		# Hard-coded numbers are taken from gdk_to_key.py
		w = self.window.window.get_focus()
		if OSDAppController.is_open_combobox(w):
			if y < 0:
				self.keypress(Keys.KEY_UP)
			elif y > 0:
				self.keypress(Keys.KEY_DOWN)
		elif isinstance(w, (Gtk.ComboBox, Gtk.ToggleButton, Gtk.Scale, Gtk.SpinButton)):
			if y < 0:
				self.keypress(Keys.KEY_TAB, modifiers=Gdk.ModifierType.SHIFT_MASK)
			elif y > 0:
				self.keypress(Keys.KEY_TAB)
			elif isinstance(w, Gtk.SpinButton):
				if x > 0:
					self.keypress(Keys.KEY_DOWN)
				elif x < 0:
					self.keypress(Keys.KEY_UP)
			else:
				if x > 0:
					self.keypress(Keys.KEY_UP)
				elif x < 0:
					self.keypress(Keys.KEY_DOWN)
		else:
			if y < 0:
				self.keypress(Keys.KEY_UP)
			elif y > 0:
				self.keypress(Keys.KEY_DOWN)
			if x > 0:
				self.keypress(Keys.KEY_LEFT)
			elif x < 0:
				self.keypress(Keys.KEY_RIGHT)
	
	
	def on_input_event(self, daemon, what, data):
		if self.child_window:
			# OSK is displayed
			return
		if what == "STICK":
			self.scon.set_stick(*data)
		elif what == "A" and data[0] == 1:
			w = self.window.window.get_focus()
			if isinstance(w, Gtk.Entry):
				self.open_osk()
			elif isinstance(w, (Gtk.Button, Gtk.Expander)):
				self.keypress(Keys.KEY_SPACE)
		elif what in ("RB", "LB") and data[0] == 1:
			if hasattr(self.window, "on_shoulder"):
				self.window.on_shoulder(what)
		elif what == "B" and data[0] == 0:
			self.keypress(Keys.KEY_ESC)
		elif what in (LEFT, RIGHT):
			self.emit("pad-move", what, *data)
		elif what in ("LPAD", "RPAD"):
			self.emit("pad-click", LEFT if what == "LPAD" else RIGHT)
	
	
	def on_keyboard_closed(self, *a):
		self.child_window = None
	
	
	def open_osk(self, *a):
		self.child_window = AppCtrlKeyboard(self)
		self.child_window.connect('destroy', self.on_keyboard_closed)
		self.child_window.show()
		self.child_window.use_daemon(self.dm)


class AppCtrlKeyboard(Keyboard):
	def __init__(self, parent):
		self.parent = parent
		Keyboard.__init__(self, parent.app.config)
	
	
	def create_mapper(self):
		# This OSK doesn't need to emulate actual keyboard
		self.mapper = SlaveMapper(self.profile)
		self.mapper.set_special_actions_handler(self)
	
	
	def lock_inputs(self):
		# Inputs are already locked by OSDAppController
		pass
	
	
	def unlock_inputs(self):
		# OSDAppController still needs those inputs locked
		pass
	
	
	def key_from_cursor(self, cursor, pressed):
		x, y = cursor.position
		
		if pressed:
			for a in self.background.areas:
				if a.contains(x, y):
					if a.name.startswith("KEY_") and hasattr(Keys, a.name):
						key = getattr(Keys, a.name)
						#if self._pressed[cursor] is not None:
						#	self.mapper.keyboard.releaseEvent([ self._pressed[cursor] ])
						self.parent.keypress(key)
						self._pressed[cursor] = key
						self._pressed_areas[cursor] = a
					break
		elif self._pressed[cursor] is not None:
			# self.mapper.keyboard.releaseEvent([ self._pressed[cursor] ])
			self._pressed[cursor] = None
			del self._pressed_areas[cursor]
		if not self.timer_active('redraw'):
			self.timer('redraw', 0.01, self.redraw_background)
