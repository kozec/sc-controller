#!/usr/bin/env python2
"""
SC-Controller - Icon Chooser
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib, GObject
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
import os, traceback, logging
log = logging.getLogger("IconChooser")

class IconChooser(Editor):
	GLADE = "icon_chooser.glade"

	def __init__(self, app, callback):
		self.app = app
		self.setup_widgets()
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		headerbar(self.builder.get_object("header"))
