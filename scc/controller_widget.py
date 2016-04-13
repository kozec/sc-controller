#!/usr/bin/env python2
"""
SC-Controller - Controller Button

Wraps around actual button and provides code for setting actions
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk
import os, sys, logging
from scc.constants import SCButtons

log = logging.getLogger("ControllerWidget")

class ControllerWidget:
	def __init__(self, app, id, widget):
		self.app = app
		self.id = id
		self.name = id if type(id) in (str, unicode) else id.name
		self.widget = widget
		
		filename = os.path.join(self.app.iconpath, self.name + ".svg")
		self.label = Gtk.Label()
		self.icon = Gtk.Image.new_from_file(filename)
		self.update()
		
		self.widget.connect('enter', self.on_cursor_enter)
		self.widget.connect('leave', self.on_cursor_leave)
		self.widget.connect('clicked', self.on_click)
	
	def update(self):
		if self.id in SCButtons:
			if self.id in self.app.current.buttons:
				self.label.set_label(self.app.current.buttons[self.id].describe())
			else:
				self.label.set_label(_("(no action)"))
	
	
	def on_click(self, *a):
		self.app.show_editor(self.id)
	
	
	def on_cursor_enter(self, *a):
		self.app.hilight(self.name)
	
	
	def on_cursor_leave(self, *a):
		self.app.hilight(None)
