#!/usr/bin/env python2
"""
SC-Controller - Menu Editor

Edits .menu files and menus stored in profile.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
import os, logging
log = logging.getLogger("MenuEditor")


class MenuEditor(Editor):
	GLADE = "menu_editor.glade"

	def __init__(self, app, callback):
		self.app = app
		Editor.install_error_css()
		self.setup_widgets()
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.window = self.builder.get_object("Dialog")
		self.builder.connect_signals(self)
		headerbar(self.builder.get_object("header"))
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		pass
	
	
	def set_menu(self, id):
		"""
		Setups editor for menu with specified ID.
		ID may be id of menu in profile or, if it contains ".", filename.
		"""
		self.set_title(_("Menu Editor"))
		rbGlobal = self.builder.get_object("rbGlobal")
		rbInProfile = self.builder.get_object("rbInProfile")
		entName = self.builder.get_object("entName")
		
		if "." in id:
			rbGlobal.set_active(True)
			entName.set_text("Aa/Sccc/Emas")
			items = []
		else:
			rbInProfile.set_active(True)
			entName.set_text(id)
			items = self.app.current.menus[id]
		
		for i in items:
			print i

