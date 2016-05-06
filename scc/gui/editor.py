#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.uinput import Keys
from scc.actions import ButtonAction, AxisAction, MouseAction, MultiAction
from scc.actions import HatLeftAction, HatRightAction
from scc.actions import HatUpAction, HatDownAction
from scc.gui.svg_widget import SVGWidget
from scc.gui.gdk_to_key import keyevent_to_key
from scc.gui.area_to_action import AREA_TO_ACTION

class Editor(object):
	""" Common stuff for all editor windows """
	
	def on_window_key_press_event(self, trash, event):
		""" Checks if pressed key was escape and if yes, closes window """
		if event.keyval == Gdk.KEY_Escape:
			self.close()
	
	
	def set_title(self, title):
		self.window.set_title(title)
		self.builder.get_object("header").set_title(title)
	
	
	def close(self, *a):
		self.window.destroy()
	
	
	def show(self, modal_for):
		self.window.set_transient_for(modal_for)
		self.window.set_modal(True)
		self.window.show()
