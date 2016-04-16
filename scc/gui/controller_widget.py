#!/usr/bin/env python2
"""
SC-Controller - Controller Widget

Button that user can click to choose emulated action for physical button, axis
or pad.

Wraps around actual button defined in glade file.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Pango
from scc.constants import SCButtons
from scc.actions import Action
from scc.profile import Profile
import os, sys, logging

log = logging.getLogger("ControllerWidget")

TRIGGERS = [ Profile.LEFT, Profile.RIGHT ]
PADS	= [ "LPAD", "RPAD" ]
STICKS	= [ "STICK" ]
_NOT_BUTTONS = PADS + [ "LT", "RT" ] + [ x + "TOUCH" for x in PADS ]
BUTTONS = [ b for b in SCButtons if b.name not in _NOT_BUTTONS ]

class ControllerWidget:
	ACTION_CONTEXT = None

	def __init__(self, app, id, widget):
		self.app = app
		self.id = id
		self.name = id if type(id) in (str, unicode) else id.name
		self.widget = widget

		filename = os.path.join(self.app.iconpath, self.name + ".svg")
		self.label = Gtk.Label()
		self.label.set_ellipsize(Pango.EllipsizeMode.END)
		self.icon = Gtk.Image.new_from_file(filename)
		self.update()

		self.widget.connect('enter', self.on_cursor_enter)
		self.widget.connect('leave', self.on_cursor_leave)
		self.widget.connect('clicked', self.on_click)


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
			self.label.set_label(self.app.current.buttons[self.id].describe(self.ACTION_CONTEXT))
		else:
			self.label.set_label(_("(no action)"))


class ControllerStick(ControllerWidget):
	ACTION_CONTEXT = Action.AC_STICK
	def __init__(self, app, name, widget):
		ControllerWidget.__init__(self, app, name, widget)
		
		vbox = Gtk.Box(Gtk.Orientation.HORIZONTAL)
		vbox.pack_start(self.icon, False, False, 1)
		vbox.pack_start(self.label, False, False, 1)
		self.widget.add(vbox)
		self.widget.show_all()
	
	
	def _set_label(self, stickdata):
		if Profile.WHOLE in stickdata:
			self.label.set_label(stickdata[Profile.WHOLE].describe(self.ACTION_CONTEXT))
		elif Profile.X in stickdata or Profile.Y in stickdata:
			txt = []
			for i in [Profile.X, Profile.Y]:
				if i in stickdata:
					txt.append(stickdata[i].describe(self.ACTION_CONTEXT))
			self.label.set_label("\n".join(txt))
		else:
			self.label.set_label(_("(no action)"))
	
	
	def update(self):
		self._set_label(self.app.current.stick)


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
			self._set_label(self.app.current.pads[Profile.LEFT])
		else:
			self._set_label(self.app.current.pads[Profile.RIGHT])
