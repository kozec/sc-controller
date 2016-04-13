#!/usr/bin/env python2
"""
SC-Controller - Controller Button

Wraps around actual button and provides code for setting actions
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk
from scc.actions import Action
from scc.gui.controller_widget import ControllerWidget
import logging

log = logging.getLogger("ControllerButton")

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


class ControllerTrigger(ControllerButton):
	ACTION_CONTEXT = Action.AC_TRIGGER
