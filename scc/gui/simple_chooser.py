#!/usr/bin/env python2
"""
SC-Controller - Simple Chooser

Used by Action Editor to display window with just one Component
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.gui.dwsnc import headerbar
from scc.gui.ae import AEComponent
from scc.gui.editor import Editor
import logging, os, types, importlib
log = logging.getLogger("SimpleChooser")

class SimpleChooser(Editor):
	GLADE = "simple_chooser.glade"
	
	def __init__(self, app, component_name, callback):
		self.app = app
		self._action = None
		self.component = None
		self.callback = callback
		self.setup_widgets()
		self.load_component(component_name)
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.window = self.builder.get_object("Dialog")
		self.builder.connect_signals(self)
		headerbar(self.builder.get_object("header"))
	
	
	def load_component(self, component_name):
		mod = importlib.import_module("scc.gui.ae.%s" % (component_name,))
		for x in dir(mod):
			cls = getattr(mod, x)
			if isinstance(cls, (type, types.ClassType)) and issubclass(cls, AEComponent):
				if cls.NAME == component_name:
					self.component = cls(self.app, self)
					break
		if self.component is None:
			raise ValueError("Unknown component '%s'" % (component_name,))
		self.component.load()
		self.window.add(self.component.get_widget())
	
	
	def display_action(self, mode, action):
		self._action = action
		self.component.set_action(mode, action)
	
	
	def set_action(self, action):
		self.callback(action)
		self.close()
		self.window.destroy()


	def hide_axes(self):
		""" Prevents user from selecting axes """
		self.component.hide_axes()
