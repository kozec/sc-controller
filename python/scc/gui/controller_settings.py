#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import GLib, GdkPixbuf
from scc.paths import get_controller_icons_path, get_default_controller_icons_path
from scc.gui.userdata_manager import UserDataManager
from scc.gui.editor import Editor, ComboSetter

import os, logging
log = logging.getLogger("GS")

class ControllerSettings(Editor, UserDataManager, ComboSetter):
	GLADE = "controller_settings.glade"
	
	def __init__(self, app, controller, profile_switcher=None):
		UserDataManager.__init__(self)
		self.app = app
		self.controller = controller
		self.profile_switcher = profile_switcher
		self.setup_widgets()
		self._config = controller.get_config()
		self._timer = None
		self.load_icons()
		self.load_settings()
		self._eh_ids = ()
	
	
	def load_icons(self):
		paths = [ get_default_controller_icons_path(), get_controller_icons_path() ]
		self.load_user_data(paths, "*.svg", None, self.on_icons_loaded)
	
	
	def on_icons_loaded(self, icons):
		lstIcons = self.builder.get_object("lstIcons")
		cbIcon = self.builder.get_object("cbIcon")
		paths = [ f.get_path() for f in icons ]
		tp = "%s-" % (self.controller.get_type(),)
		if tp in ("evdev-", "dinput-"):
			# Special cases so I don't have to impose symlinks on Windows
			tp = "generic-"
		for path in sorted(paths):
			filename = os.path.split(path)[-1]
			name = ".".join(filename.split(".")[0:-1])
			if not name.startswith(tp):
				# Ignore images for other types
				continue
			try:
				pb = GdkPixbuf.Pixbuf.new_from_file(path)
			except:
				# Failed to load image
				continue
			lstIcons.append(( path, filename, name, pb ))
		
		if "icon" in self._config["gui"]:
			# Should be always
			self.set_cb(cbIcon, self._config["gui"]["icon"], 1)
	
	
	def on_Dialog_destroy(self, *a):
		for x in self._eh_ids:
			self.app.dm.disconnect(x)
		self._eh_ids = ()
	
	
	def on_btClearControlWith_clicked(self, *a):
		self.builder.get_object("cbControlWith").set_active(0)
	
	
	def on_btClearConfirmWith_clicked(self, *a):
		self.builder.get_object("cbConfirmWith").set_active(0)
	
	
	def on_btClearCancelWith_clicked(self, *a):
		self.builder.get_object("cbCancelWith").set_active(1)
	
	
	def on_exTouchpadRotation_activate(self, ex, *a):
		rvTouchpadRotation = self.builder.get_object("rvTouchpadRotation")
		rvTouchpadRotation.set_reveal_child(not ex.get_expanded())
	
	
	def on_exMenuButtons_activate(self, ex, *a):
		rvMenuButtons = self.builder.get_object("rvMenuButtons")
		rvMenuButtons.set_reveal_child(not ex.get_expanded())
	
	
	def on_btClearLeftRotation_clicked(self, *a):
		sclLeftRotation = self.builder.get_object("sclLeftRotation")
		sclLeftRotation.set_value(20)
	
	
	def on_btClearRightRotation_clicked(self, *a):
		sclRightRotation = self.builder.get_object("sclRightRotation")
		sclRightRotation.set_value(-20)
	
	
	def on_rotation_value_changed(self, *a):
		if self._recursing: return
		self.save_config()
	
	
	def load_settings(self):
		txName = self.builder.get_object("txName")
		sclLED = self.builder.get_object("sclLED")
		cbAlignOSD = self.builder.get_object("cbAlignOSD")
		sclIdleTimeout = self.builder.get_object("sclIdleTimeout")
		sclLeftRotation = self.builder.get_object("sclLeftRotation")
		sclRightRotation = self.builder.get_object("sclRightRotation")
		cbControlWith = self.builder.get_object("cbControlWith")
		cbConfirmWith = self.builder.get_object("cbConfirmWith")
		cbCancelWith = self.builder.get_object("cbCancelWith")
		
		cfg = self._config
		self._recursing = True
		txName.set_text(cfg["gui"]["name"] or "")
		sclLED.set_value(float(cfg["led_level"]))
		sclIdleTimeout.set_value(float(cfg["idle_timeout"]))
		sclLeftRotation.set_value(float(cfg["input_rotation/left"]))
		sclRightRotation.set_value(float(cfg["input_rotation/right"]))
		cbAlignOSD.set_active(cfg["osd_alignment"] != 0)
		self.set_cb(cbControlWith, cfg["menu_control"], keyindex=1)
		self.set_cb(cbConfirmWith, cfg["menu_confirm"], keyindex=1)
		self.set_cb(cbCancelWith, cfg["menu_cancel"], keyindex=1)
		cbConfirmWith.set_row_separator_func( lambda model, iter : model.get_value(iter, 0) == "-" )
		cbCancelWith.set_row_separator_func( lambda model, iter : model.get_value(iter, 0)  == "-" )
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
		sclIdleTimeout = self.builder.get_object("sclIdleTimeout")
		sclLeftRotation = self.builder.get_object("sclLeftRotation")
		sclRightRotation = self.builder.get_object("sclRightRotation")
		cbControlWith = self.builder.get_object("cbControlWith")
		cbConfirmWith = self.builder.get_object("cbConfirmWith")
		cbCancelWith = self.builder.get_object("cbCancelWith")
		
		# Store data
		cfg = self._config
		cfg["gui"]["name"] = txName.get_text().decode("utf-8")
		cfg["led_level"] = sclLED.get_value()
		cfg["osd_alignment"] = 1 if cbAlignOSD.get_active() else 0
		cfg["idle_timeout"] = sclIdleTimeout.get_value()
		cfg["input_rotation/left"] = sclLeftRotation.get_value()
		cfg["input_rotation/right"] = sclRightRotation.get_value()
		cfg["menu_control"] = cbControlWith.get_model().get_value(cbControlWith.get_active_iter(), 1)
		cfg["menu_confirm"] = cbConfirmWith.get_model().get_value(cbConfirmWith.get_active_iter(), 1)
		cfg["menu_cancel"] = cbCancelWith.get_model().get_value(cbCancelWith.get_active_iter(), 1)
		
		try:
			cfg["gui"]["icon"] = cbIcon.get_model().get_value(cbIcon.get_active_iter(), 1)
			if self.profile_switcher:
				self.profile_switcher.update_icon()
		except:
			# Just in case there are no icons at all
			pass
		
		# Save (almost)
		self.schedule_save_config()
	
	
	def schedule_save_config(self, *a):
		"""
		Schedules config saving in 1s.
		Done to prevent literal madness when user moves slider.
		"""
		def cb(*a):
			self._timer = None
			self._config.save()
			self.app.dm.reconfigure()
		
		if self._timer is not None:
			GLib.source_remove(self._timer)
		self._timer = GLib.timeout_add_seconds(1, cb)	
	
	
	def on_sclIdleTimeout_format_value(self, scale, value):
		if value <= 180:	# 2 minutes
			return _("%s seconds") % int(value)
		if value % 60 == 0:
			return _("%s minutes") % int(value / 60)
		return _("%sm %ss") % (int(value / 60), int(value % 60))
	
	
	def on_sclLED_value_changed(self, scale, *a):
		if self._recursing: return
		cfg = self._config
		cfg["led_level"] = scale.get_value()
		try:
			self.controller.set_led_level(scale.get_value())
		except IndexError:
			# Happens when there is no controller connected to daemon
			pass
		self.schedule_save_config()
	
	
	def on_sclIdleTimeout_value_changed(self, scale, *a):
		if self._recursing: return
		cfg = self._config
		cfg["idle_timeout"] = scale.get_value()
		self.schedule_save_config()

