#!/usr/bin/env python2
"""
SC-Controller - ProfileSwitcher

Set of widgets designed to allow user to select profile, placed in one Gtk.Box:
 [ Icon | Combo box with profile selection       (ch) | (S) ]

... where (S) is Save button that can be shown on demand and (ch) is change
indicator drawn in combobox.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, Gio, GLib, GObject
from scc.gui.userdata_manager import UserDataManager
from scc.paths import get_controller_icons_path, get_default_controller_icons_path
from scc.tools import find_profile, find_controller_icon

import sys, os, random, logging
log = logging.getLogger("PS")

class ProfileSwitcher(Gtk.Box, UserDataManager):
	"""
	List of signals:
		changed (name, giofile)
			Emited when value of selection combobox is changed
		new-clicked (name)
			Emited when user selects 'new profile' option.
			'name' is of currently selected profile.
		save-clicked ()
			Emited when user clicks on save button
		unknown-profile (name)
			Emited when daemon reports unknown profile for controller.
			'name' is name of reported profile.
	"""
	
	__gsignals__ = {
			b"changed"					: (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
			b"new-clicked"					: (GObject.SIGNAL_RUN_FIRST, None, (object,)),
			b"save-clicked"					: (GObject.SIGNAL_RUN_FIRST, None, ()),
			b"unknown-profile"					: (GObject.SIGNAL_RUN_FIRST, None, (object,)),
	}
	
	SEND_TIMEOUT = 100	# How many ms should switcher wait before sending event
						# about profile being switched
	
	def __init__(self, imagepath, config):
		Gtk.Box.__init__(self, Gtk.Orientation.HORIZONTAL, 0)
		UserDataManager.__init__(self)
		self.imagepath = imagepath
		self.config = config
		self.setup_widgets()
		self._allow_new = False
		self._first_time = True
		self._current = None
		self._recursing = False
		self._timer = None	# Used to prevent sending too many request
							# when user scrolls throught combobox
		self._signal = None
		self._controller = None
	
	
	def setup_widgets(self):
		# Create
		self._icon = Gtk.Image()
		self._model = Gtk.ListStore(str, object, str)
		self._combo = Gtk.ComboBox.new_with_model(self._model)
		self._revealer = None
		self._savebutton = None
		
		# Setup
		rend1 = Gtk.CellRendererText()
		rend2 = Gtk.CellRendererText()
		self._icon.set_margin_right(10)
		self._combo.pack_start(rend1, True)
		self._combo.pack_start(rend2, False)
		self._combo.add_attribute(rend1, "text", 0)
		self._combo.add_attribute(rend2, "text", 2)
		self._combo.set_row_separator_func(
			lambda model, iter : model.get_value(iter, 1) is None and model.get_value(iter, 0) == "-" )
		self._combo.connect('changed', self.on_combo_changed)
		
		# Pack
		self.pack_start(self._icon, False, True, 0)
		self.pack_start(self._combo, True, True, 0)
	
	
	def set_profile(self, name, create=False):
		"""
		Selects specified profile in UI.
		Returns True on success or False if profile is not in combobox.
		
		If 'create' is set to True, creates new combobox item if needed.
		"""
		if name.endswith(".mod"): name = name[0:-4]
		if name.endswith(".sccprofile"): name = name[0:-11]
		if "/" in name : name = os.path.split(name)[-1]
		
		self._current = name
		active = self._combo.get_active_iter()
		giofile = None
		for row in self._model:
			if self._model.get_value(row.iter, 1) is not None:
				if name == self._model.get_value(row.iter, 0):
					giofile = self._model.get_value(row.iter, 1)
					if active == row.iter:
						# Already selected
						break
					self._combo.set_active_iter(row.iter)
					break
		if giofile is None and create:
			path = find_profile(name)
			if path:
				giofile = Gio.File.new_for_path(path)
				self._model.insert(0, (name, giofile, None))
				self._combo.set_active(0)
		
		return giofile != None
	
	
	def set_allow_new(self, allow):
		"""
		Enables or disables creating new profile from this ProfileSwitcher.
		Should be called before set_profile_list.
		"""
		self._allow_new = allow
	
	
	def set_profile_list(self, lst):
		"""
		Fills combobox with given list of available profiles.
		'lst' is expected to be iterable of GIO.File's.
		"""
		self._model.clear()
		i, current_index = 0, 0
		for f in sorted(lst, key=lambda f: f.get_basename()):
			name = f.get_basename()
			if name.endswith(".mod"):
				continue
			if name.startswith("."):
				continue
			if name.endswith(".sccprofile"):
				name = name[0:-11]
			if name == self._current:
				current_index = i
			self._model.append((name, f, None))
			i += 1
		if self._allow_new:
			self._model.append(("-", None, None))
			self._model.append((_("New profile..."), None, None))
		
		if self._combo.get_active_iter() is None:
			self._combo.set_active(current_index)
	
	
	def get_profile_list(self):
		""" Returns profiles in combobox as iterable of Gio.File's """
		return ( x[1] for x in self._model if x[1] is not None )
	
	
	def on_combo_changed(self, cb):
		if self._recursing : return
		
		def run_later():
			name = self._model.get_value(cb.get_active_iter(), 0)
			giofile = self._model.get_value(cb.get_active_iter(), 1)
			GLib.source_remove(self._timer)
			self._timer = None
			
			if giofile is None:
				# 'New profile selected'
				self._recursing = True
				if self._current is None:
					cb.set_active(0)
				else:
					self.set_profile(self._current)
				self._recursing = False
				
				name = self._model.get_value(cb.get_active_iter(), 0)
				self.emit('new-clicked', name)
			else:
				self._current = name
				self.emit('changed', name, giofile)
		
		if self._timer is not None:
			GLib.source_remove(self._timer)
		self._timer = GLib.timeout_add(ProfileSwitcher.SEND_TIMEOUT, run_later)
	
	
	def on_savebutton_clicked(self, *a):
		self.emit('save-clicked')
	
	
	def on_profile_changed(self, c, profile):
		""" Called when controller profile is changed from daemon """
		if not self.set_profile(profile, True):
			if self._first_time:
				def later():
					# Cannot be executed right away, as profile-changed is
					# emitted before DaemonManager finishes initiaalisation
					self.emit('unknown-profile', profile)
				GLib.idle_add(later)
		self._first_time = False
	
	
	def set_profile_modified(self, has_changes):
		"""
		Called to signalize if profile has changes to save in UI
		by displaying "changed" next to profile name and showing Save button.
		
		Returns giofile for currently selected profile. If profile is set as
		changed, giofile is automatically changed to 'original/filename.mod',
		so application can save changes without overwriting original wile.
		"""
		if has_changes:
			if not self._revealer:
				# Revealer has to be created
				self._revealer = Gtk.Revealer()
				self._savebutton = Gtk.Button.new_from_icon_name("gtk-save", Gtk.IconSize.SMALL_TOOLBAR)
				self._savebutton.set_margin_left(5)
				self._savebutton.connect('clicked', self.on_savebutton_clicked)
				self._revealer.set_reveal_child(False)
				self._revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
				self._revealer.add(self._savebutton)
				self.pack_start(self._revealer, False, True, 0)
				self.show_all()
			self._revealer.set_reveal_child(True)
			iter = self._combo.get_active_iter()
			self._model.set_value(iter, 2, _("(changed)"))
		else:
			if self._revealer:
				# Nothing to hide if there is no revealer
				self._revealer.set_reveal_child(False)
			for i in self._model:
				i[2] = None
	
	
	def get_file(self):
		""" Returns set profile as GIO file or None if there is no any """
		return None
	
	
	def set_controller(self, c):
		if self._signal:
			self._controller.disconnect(self._signal)
			self._signal = None
		self._controller = c
		if c:
			self._icon.set_tooltip_text(c.get_name())
			self._signal = c.connect('profile-changed', self.on_profile_changed)
		else:
			self._icon.set_tooltip_text(_("Profile"))
		self._update_controller_icon()
	
	
	def get_controller(self):
		""" Returns controller set by set_controller function """
		return self._controller
	
	
	def _update_controller_icon(self):
		if self._controller or not self._controller.get_id_is_persistent():
			self._icon.set_from_file(os.path.join(self.imagepath, "controller-icon.svg"))
		id = self._controller.get_id()
		if id in self.config['controllers'] and "icon" in self.config['controllers'][id]:
			icon = find_controller_icon(self.config['controllers'][id]['icon'])
			self._icon.set_from_file(icon)
		else:
			log.debug("There is no icon for controller %s, auto assinging one", id)
			paths = [ get_default_controller_icons_path(), get_controller_icons_path() ]
			
			def cb(icons):
				icon = None
				used_icons = { 
					self.config['controllers'][x]['icon']
					for x in self.config['controllers']
					if 'icon' in self.config['controllers'][x]
				}				
				tp = "%s-" % (self._controller.get_type(),)
				icons = sorted(( os.path.split(x.get_path())[-1] for x in icons ))
				for i in icons:
					if i not in used_icons and i.startswith(tp):
						# Unused icon found
						icon = i
						break
				else:
					# All icons are already used, assign anything
					icon = random.choice(icons)
				log.debug("Auto-assigned icon %s for controller %s", icon, id)
				if id not in self.config['controllers']:
					self.config['controllers'][id] = {}
				self.config['controllers'][id]["icon"] = icon
				self.config.save()
				GLib.idle_add(self._update_controller_icon)
			
			self.load_user_data(paths, "*.svg", cb)
