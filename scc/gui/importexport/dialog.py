#!/usr/bin/env python2
"""
SC-Controller - Import / Export Dialog
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.editor import Editor, ComboSetter
from export import Export
from import_vdf import ImportVdf
from import_sccprofile import ImportSccprofile

import sys, os, logging
log = logging.getLogger("IE.Dialog")

class Dialog(Editor, ComboSetter, Export, ImportVdf, ImportSccprofile):
	GLADE = "import_export.glade"
	
	def __init__(self, app):
		self.app = app
		self._back = []
		self._recursing = False
		self.setup_widgets()
		Export.__init__(self)
		ImportVdf.__init__(self)
		ImportSccprofile.__init__(self)
	
	
	def next_page(self, page):
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
	
	
	def enable_next(self, enabled=True):
		""" Returns button object """
		btNext = self.builder.get_object("btNext")
		btNext.set_visible(enabled)
		btNext.set_label(_("Next"))
		return btNext
	
	
	def on_btNext_clicked(self, *a):
		stDialog		= self.builder.get_object("stDialog")
		hname = "on_%s_next" % (stDialog.get_visible_child().get_name(),)
		if hasattr(self, hname):
			self.enable_next(enabled=False)
			getattr(self, hname)()
	
	
	def on_btBack_clicked(self, *a):
		btBack			= self.builder.get_object("btBack")
		stDialog		= self.builder.get_object("stDialog")
		btSaveAs		= self.builder.get_object("btSaveAs")
		btSaveVdf		= self.builder.get_object("btSaveVdf")
		btNext			= self.builder.get_object("btNext")
		page, self._back = self._back[-1], self._back[:-1]
		stDialog.set_visible_child(page)
		btNext.set_visible(False)
		btSaveAs.set_visible(False)
		btSaveVdf.set_visible(False)
		btBack.set_visible(len(self._back) > 0)
		self._page_selected(page)
	
	
	def on_btExport_clicked(self, *a):
		grSelectProfile	= self.builder.get_object("grSelectProfile")
		self.next_page(grSelectProfile)
	
	
	def on_btImportVdf_clicked(self, *a):
		grVdfImport	= self.builder.get_object("grVdfImport")
		self.next_page(grVdfImport)
