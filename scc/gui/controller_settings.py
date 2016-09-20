#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gdk, GObject, GLib, GdkPixbuf
from scc.paths import get_controller_icons_path, get_default_controller_icons_path
from scc.actions import Action
from scc.gui.userdata_manager import UserDataManager
from scc.gui.editor import Editor, ComboSetter

import re, sys, os, logging
log = logging.getLogger("GS")

class ControllerSettings(Editor, UserDataManager, ComboSetter):
	GLADE = "controller_settings.glade"
	
	def __init__(self, app, controller, profile_switcher=None):
		UserDataManager.__init__(self)
		self.app = app
		self.controller = controller
		self.profile_switcher = profile_switcher
		self.setup_widgets()
		self.load_icons()
		self._timer = None
		self.app.config.reload()
		self.load_settings()
		self._eh_ids = ()
	
	
	def load_icons(self):
		paths = [ get_default_controller_icons_path(), get_controller_icons_path() ]
		self.load_user_data(paths, "*.svg", self.on_icons_loaded)
	
	
	def on_icons_loaded(self, icons):
		lstIcons = self.builder.get_object("lstIcons")
		cbIcon = self.builder.get_object("cbIcon")
		paths = [ f.get_path() for f in icons ]
		for path in sorted(paths):
			filename = os.path.split(path)[-1]
			name = ".".join(filename.split(".")[0:-1])
			if self.controller.get_type() not in name:
				# Ignore images for other types
				continue
			try:
				pb = GdkPixbuf.Pixbuf.new_from_file(path)
			except:
				# Failed to load image
				continue
			lstIcons.append(( path, filename, name, pb ))
		
		cfg = self.app.config["controllers"][self.controller.get_id()]
		
		if "icon" in cfg:
			# Should be always
			self.set_cb(cbIcon, cfg["icon"], 1)
	
	
	def on_Dialog_destroy(self, *a):
		for x in self._eh_ids:
			self.app.dm.disconnect(x)
		self._eh_ids = ()
	
	
	def load_settings(self):
		txName = self.builder.get_object("txName")
		sclLED = self.builder.get_object("sclLED")
		cbAlignOSD = self.builder.get_object("cbAlignOSD")
		
		cfg = self.app.config["controllers"][self.controller.get_id()]
		if "name" not in cfg: cfg["name"] = self.controller.get_id()
		if "led_level" not in cfg: cfg["led_level"] = 80
		if "osd_alignment" not in cfg: cfg["osd_alignment"] = 0
		
		self._recursing = True
		txName.set_text(cfg["name"])
		sclLED.set_value(float(cfg["led_level"]))
		cbAlignOSD.set_active(cfg["osd_alignment"] != 0)
		self._recursing = False
	
	
	def save_config(self, *a):
		""" Transfers settings from UI back to config """
		if self._recursing:
			return
		# Get widgets
		txName = self.builder.get_object("txName")
		sclLED = self.builder.get_object("sclLED")
		cbIcon = self.builder.get_object("cbIcon")
		cbAlignOSD = self.builder.get_object("cbAlignOSD")
		
		# Store data
		cfg = self.app.config["controllers"][self.controller.get_id()]
		cfg["name"] = txName.get_text()
		cfg["led_level"] = sclLED.get_value()
		cfg["osd_alignment"] = 1 if cbAlignOSD.get_active() else 0
		try:
			cfg["icon"] = cbIcon.get_model().get_value(cbIcon.get_active_iter(), 1)
			if self.profile_switcher:
				self.profile_switcher.update_icon()
		except:
			# Just in case there are no icons at all
			pass
		
		# Save (almost)
		self.schedule_save_config()
	
	
	def schedule_save_config(self):
		"""
		Schedules config saving in 3s.
		Done to prevent literal madness when user moves slider.
		"""
		def cb(*a):
			self._timer = None
			self.app.save_config()
			
		if self._timer is not None:
			GLib.source_remove(self._timer)
		self._timer = GLib.timeout_add_seconds(3, cb)	
	
	
	def on_sclLED_value_changed(self, scale, *a):
		if self._recursing: return
		cfg = self.app.config["controllers"][self.controller.get_id()]
		cfg["led_level"] = scale.get_value()
		try:
			self.controller.set_led_level(scale.get_value())
		except IndexError:
			# Happens when there is no controller connected to daemon
			pass
		self.schedule_save_config()
