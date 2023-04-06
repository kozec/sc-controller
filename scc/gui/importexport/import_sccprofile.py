#!/usr/bin/env python2

from scc.tools import _

from gi.repository import Gtk, Gio, GLib, GObject
from scc.tools import get_profiles_path, get_menus_path, find_profile, find_menu
from scc.special_actions import ChangeProfileAction, MenuAction
from scc.special_actions import ShellCommandAction
from scc.profile import Profile, Encoder
from scc.menu_data import MenuData
from scc.gui.parser import GuiActionParser
from .export import Export

import sys, os, json, tarfile, tempfile, logging
log = logging.getLogger("IE.ImportSSCC")

class ImportSccprofile(object):
	
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
		files = self.builder.get_object("lstImportPackage")
		# Load profile
		profile = Profile(GuiActionParser())
		try:
			profile.load(filename)
		except Exception as e:
			# Profile cannot be parsed. Display error message and let user to quit
			# Error message reuses page from VDF import, because they are
			# basically the same
			log.error(e)
			self.error(str(e))
			return
		
		name = ".".join(os.path.split(filename)[-1].split(".")[0:-1])
		files.clear()
		o = GObject.GObject()
		o.obj = profile
		files.append(( 2, name, name, _("(profile)"), o ))
		
		self.check_shell_commands()
	
	
	def import_scc_tar(self, filename):
		"""
		Imports packaged profiles.
		Checks for shell() actions everywhere and ask user to
		enter main name, check generated ones and optionaly change
		them as he wish.
		"""
		files = self.builder.get_object("lstImportPackage")
		try:
			# Open tar
			tar = tarfile.open(filename, "r:gz")
			files.clear()
			# Grab 1st profile
			name = tar.extractfile(Export.PN_NAME).read()
			main_profile = "%s.sccprofile" % name
			parser = GuiActionParser()
			o = GObject.GObject()
			o.obj = Profile(parser).load_fileobj(tar.extractfile(main_profile))
			files.append(( 2, name, name, _("(profile)"), o ))
			for x in tar:
				name = ".".join(x.name.split(".")[0:-1])
				if x.name.endswith(".sccprofile") and x.name != main_profile:
					o = GObject.GObject()
					o.obj = Profile(parser).load_fileobj(tar.extractfile(x))
					files.append(( True, name, name, _("(profile)"), o ))
				elif x.name.endswith(".menu"):
					o = GObject.GObject()
					o.obj = MenuData.from_fileobj(tar.extractfile(x), parser)
					files.append(( True, name, name, _("(menu)"), o ))
		except Exception as e:
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
		files =				self.builder.get_object("lstImportPackage")
		model = tvShellCommands.get_model()
		model.clear()
		# Get all shell commands in all profiles
		for trash, trash, trash, trash, obj in files:
			if isinstance(obj.obj, Profile):
				for a in obj.obj.get_all_actions():
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
		files =					self.builder.get_object("lstImportPackage")
		vbImportPackage =		self.builder.get_object("vbImportPackage")
		
		enabled, trash, name, trash, obj = files[0]
		lblSccImportFinished.set_text(_("Profile sucessfully imported"))
		txName2.set_text(name)
		vbImportPackage.set_visible(len(files) > 1)
		self.next_page(grSccImportFinished)
		self.on_txName2_changed()
	
	
	def on_txName2_changed(self, *a):
		txName2 =			self.builder.get_object("txName2")
		btNext =			self.enable_next(True, self.on_scc_import_confirmed)
		files =				self.builder.get_object("lstImportPackage")
		cbImportHidden =	self.builder.get_object("cbImportPackageHidden")
		cbImportVisible =	self.builder.get_object("cbImportPackageVisible")
		cbImportNone =		self.builder.get_object("cbImportPackageNone")
		rvAdvanced =		self.builder.get_object("rvImportPackageAdvanced")
		btNext.set_label('Apply')
		btNext.set_use_stock(True)
		main_name = txName2.get_text().decode("utf-8")
		if self.check_name(main_name):
			btNext.set_sensitive(True)
		else:
			btNext.set_sensitive(False)
		
		cbImportHidden.set_label(_("Import as hidden menus and profiles named \".%s:name\"") % (main_name,))
		cbImportVisible.set_label(_("Import normaly, with names formated as \"%s:name\"") % (main_name,))
		
		for i in range(0, len(files)):
			enabled, name, importas, type, obj = files[i]
			if enabled == 2:
				importas = main_name
			elif cbImportHidden.get_active():
				importas = ".%s:%s" % (main_name, name)
				enabled = 1
			elif cbImportVisible.get_active():
				importas = "%s:%s" % (main_name, name)
				enabled = 1
			elif cbImportNone.get_active():
				enabled = 0
			files[i] = enabled, name, importas, type, obj
	
	
	def on_cbImportPackageAdvanced_toggled(self, *a):
		rvImportPackageAdvanced =	self.builder.get_object("rvImportPackageAdvanced")
		cbImportPackageAdvanced =	self.builder.get_object("cbImportPackageAdvanced")
		rvImportPackageAdvanced.set_reveal_child(cbImportPackageAdvanced.get_active())
	
	
	def on_crIPKGEnabled_toggled(self, renderer, path):
		files = self.builder.get_object("lstImportPackage")
		i = int(path)
		enabled, name, importas, type, obj = files[i]
		# 1st rown cannot be toggled
		if enabled != 2:
			enabled = 1 if enabled == 0 else 0
			files[i] = enabled, name, importas, type, obj
	
	
	def on_crIPKGImportAs_edited(self, renderer, path, new_name):
		files =		self.builder.get_object("lstImportPackage")
		txName2 =	self.builder.get_object("txName2")
		i = int(path)
		enabled, name, importas, type, obj = files[i]
		importas = new_name
		if enabled == 2:
			txName2.set_text(importas)
		files[i] = enabled, name, importas, type, obj
	
	
	def on_scc_import_confirmed(self, *a):
		files =		self.builder.get_object("lstImportPackage")
		new_profile_names = {}
		new_menu_names = {}
		for enabled, name, importas, trash, obj in files:
			if enabled != 0:
				if isinstance(obj.obj, Profile):
					new_profile_names[name] = importas
				elif isinstance(obj.obj, MenuData):
					new_menu_names["%s.menu" % (name,)] = "%s.menu" % (importas,)
		
		def apply_replacements(obj):
			for a in obj.get_all_actions():
				if isinstance(a, ChangeProfileAction):
					if a.profile in new_profile_names:
						a.profile = new_profile_names[a.profile]
						a.parameters = tuple([ a.profile ] + list(a.parameters[1:]))
				elif isinstance(a, MenuAction):
					if a.menu_id in new_menu_names:
						a.menu_id = new_menu_names[a.menu_id]
						a.parameters = tuple([ a.menu_id ] + list(a.parameters[1:]))
		
		for enabled, trash, importas, trash, obj in files:
			if enabled != 0:
				# TODO: update references
				if isinstance(obj.obj, Profile):
					apply_replacements(obj.obj)
					obj.obj.save(os.path.join(get_profiles_path(), "%s.sccprofile" % (importas,)))
				elif isinstance(obj.obj, MenuData):
					apply_replacements(obj.obj)
					jstr = Encoder(sort_keys=True, indent=4).encode(obj.obj)
					filename = os.path.join(get_menus_path(), "%s.menu" % (importas,))
					open(filename, "w").write(jstr)
		
		trash, trash, importas, trash, obj = files[0]	# 1st is always profile that's being imported
		self.app.new_profile(obj.obj, importas)
		GLib.idle_add(self.window.destroy)
