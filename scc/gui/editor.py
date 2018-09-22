#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.uinput import Keys
from scc.actions import MultiAction, HatLeftAction, HatRightAction
from scc.actions import ButtonAction, AxisAction, MouseAction
from scc.actions import HatUpAction, HatDownAction
from scc.gui.svg_widget import SVGWidget
from scc.gui.gdk_to_key import keyevent_to_key
from scc.gui.area_to_action import AREA_TO_ACTION

import os, logging
log = logging.getLogger("Editor")


class ComboSetter(object):
	
	def set_cb(self, cb, key, keyindex=0):
		"""
		Sets combobox value.
		Returns True on success or False if key is not found.
		"""
		model = cb.get_model()
		self._recursing = True
		for row in model:
			if key == row[keyindex]:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return True
		else:
			log.warning("Failed to set combobox value, key '%s' not found", key)
		self._recursing = False
		return False


class Editor(ComboSetter):
	""" Common stuff for all editor windows """
	ERROR_CSS = " #error {background-color:green; color:red;} "
	_error_css_provider = None
	
	def __init__(self):
		self.added_widget = None		# See add_widget method
	
	
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
	
	
	def hide_dont_destroy(self, w, *a):
		"""
		When used as handler for 'delete-event' signal, prevents window from
		being destroyed after closing.
		"""
		w.hide()
		return True
	
	
	def set_title(self, title):
		self.window.set_title(title)
		self.builder.get_object("header").set_title(title)
	
	
	def close(self, *a):
		self.window.destroy()
	
	
	def get_transient_for(self):
		"""
		Returns parent window for this editor. Usually main application window
		"""
		return self._transient_for
	
	
	def show(self, transient_for):
		if transient_for:
			self._transient_for = transient_for
			self.window.set_transient_for(transient_for)
			self.window.set_modal(True)
		self.window.show()
	
	
	def add_widget(self, label, widget):
		"""
		Adds new widget into row before Action Name.
		
		Widget is automatically passed to Macro Editor or Modeshift Editor
		if either one is opened from editor window.
		
		When editor window is closed or destroyed, widget is automatically
		deattached to keep it from destroying.
		"""
		lblAddedWidget = self.builder.get_object("lblAddedWidget")
		vbAddedWidget = self.builder.get_object("vbAddedWidget")
		lblAddedWidget.set_label(label)
		lblAddedWidget.set_visible(True)
		for ch in vbAddedWidget.get_children():
			vbAddedWidget.remove(ch)
		self.added_widget = widget
		vbAddedWidget.pack_start(widget, True, False, 0)
		vbAddedWidget.set_visible(True)
	
	
	def remove_added_widget(self):
		"""
		Removes added widget, if any.
		Should be called from on_destory handlers.
		"""
		vbAddedWidget = self.builder.get_object("vbAddedWidget")
		for ch in vbAddedWidget.get_children():
			vbAddedWidget.remove(ch)
		self.added_widget = None
	
	
	def send_added_widget(self, target):
		""" Transfers added widget to new editor window """
		if self.added_widget:
			vbAddedWidget  = self.builder.get_object("vbAddedWidget")
			lblAddedWidget = self.builder.get_object("lblAddedWidget")
			label = lblAddedWidget.get_label()
			w = self.added_widget
			self.remove_added_widget()
			target.add_widget(label, w)
