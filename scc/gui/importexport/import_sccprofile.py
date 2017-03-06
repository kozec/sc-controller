#!/usr/bin/env python2
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gio, GLib
from scc.tools import get_profiles_path, find_profile, find_menu
from scc.special_actions import ShellCommandAction
from scc.menu_data import MenuData
from scc.profile import Profile
from scc.gui.parser import GuiActionParser
from export import Export

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
				self.import_scc_tar(d.get_filename())
			else:
				self.import_scc(d.get_filename())
	
	
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
			return
		
		self._files = [
			( ".".join(os.path.split(filename)[-1].split(".")[0:-1]), profile )
		]
		self.check_shell_commands()
	
	
	def import_scc_tar(self, filename):
		"""
		Imports packaged profiles.
		Checks for shell() actions everywhere and ask user to
		enter main name, check generated ones and optionaly change
		them as he wish.
		"""
		try:
			# Open tar
			tar = tarfile.open(filename, "r:gz")
			self._files = []
			# Grab 1st profile
			name = tar.extractfile(Export.PN_NAME).read()
			main_profile = "%s.sccprofile" % name
			parser = GuiActionParser()
			self._files.append(( name, Profile(parser)
				.load_fileobj(tar.extractfile(main_profile))
			))
			for x in tar:
				if x.name.endswith(".sccprofile") and x.name != main_profile:
					self._files.append(( ".".join(x.name.split(".")[0:-1]),
						Profile(parser).load_fileobj(tar.extractfile(x))
					))
				elif x.name.endswith(".menu"):
					self._files.append(( ".".join(x.name.split(".")[0:-1]),
						MenuData.from_fileobj(tar.extractfile(x), parser)
					))
		except Exception, e:
			# Either entire tar or some profile cannot be parsed.
			# Display error message and let user to quit
			# Error message reuses same page as above.
			log.error(e)
			self.error(str(e))
			return
		self.check_shell_commands()
	
	
	def check_shell_commands(self):
		"""
		Check for shell commands in profiles being imported.
		If there are any shell commands found, displays warning page
		and lets user to confirm import of them.
		
		Othewise, goes straight to next page as if user already confirmed them.
		"""
		grShellCommands =	self.builder.get_object("grShellCommands")
		tvShellCommands =	self.builder.get_object("tvShellCommands")
		model = tvShellCommands.get_model()
		model.clear()
		# Get all shell commands in all profiles
		for name, obj in self._files:
			if isinstance(obj, Profile):
				for a in obj.get_actions():
					if isinstance(a, ShellCommandAction):
						model.append((False, a.command))
		
		if len(model) > 0:
			# If there is shell command present, jump to warning page
			self.next_page(grShellCommands)
			btNext = self.enable_next(True, self.shell_import_confirmed)
			btNext.set_label(_("Continue"))
			btNext.set_sensitive(False)
		else:
			# Otherwise continue to next one
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
