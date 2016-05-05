#!/usr/bin/env python2
"""
SC-Controller - Controller Widget

Button that user can click to choose emulated action for physical button, axis
or pad.

Wraps around actual button defined in glade file.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, Pango
from scc.constants import SCButtons, STICK, GYRO, LEFT, RIGHT
from scc.actions import Action, XYAction
from scc.profile import Profile
import os, sys, logging

log = logging.getLogger("ControllerWidget")

TRIGGERS = [ Profile.LEFT, Profile.RIGHT ]
PADS	= [ "LPAD", "RPAD" ]
STICKS	= [ STICK ]
GYROS	= [ GYRO ]
PRESSABLE = [ SCButtons.LPAD, SCButtons.RPAD, SCButtons.STICK ]
_NOT_BUTTONS = PADS + STICKS + GYROS + [ "LT", "RT" ] 
_NOT_BUTTONS += [ x + "TOUCH" for x in PADS ]
BUTTONS = [ b for b in SCButtons if b.name not in _NOT_BUTTONS ]
LONG_TEXT = 12

class ControllerWidget:
	ACTION_CONTEXT = None

	def __init__(self, app, id, widget):
		self.app = app
		self.id = id
		self.name = id if type(id) in (str, unicode) else id.name
		self.widget = widget
		
		self.label = Gtk.Label()
		self.label.set_ellipsize(Pango.EllipsizeMode.END)
		self.icon = Gtk.Image.new_from_file(self.get_image())
		self.update()
		
		self.widget.connect('enter', self.on_cursor_enter)
		self.widget.connect('leave', self.on_cursor_leave)
		self.widget.connect('clicked', self.on_click)
	
	
	def get_image(self):
		return os.path.join(self.app.imagepath, self.name + ".svg")
	
	
	def update(self):
		self.label.set_label(_("(no action)"))
	
	
	def on_click(self, *a):
		self.app.show_editor(self.id)
	
	
	def on_cursor_enter(self, *a):
		self.app.hilight(self.name)
	
	
	def on_cursor_leave(self, *a):
		self.app.hilight(None)


class ControllerButton(ControllerWidget):
	ACTION_CONTEXT = Action.AC_BUTTON

	def __init__(self, app, name, widget):
		ControllerWidget.__init__(self, app, name, widget)

		vbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
		separator = Gtk.Separator(orientation = Gtk.Orientation.VERTICAL)
		vbox.pack_start(self.icon, False, False, 1)
		vbox.pack_start(separator, False, False, 1)
		vbox.pack_start(self.label, False, True, 1)
		self.widget.add(vbox)
		self.widget.show_all()
		self.label.set_max_width_chars(12)
		if name == "C":
			self.label.set_max_width_chars(10)
	
	
	def update(self):
		if self.id in SCButtons and self.id in self.app.current.buttons:
			txt = self.app.current.buttons[self.id].describe(self.ACTION_CONTEXT)
			if len(txt) > LONG_TEXT or "\n" in txt:
				txt = "\n".join(txt.split("\n")[0:2])
				self.label.set_markup("<small>%s</small>" % (txt,))
			else:
				self.label.set_label(txt)
		else:
			self.label.set_label(_("(no action)"))


class ControllerStick(ControllerWidget):
	ACTION_CONTEXT = Action.AC_STICK
	def __init__(self, app, name, widget):
		self.pressed = Gtk.Label()
		ControllerWidget.__init__(self, app, name, widget)
		
		grid = Gtk.Grid()
		self.widget.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
		self.widget.connect('motion-notify-event', self.on_cursor_motion)
		self.label.set_property("vexpand", True)
		self.label.set_property("hexpand", True)
		self.label.set_xalign(0.0); self.label.set_yalign(0.5)
		self.pressed.set_property("hexpand", True)
		self.pressed.set_xalign(0.0); self.pressed.set_yalign(1.0)
		self.icon.set_margin_right(5)
		grid.attach(self.icon, 1, 1, 1, 2)
		grid.attach(self.label, 2, 1, 1, 1)
		grid.attach(self.pressed, 2, 2, 1, 1)
		self.over_icon = False
		self.widget.add(grid)
		self.widget.show_all()
	
	
	def on_cursor_enter(self, *a):
		return
	
	
	def on_click(self, *a):
		if self.over_icon:
			self.app.show_editor(getattr(SCButtons, self.id), True)
		else:
			self.app.show_editor(self.id)
	
	
	def on_cursor_motion(self, trash, event):
		# self.icon.get_allocation().x + self.icon.get_allocation().width	# yields nonsense
		ix2 = 74
		# Check if cursor is placed on icon
		if event.x < ix2:
			self.app.hilight(self.name + "_press")
			self.over_icon = True
		else:
			self.app.hilight(self.name)
			self.over_icon = False
	
	
	def _set_label(self, action):
		self.label.set_label(action.describe(self.ACTION_CONTEXT))
	
	
	def update(self):
		action = self.app.current.buttons[SCButtons.STICK]
		self._set_label(self.app.current.stick)
		self.pressed.set_markup("<small>Pressed: %s</small>" % (action.describe(self.ACTION_CONTEXT),))


class ControllerTrigger(ControllerButton):
	ACTION_CONTEXT = Action.AC_TRIGGER
	def update(self):
		if self.id in TRIGGERS and self.id in self.app.current.triggers:
			self.label.set_label(self.app.current.triggers[self.id].describe(self.ACTION_CONTEXT))
		else:
			self.label.set_label(_("(no action)"))


class ControllerPad(ControllerStick):
	ACTION_CONTEXT = Action.AC_PAD
	def update(self):
		if self.id == "LPAD":
			action = self.app.current.pads[Profile.LEFT]
			pressed = self.app.current.buttons[SCButtons.LPAD]
		else:
			action = self.app.current.pads[Profile.RIGHT]
			pressed = self.app.current.buttons[SCButtons.RPAD]
		
		self._set_label(action)
		self.pressed.set_markup("<small>Pressed: %s</small>" % (pressed.describe(self.ACTION_CONTEXT),))


class ControllerGyro(ControllerWidget):
	ACTION_CONTEXT = Action.AC_GYRO
	def __init__(self, app, name, widget):
		self.pressed = Gtk.Label()
		ControllerWidget.__init__(self, app, name, widget)
		
		grid = Gtk.Grid()
		self.label.set_property("vexpand", True)
		self.label.set_property("hexpand", True)
		self.label.set_xalign(0.0); self.label.set_yalign(0.5)
		self.pressed.set_property("hexpand", True)
		self.pressed.set_xalign(0.0); self.pressed.set_yalign(1.0)
		self.icon.set_margin_right(5)
		grid.attach(self.icon, 1, 1, 1, 2)
		grid.attach(self.label, 2, 1, 1, 1)
		grid.attach(self.pressed, 2, 2, 1, 1)
		self.over_icon = False
		self.widget.add(grid)
		self.widget.show_all()
	
	
	def on_click(self, *a):
		self.app.show_editor(self.id)
	
	
	def _set_label(self, action):
		self.label.set_label(action.describe(self.ACTION_CONTEXT))
	
	
	def update(self):
		self._set_label(self.app.current.gyro)
