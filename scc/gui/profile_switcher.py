#!/usr/bin/env python2
"""
SC-Controller - ProfileSwitcher

Set of widgets designed to allow user to select profile, placed in one Gtk.Box:
 [ Label | Combo box with profile selection       (ch) | (S) ]

... where (S) is Save button thatn can be shown on demand and (ch) is similar
change indicator.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, Gio, GLib, GObject
from scc.tools import find_profile

import sys, os, logging
log = logging.getLogger("PS")

class ProfileSwitcher(Gtk.Box):
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
	
	def __init__(self, userdatamanager=None):
		Gtk.Box.__init__(self, Gtk.Orientation.HORIZONTAL, 0)
		self.udm = userdatamanager
		self.setup_widgets()
		self._allow_new = False
		self._first_time = True
		self._current = None
		self._recursing = False
		self._signal = None
		self._controller = None
	
	
	def setup_widgets(self):
		# Create
		self._label = Gtk.Label(_("Profile"))
		self._model = Gtk.ListStore(str, object, str)
		self._combo = Gtk.ComboBox.new_with_model(self._model)
		self._revealer = None
		self._savebutton = None
		
		# Setup
		self._label.set_size_request(100, -1)
		self._label.set_xalign(0)
		self._label.set_margin_right(10)
		rend1 = Gtk.CellRendererText()
		rend2 = Gtk.CellRendererText()
		self._combo.pack_start(rend1, True)
		self._combo.pack_start(rend2, False)
		self._combo.add_attribute(rend1, "text", 0)
		self._combo.add_attribute(rend2, "text", 2)
		self._combo.set_row_separator_func(
			lambda model, iter : model.get_value(iter, 1) is None and model.get_value(iter, 0) == "-" )
		self._combo.connect('changed', self.on_combo_changed)
		
		# Pack
		self.pack_start(self._label, False, True, 0)
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
		'lst' is expected to be iterable of GIO.File's or another
		ProfileSwitcher to copy data from.
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
	
	
	def on_combo_changed(self, cb):
		if self._recursing : return
		name = self._model.get_value(cb.get_active_iter(), 0)
		giofile = self._model.get_value(cb.get_active_iter(), 1)
		
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
			self._label.set_text(c.get_name())
			self._signal = c.connect('profile-changed', self.on_profile_changed)
		else:
			self._label.set_text(_("Profile"))
	
	
	def get_controller(self):
		""" Returns controller set by set_controller function """
		return self._controller
