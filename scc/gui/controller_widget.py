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
from scc.actions import Action, XYAction, MultiAction
from scc.gui.ae.gyro_action import is_gyro_enable
from scc.modifiers import DoubleclickModifier
from scc.profile import Profile
from scc.tools import nameof
import os, sys, logging

log = logging.getLogger("ControllerWidget")

TRIGGERS = [ "LT", "RT" ]
PADS	= [ "LPAD", "RPAD" ]
STICKS	= [ STICK ]
GYROS	= [ GYRO ]
PRESSABLE = [ SCButtons.LPAD, SCButtons.RPAD, SCButtons.STICKPRESS ]
_NOT_BUTTONS = PADS + STICKS + GYROS + TRIGGERS
_NOT_BUTTONS += [ x + "TOUCH" for x in PADS ]
BUTTONS = [ b for b in SCButtons if b.name not in _NOT_BUTTONS ]
LONG_TEXT = 12

class ControllerWidget:
	ACTION_CONTEXT = None

	def __init__(self, app, id, use_icon, widget):
		self.app = app
		self.id = id
		self.name = id if type(id) in (str, unicode) else id.name
		self.widget = widget
		
		self.label = Gtk.Label()
		self.label.set_ellipsize(Pango.EllipsizeMode.END)
		self.icon = Gtk.Image.new_from_file(self.get_image()) if use_icon else None
		self.update()
		
		self.widget.connect('enter', self.on_cursor_enter)
		self.widget.connect('leave', self.on_cursor_leave)
		self.widget.connect('clicked', self.on_click)
		self.widget.connect('button-release-event', self.on_button_release)
	
	
	def get_image(self):
		return os.path.join(self.app.imagepath, self.name + ".svg")
	
	
	def update(self):
		self.label.set_label(_("(no action)"))
	
	
	def on_click(self, *a):
		self.app.show_editor(self.id)
	
	def on_button_release(self, bt, event):
		if event.button == 3:
			# Rightclick
			self.app.show_context_menu(self.id)
	
	
	def on_cursor_enter(self, *a):
		self.app.hilight(self.name)
	
	
	def on_cursor_leave(self, *a):
		self.app.hilight(None)


class ControllerButton(ControllerWidget):
	ACTION_CONTEXT = Action.AC_BUTTON
	
	def __init__(self, app, name, use_icon, widget):
		ControllerWidget.__init__(self, app, name, use_icon, widget)
		
		if use_icon:
			vbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
			separator = Gtk.Separator(orientation = Gtk.Orientation.VERTICAL)
			vbox.pack_start(self.icon, False, False, 1)
			vbox.pack_start(separator, False, False, 1)
			vbox.pack_start(self.label, False, True, 1)
			self.widget.add(vbox)
		else:
			self.widget.add(self.label)
		self.widget.show_all()
		self.label.set_max_width_chars(12)
		if name == "C":
			self.label.set_max_width_chars(10)
	
	
	def update(self):
		if self.id in SCButtons and self.id in self.app.current.buttons:
			txt = self.app.current.buttons[self.id].describe(self.ACTION_CONTEXT)
			if len(txt) > LONG_TEXT or "\n" in txt:
				txt = "\n".join(txt.split("\n")[0:2])
				txt = txt.replace("<", "&lt;").replace(">", "&gt;")
				self.label.set_markup("<small>%s</small>" % (txt,))
			else:
				txt = txt.replace("<", "&lt;").replace(">", "&gt;")
				self.label.set_markup(txt)
		else:
			self.label.set_label(_("(no action)"))


class ControllerStick(ControllerWidget):
	ACTION_CONTEXT = Action.AC_STICK
	
	def __init__(self, app, name, use_icon, enable_press, widget):
		self.pressed = Gtk.Label() if enable_press else None
		self.click_button = SCButtons.STICKPRESS
		ControllerWidget.__init__(self, app, name, use_icon, widget)
		
		grid = Gtk.Grid()
		self.widget.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
		self.widget.connect('motion-notify-event', self.on_cursor_motion)
		self.label.set_property("vexpand", True)
		self.label.set_property("hexpand", True)
		if self.pressed:
			self.label.set_xalign(0.0); self.label.set_yalign(0.5)
			self.pressed.set_property("hexpand", True)
			self.pressed.set_xalign(0.0); self.pressed.set_yalign(1.0)
			grid.attach(self.pressed, 2, 2, 1, 1)
		else:
			self.label.set_xalign(0.5); self.label.set_yalign(0.5)
			self.pressed = None
		if self.icon:
			self.icon.set_margin_right(5)
			grid.attach(self.icon, 1, 1, 1, 2)
		grid.attach(self.label, 2, 1, 1, 1)
		self.over_icon = False
		self.enable_press = enable_press
		self.widget.add(grid)
		self.widget.show_all()
	
	
	def on_cursor_enter(self, *a):
		return
	
	
	def on_click(self, *a):
		if self.over_icon and self.enable_press:
			self.app.show_editor(self.click_button)
		else:
			self.app.show_editor(self.id)
	
	
	def on_cursor_motion(self, trash, event):
		# self.icon.get_allocation().x + self.icon.get_allocation().width	# yields nonsense
		ix2 = 74
		# Check if cursor is placed on icon
		if event.x < ix2:
			what = dict(
				LPAD = LEFT,
				RPAD = RIGHT,
				STICK = nameof(SCButtons.STICKPRESS)
			)[self.name]
			self.app.hilight(what)
			self.over_icon = True
		else:
			self.app.hilight(self.name)
			self.over_icon = False
	
	
	def _set_label(self, action):
		self.label.set_label(action.describe(self.ACTION_CONTEXT))
	
	
	def update(self):
		action = self.app.current.buttons[self.click_button]
		self._set_label(self.app.current.stick)
		if self.pressed:
			self._update_pressed(action)
	
	
	def _update_pressed(self, action):
		escape = lambda t : t.replace("<", "&lt;").replace(">", "&gt;")
		if isinstance(action, DoubleclickModifier):
			lines = []
			if action.normalaction:
				txt = action.normalaction.describe(self.ACTION_CONTEXT)
				lines.append("Pressed: %s" % (escape(txt),))
			if action.holdaction:
				txt = action.holdaction.describe(self.ACTION_CONTEXT)
				lines.append("Hold: %s" % (escape(txt),))
			self.pressed.set_markup("<small>%s</small>" % ("\n".join(lines), ))
		else:
			txt = escape(action.describe(self.ACTION_CONTEXT))
			self.pressed.set_markup("<small>Pressed: %s</small>" % (txt,))


class ControllerTrigger(ControllerButton):
	ACTION_CONTEXT = Action.AC_TRIGGER
	
	def update(self):
		# TODO: Use LT and RT in profile as well
		side = LEFT if self.id == "LT" else RIGHT
		if self.id in TRIGGERS and side in self.app.current.triggers:
			self.label.set_label(self.app.current.triggers[side].describe(self.ACTION_CONTEXT))
		else:
			self.label.set_label(_("(no action)"))


class ControllerPad(ControllerStick):
	ACTION_CONTEXT = Action.AC_PAD
	
	
	def __init__(self, app, name, use_icon, enable_press, widget):
		ControllerStick.__init__(self, app, name, use_icon, enable_press, widget)
		self.click_button = getattr(SCButtons, self.id)
	
	
	def update(self):
		if self.id == "LPAD":
			action = self.app.current.pads[Profile.LEFT]
			pressed = self.app.current.buttons[SCButtons.LPAD]
		else:
			action = self.app.current.pads[Profile.RIGHT]
			pressed = self.app.current.buttons[SCButtons.RPAD]
		
		self._set_label(action)
		if self.pressed:
			self._update_pressed(pressed)


class ControllerGyro(ControllerWidget):
	ACTION_CONTEXT = Action.AC_GYRO
	
	def __init__(self, app, name, use_icon, widget):
		self.pressed = Gtk.Label()
		ControllerWidget.__init__(self, app, name, use_icon, widget)
		
		grid = Gtk.Grid()
		self.label.set_property("vexpand", True)
		self.label.set_property("hexpand", True)
		self.label.set_xalign(0.0); self.label.set_yalign(0.5)
		self.pressed.set_property("hexpand", True)
		self.pressed.set_xalign(0.0); self.pressed.set_yalign(1.0)
		if self.icon:
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
		if is_gyro_enable(action):
			action = action.mods[action.order[0]] or action.default
		if isinstance(action, MultiAction):
			rv = []
			for a in action.actions:
				d = a.describe(self.ACTION_CONTEXT)
				if not d in rv : rv.append(d)
			self.label.set_label("\n".join(rv))
			return
		self.label.set_label(action.describe(self.ACTION_CONTEXT))
	
	
	def update(self):
		self._set_label(self.app.current.gyro)
