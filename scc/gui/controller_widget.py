#!/usr/bin/env python2
"""
SC-Controller - Controller Button

Wraps around actual button and provides code for setting actions
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Pango
from scc.constants import SCButtons
from scc.profile import Profile
import os, sys, logging

log = logging.getLogger("ControllerWidget")

TRIGGERS = [ Profile.LEFT, Profile.RIGHT ]
PADS	= [ "LPAD", "STICK", "RPAD" ]
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
		if self.id in SCButtons and self.id in self.app.current.buttons:
			self.label.set_label(self.app.current.buttons[self.id].describe(self.ACTION_CONTEXT))
		elif self.id in TRIGGERS and self.id in self.app.current.triggers:
			self.label.set_label(self.app.current.triggers[self.id].describe(self.ACTION_CONTEXT))
		else:
			self.label.set_label(_("(no action)"))


	def on_click(self, *a):
		self.app.show_editor(self.id)


	def on_cursor_enter(self, *a):
		self.app.hilight(self.name)


	def on_cursor_leave(self, *a):
		self.app.hilight(None)
