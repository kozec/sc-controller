#!/usr/bin/env python2
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gio, GLib
from scc.tools import get_profiles_path, find_profile, find_menu
from scc.special_actions import ShellCommandAction
from scc.profile import Profile
from scc.gui.parser import GuiActionParser

import sys, os, json, tarfile, tempfile, logging
log = logging.getLogger("IE.ImportSSCC")

class ImportSccprofile(object):
	def __init__(self):
		# _files holds list of (filename, object) generated while
		# importing and saved only after final confirmation by user
		self._files = []
	
	
	def on_btImportSccprofile_clicked(self, *a):
		# Create filters
		f1 = Gtk.FileFilter()
		f1.set_name("SC-Controller Profile or Archive")
		f1.add_pattern("*.sccprofile")
		f1.add_pattern("*.sccprofile.tar.gz")
		
		# Create dialog
		d = Gtk.FileChooserNative.new(_("Import Profile..."),
				self.window, Gtk.FileChooserAction.OPEN)
		d.add_filter(f1)
		if d.run() == Gtk.ResponseType.ACCEPT:
			if d.get_filename().endswith(".tar.gz"):
				if self.import_scc_tar(d.get_filename()):
					self.window.destroy()
			else:
				if self.import_scc(d.get_filename()):
					self.window.destroy()
	
	
	def error(self, text):
		"""
		Displays error page (reused from VDF import).
		"""
		tbError =			self.builder.get_object("tbError")
		grImportFailed =	self.builder.get_object("grImportFailed")
		
		tbError.set_text(text)
		self.next_page(grImportFailed)
	
	
	def import_scc(self, filename):
		"""
		Imports simple, single-file scc-profile.
		Just loads it, checks for shell() actions and asks user to enter name.
		"""
		# Load profile
		profile = Profile(GuiActionParser())
		try:
			profile.load(filename)
		except Exception, e:
			# Profile cannot be parsed. Display error message and let user to quit
			# Error message reuses page from VDF import, because they are
			# basically the same
			log.error(e)
			self.error(str(e))
			return False
		
		self._files = [
			( ".".join(os.path.split(filename)[-1].split(".")[0:-1]), profile )
		]
		
		# Check for shell commands
		grShellCommands =	self.builder.get_object("grShellCommands")
		tvShellCommands =	self.builder.get_object("tvShellCommands")
		model = tvShellCommands.get_model()
		model.clear()
		for a in profile.get_actions():
			if isinstance(a, ShellCommandAction):
				model.append((False, a.command))
		# If there is shell command present, jump to warning page
		if len(model) > 0:
			self.next_page(grShellCommands)
			btNext = self.enable_next(True, self.shell_import_confirmed)
			btNext.set_label(_("Continue"))
			btNext.set_sensitive(False)
		else:
			self.shell_import_confirmed()
	
	
	def on_crShellCommandChecked_toggled(self, cr, path):
		tvShellCommands =	self.builder.get_object("tvShellCommands")
		btNext =			self.builder.get_object("btNext")
		model = tvShellCommands.get_model()
		model[path][0] = not model[path][0]
		btNext.set_sensitive(True)
		for row in model:
			if not row[0]:
				btNext.set_sensitive(False)
				return
	
	
	def shell_import_confirmed(self):
		grSccImportFinished =	self.builder.get_object("grSccImportFinished")
		lblSccImportFinished =	self.builder.get_object("lblSccImportFinished")
		txName2 =				self.builder.get_object("txName2")
		
		name, obj = self._files[0]	# 1st is always profile that's being imported
		lblSccImportFinished.set_text(_("Profile sucessfully imported"))
		txName2.set_text(name)
		self.next_page(grSccImportFinished)
		self.on_txName2_changed()
	
	
	def on_txName2_changed(self, *a):
		txName2 = self.builder.get_object("txName2")
		btNext = self.enable_next(True, self.on_scc_import_confirmed)
		btNext.set_label('Apply')
		btNext.set_use_stock(True)
		if self.check_name(txName2.get_text()):
			btNext.set_sensitive(True)
			name, obj = self._files[0]	# 1st is always profile that's being imported
			name = txName2.get_text()
			self._files[0] = name, obj
		else:
			btNext.set_sensitive(False)
	
	
	def on_scc_import_confirmed(self, *a):
		for name, obj in self._files:
			if isinstance(obj, Profile):
				obj.save(os.path.join(get_profiles_path(), "%s.sccprofile" % (name,)))
		
		name, obj = self._files[0]	# 1st is always profile that's being imported
		self.app.new_profile(obj, name)
		GLib.idle_add(self.window.destroy)
