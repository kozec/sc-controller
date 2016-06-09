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

import os

class Editor(object):
	""" Common stuff for all editor windows """
	ERROR_CSS = " #error {background-color:green; color:red;} "
	_error_css_provider = None
	
	def on_window_key_press_event(self, trash, event):
		""" Checks if pressed key was escape and if yes, closes window """
		if event.keyval == Gdk.KEY_Escape:
			self.close()
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.window = self.builder.get_object("Dialog")
		self.builder.connect_signals(self)
	
	
	@staticmethod
	def install_error_css():
		if Editor._error_css_provider is None:
			Editor._error_css_provider = Gtk.CssProvider()
			Editor._error_css_provider.load_from_data(str(Editor.ERROR_CSS))
			Gtk.StyleContext.add_provider_for_screen(
					Gdk.Screen.get_default(),
					Editor._error_css_provider,
					Gtk.STYLE_PROVIDER_PRIORITY_USER)
	
	
	def set_cb(self, cb, key, keyindex=0):
		""" Sets combobox value """
		model = cb.get_model()
		self._recursing = True
		for row in model:
			if key == row[keyindex]:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return
		self._recursing = False
	
	
	def set_title(self, title):
		self.window.set_title(title)
		self.builder.get_object("header").set_title(title)
	
	
	def close(self, *a):
		self.window.destroy()
	
	
	def show(self, modal_for):
		if modal_for:
			self.window.set_transient_for(modal_for)
			self.window.set_modal(True)
		self.window.show()
