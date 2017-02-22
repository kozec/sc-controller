#!/usr/bin/env python2
"""
SC-Controller - Import / Export Dialog
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.editor import Editor, ComboSetter
from export import Export
from import_vdf import ImportVdf

import sys, os, logging
log = logging.getLogger("IE.Dialog")

class Dialog(Editor, ComboSetter, Export, ImportVdf):
	GLADE = "import_export.glade"
	
	def __init__(self, app):
		self.app = app
		self._back = []
		self.setup_widgets()
		Export.__init__(self)
		ImportVdf.__init__(self)
	
	
	def _next_page(self, page):
		stDialog = self.builder.get_object("stDialog")
		btBack = self.builder.get_object("btBack")
		self._back.append(stDialog.get_visible_child())
		stDialog.set_visible_child(page)
		btBack.set_visible(True)
		self._page_selected(page)
	
	
	def _page_selected(self, page):
		stDialog	= self.builder.get_object("stDialog")
		hbDialog	= self.builder.get_object("hbDialog")
		hbDialog.set_title(stDialog.child_get_property(page, "title"))
		hname = "on_%s_activated" % (page.get_name(),)
		if hasattr(self, hname):
			getattr(self, hname)()
	
	
	def on_btBack_clicked(self, *a):
		btBack			= self.builder.get_object("btBack")
		stDialog		= self.builder.get_object("stDialog")
		btSaveAs		= self.builder.get_object("btSaveAs")
		btNext			= self.builder.get_object("btNext")
		grSelectProfile	= self.builder.get_object("grSelectProfile")
		page, self._back = self._back[-1], self._back[:-1]
		stDialog.set_visible_child(page)
		btNext.set_visible(False)
		btSaveAs.set_visible(False)
		btBack.set_visible(len(self._back) > 0)
		self._page_selected(page)
	
	
	def on_btExport_clicked(self, *a):
		grSelectProfile	= self.builder.get_object("grSelectProfile")
		self._next_page(grSelectProfile)
		if not self._profile_load_started:
			self._profile_load_started = True
			self.load_profile_list()
	
	
	def on_btImportVdf_clicked(self, *a):
		grVdfImport	= self.builder.get_object("grVdfImport")
		self._next_page(grVdfImport)
