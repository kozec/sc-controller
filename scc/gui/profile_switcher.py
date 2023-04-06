#!/usr/bin/env python3
"""
SC-Controller - ProfileSwitcher

Set of widgets designed to allow user to select profile, placed in one Gtk.Box:
 [ Icon | Combo box with profile selection       (ch) | (S) ]

... where (S) is Save button that can be shown on demand and (ch) is change
indicator drawn in combobox.
"""

from scc.tools import _

from gi.repository import Gtk, Gio, GLib, GObject
from scc.gui.userdata_manager import UserDataManager
from scc.paths import get_controller_icons_path, get_default_controller_icons_path
from scc.tools import find_profile, find_controller_icon

import os, random, logging
log = logging.getLogger("PS")

class ProfileSwitcher(Gtk.EventBox, UserDataManager):
	"""
	List of signals:
		changed (name, giofile)
			Emited when value of selection combobox is changed
		new-clicked (name)
			Emited when user selects 'new profile' option.
			'name' is of currently selected profile.
		right-clicked ()
			Emited whenm user right-clicks anything
		save-clicked ()
			Emited when user clicks on save button
		switch-to-clicked ()
			Emited when user clicks on "switch to this controller" button
		unknown-profile (name)
			Emited when daemon reports unknown profile for controller.
			'name' is name of reported profile.
	"""
	
	__gsignals__ = {
			b"changed"				: (GObject.SignalFlags.RUN_FIRST, None, (object, object)),
			b"new-clicked"			: (GObject.SignalFlags.RUN_FIRST, None, (object,)),
			b"right-clicked"		: (GObject.SignalFlags.RUN_FIRST, None, ()),
			b"save-clicked"			: (GObject.SignalFlags.RUN_FIRST, None, ()),
			b"switch-to-clicked"	: (GObject.SignalFlags.RUN_FIRST, None, ()),
			b"unknown-profile"		: (GObject.SignalFlags.RUN_FIRST, None, (object,)),
	}
	
	SEND_TIMEOUT = 100	# How many ms should switcher wait before sending event
						# about profile being switched
	
	def __init__(self, imagepath, config):
		Gtk.EventBox.__init__(self)
		UserDataManager.__init__(self)
		self.imagepath = imagepath
		self.config = config
		self._allow_new = False
		self._first_time = True
		self._current = None
		self._recursing = False
		self._timer = None	# Used to prevent sending too many request
							# when user scrolls throught combobox
		self._signal = None
		self._controller = None
		self.setup_widgets()
	
	
	def setup_widgets(self):
		# Create
		self._icon = Gtk.Image()
		self._model = Gtk.ListStore(str, object, str)
		self._combo = Gtk.ComboBox.new_with_model(self._model)
		self._box = Gtk.Box(Gtk.Orientation.HORIZONTAL, 0)
		self._savebutton = None
		self._switch_to_button = None
		
		# Setup
		rend1 = Gtk.CellRendererText()
		rend2 = Gtk.CellRendererText()
		self._box.set_spacing(12)
		self._combo.pack_start(rend1, True)
		self._combo.pack_start(rend2, False)
		self._combo.add_attribute(rend1, "text", 0)
		self._combo.add_attribute(rend2, "text", 2)
		self._combo.set_row_separator_func(
			lambda model, iter : model.get_value(iter, 1) is None and model.get_value(iter, 0) == "-" )
		self.update_icon()
		
		# Signals
		self._combo.connect('changed', self.on_combo_changed)
		self.connect("button_press_event", self.on_button_press)
		
		# Pack
		self._box.pack_start(self._icon, False, True, 0)
		self._box.pack_start(self._combo, True, True, 0)
		self.add(self._box)
	
	
	def set_profile(self, name, create=False):
		"""
		Selects specified profile in UI.
		Returns True on success or False if profile is not in combobox.
		
		If 'create' is set to True, creates new combobox item if needed.
		"""
		if name is None:
			return
		
		
		if name.endswith(".mod"): name = name[0:-4]
		if name.endswith(".sccprofile"): name = name[0:-11]
		if "/" in name : name = os.path.split(name)[-1]
		self._current = name
		if type(name) == str:
			# GTK can't handle this
			name = name.encode("utf-8")
		
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
	
	
	def set_allow_switch(self, allow):
		"""
		Enables or disables profile switching for this ProfileSwitcher.
		When disabled, only save button is be usable.
		"""
		self._combo.set_sensitive(allow)
	
	
	def set_profile_list(self, lst):
		"""
		Fills combobox with given list of available profiles.
		'lst' is expected to be iterable of GIO.File's.
		"""
		self._model.clear()
		i, current_index = 0, 0
		for f in sorted(lst, key=lambda f: f.get_basename()):
			name = f.get_basename().decode("utf-8")
			if type(name) is str:
				name = name.decode("utf-8")
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
	
	
	def get_profile_name(self):
		""" Returns name of currently selected profile """
		return self._model.get_value(self._combo.get_active_iter(), 0)
	
	
	def refresh_profile_path(self, name):
		"""
		Called from main window after profile file is deleted.
		May either change path to profile in default_profiles directory,
		or remove entry entirely.
		"""
		prev = None
		new_path = find_profile(name)
		# Find row with named profile
		for row in self._model:
			if row[0] == name:
				active = self._combo.get_active_iter()
				if new_path is None:
					# Profile was completly removed
					if self._model.get_value(active, 0) == name:
						# If removed profile happends to be active one (what's
						# almost always), switch to previous profile in list
						self._model.remove(row.iter)
						if prev is None:
							# ... unless removed profile was 1st in list. Switch
							# to next in that case
							self._combo.set_active_iter(self._model[0].iter)
						else:
							self._combo.set_active_iter(prev.iter)
					else:
						self._model.remove(row.iter)
				else:
					giofile = Gio.File.new_for_path(new_path)
					self._model.set_value(row.iter, 1, giofile)
					if self._model.get_value(active, 0) == name:
						# Active profile was changed
						self.emit('changed', name, giofile)
				return
			prev = row
	
	
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
				
				self.emit('new-clicked', self.get_profile_name())
			else:
				self._current = name
				self.emit('changed', name, giofile)
		
		if self._timer is not None:
			GLib.source_remove(self._timer)
		self._timer = GLib.timeout_add(ProfileSwitcher.SEND_TIMEOUT, run_later)
	
	
	def on_button_press(self, trash, event):
		if event.button == 3:
			self.emit('right-clicked')	
	
	
	def on_savebutton_clicked(self, *a):
		self.emit('save-clicked')
	
	
	def on_switch_to_clicked(self, *a):
		self.emit('switch-to-clicked')
	
	
	def on_daemon_dead(self, *a):
		""" Called from App when connection to daemon is lost """
		self._first_time = True
	
	
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
	
	
	def set_profile_modified(self, has_changes, is_template=False):
		"""
		Called to signalize that profile has changes to save in UI
		by displaying "changed" next to profile name and showing Save button.
		
		Returns giofile for currently selected profile. If profile is set as
		changed, giofile is automatically changed to 'original/filename.mod',
		so application can save changes without overwriting original wile.
		"""
		if has_changes:
			if not self._savebutton:
				# Save button has to be created
				self._savebutton = ButtonInRevealer(
					"gtk-save", _("Save changes"),
					self.on_savebutton_clicked)
				self._box.pack_start(self._savebutton, False, True, 0)
				self.show_all()
			self._savebutton.set_reveal_child(True)
			iter = self._combo.get_active_iter()
			if is_template:
				self._model.set_value(iter, 2, _("(changed template)"))
			else:
				self._model.set_value(iter, 2, _("(changed)"))
		else:
			if self._savebutton:
				# Nothing to hide if there is no revealer
				self._savebutton.set_reveal_child(False)
			for i in self._model:
				i[2] = None
			if is_template:
				iter = self._combo.get_active_iter()
				self._model.set_value(iter, 2, _("(template)"))
	
	
	def set_switch_to_enabled(self, enabled):
		"""
		Shows or hides 'switch-to' button
		"""
		if enabled:
			if not self._switch_to_button:
				# Save button has to be created
				self._switch_to_button = ButtonInRevealer(
					"gtk-edit", _("Edit mappings of this controller"),
					self.on_switch_to_clicked)
				self._box.pack_start(self._switch_to_button, False, True, 0)
				self.show_all()
			self._switch_to_button.set_reveal_child(True)
		else:
			if self._switch_to_button:
				# Nothing to hide if there is no revealer
				self._switch_to_button.set_reveal_child(False)
	
	
	def get_file(self):
		""" Returns set profile as GIO file or None if there is no any """
		return None
	
	
	def set_controller(self, c):
		if self._signal:
			self._controller.disconnect(self._signal)
			self._signal = None
		self._controller = c
		if c:
			name = self.config.get_controller_config(c.get_id())["name"]
			self._icon.set_tooltip_text(name)
			self._signal = c.connect('profile-changed', self.on_profile_changed)
		else:
			self._icon.set_tooltip_text(_("Profile"))
		self.update_icon()
	
	
	def get_controller(self):
		""" Returns controller set by set_controller function """
		return self._controller
	
	
	def update_icon(self):
		""" Changes displayed icon to whatever is currently set in config """
		# Called internally and from ControllerSettings
		if not self._controller:
			self._icon.set_from_file(os.path.join(self.imagepath, "controller-icon.svg"))
			return
		
		id = self._controller.get_id()
		cfg = self.config.get_controller_config(id)
		if cfg["icon"]:
			icon = find_controller_icon(cfg["icon"])
			self._icon.set_from_file(icon)
		else:
			log.debug("There is no icon for controller %s, auto assinging one", id)
			paths = [ get_default_controller_icons_path(), get_controller_icons_path() ]
			
			def cb(icons):
				if id != self._controller.get_id():
					# Controller was changed before callback was called
					return
				icon = None
				used_icons = { 
					self.config['controllers'][x]['icon']
					for x in self.config['controllers']
					if 'icon' in self.config['controllers'][x]
				}
				tp = "%s-" % (self._controller.get_type(),)
				icons = sorted(( os.path.split(x.get_path())[-1] for x in icons ))
				log.debug("Searching for icon type: %s", tp.strip("-"))
				for i in icons:
					if i not in used_icons and i.startswith(tp):
						# Unused icon found
						icon = i
						break
				else:
					# All icons are already used, assign anything
					icon = random.choice(icons)
				log.debug("Auto-assigned icon %s for controller %s", icon, id)
				cfg = self.config.get_controller_config(id)
				cfg["icon"] = icon
				self.config.save()
				GLib.idle_add(self.update_icon)
			
			self.load_user_data(paths, "*.svg", None, cb)


class ButtonInRevealer(Gtk.Revealer):
	
	def __init__(self, button_name, tooltip, callback):
		Gtk.Revealer.__init__(self)
		self.button = Gtk.Button.new_from_icon_name(button_name, Gtk.IconSize.SMALL_TOOLBAR)
		self.button.connect('clicked', callback)
		self.button.set_tooltip_text(tooltip)
		self.set_reveal_child(False)
		self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
		self.add(self.button)
