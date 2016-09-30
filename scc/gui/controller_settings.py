#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gdk, GObject, GLib
from scc.actions import Action
from scc.gui.userdata_manager import UserDataManager
from scc.gui.editor import Editor, ComboSetter

import re, sys, os, logging
log = logging.getLogger("GS")

class ControllerSettings(Editor, UserDataManager, ComboSetter):
	GLADE = "controller_settings.glade"
	
	def __init__(self, app, controller):
		UserDataManager.__init__(self)
		self.app = app
		self.controller = controller
		self.setup_widgets()
		self._recursing = False
		self._timer = None
		self.app.config.reload()
		self.load_settings()
		self._recursing = False
		self._eh_ids = (
			self.app.dm.connect('reconfigured', self.on_daemon_reconfigured),
		)
	
	
	def on_daemon_reconfigured(self, *a):
		# config is reloaded in main window 'reconfigured' handler.
		# Using GLib.idle_add here ensures that main window hanlder will run
		# *before* self.load_conditions
		GLib.idle_add(self.load_settings)
	
	
	def on_Dialog_destroy(self, *a):
		for x in self._eh_ids:
			self.app.dm.disconnect(x)
		self._eh_ids = ()
	
	
	def load_settings(self):
		pass
		
	
	
	def _save_osk_profile(self, profile):
		"""
		Saves on-screen keyboard profile and calls daemon.reconfigure()
		Used by methods that are changing it.
		"""
		profile.save(os.path.join(get_profiles_path(),
				OSDKeyboard.OSK_PROF_NAME + ".sccprofile"))
		self.app.dm.reconfigure()
	
	
	def on_cbStickAction_changed(self, cb):
		if self._recursing: return
		key = cb.get_model().get_value(cb.get_active_iter(), 1)
		profile = self._load_osk_profile()
		profile.stick = GuiActionParser().restart(key).parse()
		self._save_osk_profile(profile)
	
	
	def on_cbTriggersAction_changed(self, cb):
		if self._recursing: return
		key = cb.get_model().get_value(cb.get_active_iter(), 1)
		l, r = key.split("|")
		profile = self._load_osk_profile()
		profile.triggers[LEFT]  = GuiActionParser().restart(l).parse()
		profile.triggers[RIGHT] = GuiActionParser().restart(r).parse()
		self._save_osk_profile(profile)
	
	
	def on_osd_color_set(self, *a):
		"""
		Called when user selects color.
		"""
		# Following lambdas converts Gdk.Color into #rrggbb notation.
		# Gdk.Color can do similar, except it uses #rrrrggggbbbb notation that
		# is not understood by Gdk css parser....
		striphex = lambda a: hex(a).strip("0x").zfill(2)
		tohex = lambda a: "".join([ striphex(int(x * 0xFF)) for x in a.to_floats() ])
		for k in self.app.config["osd_colors"]:
			w = self.builder.get_object("cb%s" % (k,))
			if w:
				self.app.config["osd_colors"][k] = tohex(w.get_color())
		for k in self.app.config["osk_colors"]:
			w = self.builder.get_object("cbosk_%s" % (k,))
			if w:
				self.app.config["osk_colors"][k] = tohex(w.get_color())
		self.app.save_config()
	
	
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
	
	
	def save_config(self):
		""" Transfers settings from UI back to config """
		# Store data
		pass
		# Save
		self.app.save_config()
	
	
	def on_sclLED_value_changed(self, scale, *a):
		if self._recursing: return
		self.app.config["led_level"] = scale.get_value()
		try:
			self.app.dm.get_controllers()[0].set_led_level(scale.get_value())
		except IndexError:
			# Happens when there is no controller connected to daemon
			pass
		self.schedule_save_config()
