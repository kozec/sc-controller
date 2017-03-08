#!/usr/bin/env python2
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gio
from scc.gui.userdata_manager import UserDataManager
from scc.tools import get_profiles_path, find_profile, find_menu
from scc.special_actions import ChangeProfileAction, MenuAction
from scc.tools import profile_is_default, menu_is_default
from scc.parser import ActionParser, TalkingActionParser
from scc.menu_data import MenuData, Submenu
from scc.profile import Profile

import sys, os, json, tarfile, tempfile, logging
log = logging.getLogger("IE.Export")

class Export(UserDataManager):
	TP_MENU = 0
	TP_PROFILE = 1
	PN_NAME = "profile-name"

	def __init__(self):
		self.__profile_load_started = False
	
	
	def on_grSelectProfile_activated(self, *a):
		# Not an event handler, called from page_selected
		if not self.__profile_load_started:
			self.__profile_load_started = True
			self.load_profile_list()
		self.on_tvProfiles_cursor_changed()
	
	
	def on_profile_selected(self, *a):
		grMakePackage	= self.builder.get_object("grMakePackage")
		btSaveAs		= self.builder.get_object("btSaveAs")		
		btSaveAs.set_visible(True)
		self.next_page(grMakePackage)

	
	def on_profiles_loaded(self, lst):
		tvProfiles = self.builder.get_object("tvProfiles")
		model = tvProfiles.get_model()
		current = self.app.get_current_profile()
		i, current_index = 0, -1
		for f in sorted(lst, key=lambda f: f.get_basename()):
			name = f.get_basename()
			if name.endswith(".mod"):
				continue
			if name.startswith("."):
				continue
			if name.endswith(".sccprofile"):
				name = name[0:-11]
			if name == current:
				current_index = i
			model.append((i, f, name))
			i += 1
		if current_index >= 0:
			tvProfiles.set_cursor((current_index,))
	
	
	def _add_refereced_profile(self, model, giofile, used):
		"""
		Loads profile file and recursively adds all profiles and menus
		referenced by it into 'package' list.
		
		Returns True on success or False if something cannot be parsed.
		"""
		# Load & parse selected profile and check every action in it
		profile = Profile(ActionParser())
		try:
			profile.load(giofile.get_path())
		except Exception, e:
			# Profile that cannot be parsed shouldn't be exported
			log.error(e)
			return False
		
		for action in profile.get_all_actions():
			self._parse_action(model, action, used)
		
		for menu in profile.menus:
			for item in profile.menus[menu]:
				if isinstance(item, Submenu):
					self._add_refereced_menu(model, os.path.split(item.filename)[-1], used)
				if hasattr(item, "action"):
					self._parse_action(model, item.action, used)
		return True
	
	
	def _add_refereced_menu(self, model, menu_id, used):
		"""
		As _add_refereced_profile, but reads and parses menu file.
		"""
		if "." in menu_id and menu_id not in used:
			# Dot in id means filename
			used.add(menu_id)
			filename = find_menu(menu_id)
			name = ".".join(menu_id.split(".")[0:-1])
			if name.startswith(".") and menu_is_default(menu_id):
				# Default and hidden, don't bother user with it
				return
			if filename:
				model.append((not menu_is_default(menu_id), _("Menu"), name,
						filename, True, self.TP_MENU))
				try:
					menu = MenuData.from_file(filename, ActionParser())
				except Exception, e:
					# Menu that cannot be parsed shouldn't be exported
					log.error(e)
					return
				for item in menu:
					if isinstance(item, Submenu):
						self._add_refereced_menu(model, os.path.split(item.filename)[-1], used)
					if hasattr(item, "action"):
						self._parse_action(model, item.action, used)
			else:
				model.append((False, _("Menu"), _("%s (not found)") % (name,),
						"", False, self.TP_MENU))
	
	
	def _parse_action(self, model, action, used):
		"""
		Common part of _add_refereced_profile and _add_refereced_menu
		"""
		if isinstance(action, ChangeProfileAction):
			if action.profile not in used:
				filename = find_profile(action.profile)
				used.add(action.profile)
				if filename:
					model.append((not profile_is_default(action.profile),
						_("Profile"), action.profile, filename, True, self.TP_PROFILE))
					self._add_refereced_profile(model,
						Gio.File.new_for_path(filename), used)
				else:
					model.append((False, _("Profile"),
						_("%s (not found)") % (action.profile,), "",
						False, self.TP_PROFILE))
		elif isinstance(action, MenuAction):
			self._add_refereced_menu(model, action.menu_id, used)
	
	
	def on_tvProfiles_cursor_changed(self, *a):
		"""
		Called when user selects profile.
		"""
		tvProfiles	= self.builder.get_object("tvProfiles")
		tvPackage	= self.builder.get_object("tvPackage")
		btSaveAs	= self.builder.get_object("btSaveAs")
		btClose		= self.builder.get_object("btClose")
		
		package = tvPackage.get_model()
		package.clear()
		used = set()
		
		model, iter = tvProfiles.get_selection().get_selected()
		if iter:
			giofile = model[iter][1]
			s = self._add_refereced_profile(package, giofile, used)
			if self._needs_package():
				# Profile references other menus or profiles
				self.enable_next(True, self.on_profile_selected)
				btSaveAs.set_visible(False)
			else:
				# Profile can be exported directly
				self.enable_next(enabled=False)
				btSaveAs.set_visible(True)
		else:
			# Nothing selected
				self.enable_next(enabled=False)
				btSaveAs.set_visible(False)
	
	
	def _needs_package(self):
		"""
		Returns True if there is any file checked on 2nd page,
		meaning that profile has to be exported as archive.
		"""
		tvPackage = self.builder.get_object("tvPackage")
		package = tvPackage.get_model()
		return any([ row[0] for row in package ])
	
	
	def on_btSelectAll_clicked(self, *a):
		tvPackage = self.builder.get_object("tvPackage")
		package = tvPackage.get_model()
		for row in package:
			if row[4]:	# if enabled
				row[0] = True	# then selected
	
	
	def on_crPackageCheckbox_toggled(self, cr, path):
		tvPackage = self.builder.get_object("tvPackage")
		package = tvPackage.get_model()
		package[path][0] = not package[path][0]
	
	
	def on_btSaveAs_clicked(self, *a):
		# Grab stuff
		tvProfiles	= self.builder.get_object("tvProfiles")
		model, iter = tvProfiles.get_selection().get_selected()
		
		# Determine format
		f = Gtk.FileFilter()
		if self._needs_package():
			f.set_name("SC-Controller Profile Archive")
			fmt = "sccprofile.tar.gz"
		else:
			f.set_name("SC-Controller Profile")
			fmt = "sccprofile"
		f.add_pattern("*.%s" % (fmt,))
		
		# Create dialog
		d = Gtk.FileChooserNative.new(_("Export to File..."),
				self.window, Gtk.FileChooserAction.SAVE)
		d.add_filter(f)
		d.set_do_overwrite_confirmation(True)
		# Set default filename
		d.set_current_name("%s.%s" % (model[iter][2], fmt))
		if d.run() == Gtk.ResponseType.ACCEPT:
			fn = d.get_filename()
			if len(os.path.split(fn)[-1].split(".")) < 2:
				# User wrote filename without extension
				fn = "%s.%s" % (fn, fmt)
			
			if self._needs_package():
				if self._export_package(model[iter][1], fn):
					self.window.destroy()
			else:
				if self._export(model[iter][1], fn):
					self.window.destroy()
	
	
	def _export(self, giofile, target_filename):
		"""
		Performs actual exporting.
		This method is used when only profile with no referenced files
		is to be exported and works pretty simple - load, parse, save in new file.
		"""
		profile = Profile(TalkingActionParser())
		try:
			profile.load(giofile.get_path())
		except Exception, e:
			# Profile that cannot be parsed shouldn't be exported
			log.error(e)
			return False
		
		profile.save(target_filename)
		return True
	
	
	def _export_package(self, giofile, target_filename):
		"""
		Performs actual exporting.
		This method is used when profile is to be exported _with_ some
		referenced files. It reads not only passed giofile, but all files
		marked on 2nd page of export dialog.
		
		Both profiles and menus are parsed before saving, but menu actions are
		not parsed, so it is possible (but not very probable) to export
		invalid menu file with this.
		"""
		tvPackage = self.builder.get_object("tvPackage")
		package = tvPackage.get_model()
		tar = tarfile.open(target_filename, "w:gz")
		
		def export_profile(tar, filename):
			profile = Profile(TalkingActionParser())
			try:
				out = tempfile.NamedTemporaryFile()
				profile.load(filename)
				profile.save(out.name)
				tar.add(out.name, arcname=os.path.split(filename)[-1], recursive=False)
			except Exception, e:
				# Profile that cannot be parsed shouldn't be exported
				log.error(e)
				return False
			return True
		
		def export_menu(tar, filename):
			try:
				menu = MenuData.from_json_data(json.loads(open(filename, "r").read()), ActionParser())
				tar.add(filename, arcname=os.path.split(filename)[-1], recursive=False)
			except Exception, e:
				# Menu that cannot be parsed shouldn't be exported
				log.error(e)
				return False
			return True
		
		
		if not export_profile(tar, giofile.get_path()):
			return False
		
		for row in package:
			enabled, tp, filename = row[0], row[5], row[3]
			if enabled:
				if tp == self.TP_PROFILE:
					if not export_profile(tar, filename):
						return False
				elif tp == self.TP_MENU:
					if not export_menu(tar, filename):
						return False
		
		# Store original profile name so import knows which profile is
		# "important" and which just tagged along as referenced by some action.
		out = tempfile.NamedTemporaryFile()
		out.write(".".join(giofile.get_basename().split(".")[0:-1]))
		out.flush()
		tar.add(out.name, arcname=Export.PN_NAME, recursive=False)
		tar.close()
		return True
