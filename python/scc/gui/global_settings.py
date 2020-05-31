#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GObject, GLib, GdkPixbuf
from scc.menu_data import MenuData, MenuItem, Submenu, Separator, MenuGenerator
from scc.paths import get_profiles_path, get_menus_path, get_config_path
from scc.actions import ChangeProfileAction, SensitivityModifier
from scc.actions import TurnOffAction, RestartDaemonAction
from scc.tools import find_profile, find_menu, find_binary
from scc.profile import Profile, Encoder
from scc.actions import Action, NoAction
from scc.constants import LEFT, RIGHT
from scc.paths import get_share_path
from scc.gui.osk_binding_editor import OSKBindingEditor
from scc.gui.userdata_manager import UserDataManager
from scc.gui.editor import Editor, ComboSetter
from scc.gui.parser import GuiActionParser
from scc.gui.dwsnc import IS_UNITY
# from scc.x11.autoswitcher import AutoSwitcher, Condition
# from scc.osd.menu_generators import RecentListMenuGenerator
# from scc.osd.menu_generators import WindowListMenuGenerator
# from scc.osd.keyboard import Keyboard as OSDKeyboard
# from scc.osd.osk_actions import OSKCursorAction
# import scc.osd.osk_actions

import re, sys, os, json, logging, traceback
log = logging.getLogger("GS")

class GlobalSettings(Editor, UserDataManager, ComboSetter):
	GLADE = "global_settings.glade"
	
	DEFAULT_MENU_OPTIONS = [
		# label,				order, class, icon, parameter
		# TODO: Disabled
		# ('Recent profiles',		0, RecentListMenuGenerator, None, 3),
		# ('Autoswitch Options',	1, Submenu, 'system/autoswitch', '.autoswitch.menu'),
		# ('Switch To',			1, Submenu, 'system/windowlist', '.windowlist.menu'),
		# ('Display Keyboard',	2, MenuItem, 'system/keyboard', 'keyboard()'),
		# ('Turn Controller OFF', 2, MenuItem, 'system/turn-off', 'osd(turnoff())'),
		('Kill Current Window',	1, MenuItem, 'weapons/pistol-gun',
			"dialog('Really? Non-saved progress or data will be lost', "
			"name('Back', None), "
			"name('Kill', shell('kill -9 $(xdotool getwindowfocus getwindowpid)')))"),
		('Run Program...',				1, MenuItem, 'system/cog',
			'shell("scc-osd-launcher")'),
		('Display Current Bindings...',	1, MenuItem, 'system/binding-display',
			'shell("scc-osd-show-bindings")'),
		('Games',				1, Submenu, 'system/controller', '.games.menu'),
		('Edit Bindings',		2, MenuItem, 'system/edit',
			'shell("sc-controller --osd")'),
		# order: 0 - top, 1 - after 'options', 2 bottom
	]
	
	OSD_COLORS = {
		"background", "border", "text", "menuitem_border", "menuitem_hilight",
		"menuitem_hilight_text", "menuitem_hilight_border", "menuseparator"
	}
	
	OSK_COLORS = {
		"hilight", "pressed", "button1", "button1_border", "button2",
		"button2_border", "text"
	}
	
	def __init__(self, app):
		UserDataManager.__init__(self)
		self.app = app
		self.setup_widgets()
		self._timer = None
		self._recursing = False
		self._gamepad_icons = {
			'unknown': GdkPixbuf.Pixbuf.new_from_file(os.path.join(
					self.app.imagepath, "controller-icons", "unknown.svg"))
		}
		self.app.config.reload()
		self.load_settings()
		# self.load_profile_list()
		self._recursing = False
		self._eh_ids = (
			self.app.dm.connect('reconfigured', self.on_daemon_reconfigured),
		)
	
	def _get_gamepad_icon(self, drv):
		if drv in self._gamepad_icons:
			return self._gamepad_icons[drv]
		try:
			p = GdkPixbuf.Pixbuf.new_from_file(os.path.join(
				self.app.imagepath, "controller-icons", drv + "-4.svg"))
		except:
			log.warning("Failed to load gamepad icon for driver '%s'", drv)
			p = self._gamepad_icons["unknown"]
		self._gamepad_icons[drv] = p
		return p
	
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
		self.load_autoswitch()
		self.load_osk()
		self.load_colors()
		self.load_cbMIs()
		self.load_drivers()
		self.load_controllers()
		# Load rest
		self._recursing = True
		(self.builder.get_object("cbInputTestMode")
				.set_active(bool(self.app.config['enable_sniffing'])))
		(self.builder.get_object("cbEnableSerials")
				.set_active(not bool(self.app.config['ignore_serials'])))
		# (self.builder.get_object("cbEnableRumble")
		# 		.set_active(bool(self.app.config['output']['rumble'])))
		(self.builder.get_object("cbEnableStatusIcon")
				.set_active(bool(self.app.config['gui']['enable_status_icon'])))
		(self.builder.get_object("cbMinimizeToStatusIcon")
				.set_active(not IS_UNITY and bool(self.app.config['gui']['minimize_to_status_icon'])))
		(self.builder.get_object("cbMinimizeToStatusIcon")
				.set_sensitive(not IS_UNITY and self.app.config['gui']['enable_status_icon']))
		(self.builder.get_object("cbMinimizeOnStart")
				.set_active(not IS_UNITY and bool(self.app.config['gui']['minimize_on_start'])))
		(self.builder.get_object("cbMinimizeOnStart")
				.set_sensitive(not IS_UNITY and self.app.config['gui']['enable_status_icon']))
		(self.builder.get_object("cbAutokillDaemon")
				.set_active(self.app.config['gui']['autokill_daemon']))
		(self.builder.get_object("cbNewRelease")
				.set_active(self.app.config['gui']['news']['enabled']))
		self._recursing = False
	
	def load_drivers(self):
		pass
		"""
		for key, value in self.app.config['drivers'].items():
			w = self.builder.get_object("cbEnableDriver_%s" % (key, ))
			if w:
				w.set_active(value)
		"""
	
	def _load_color(self, w, value):
		""" Common part of load_colors """
		if w:
			success, color = Gdk.Color.parse("#%s" % (value,))
			if not success:
				success, color = Gdk.Color.parse("#%s" % (value,))
			w.set_color(color)
	
	def load_colors(self):
		cbOSDStyle = self.builder.get_object("cbOSDStyle")
		cbOSDColorPreset = self.builder.get_object("cbOSDColorPreset")
		for k in self.OSD_COLORS:
			w = self.builder.get_object("cb%s" % (k,))
			self._load_color(w, self.app.config["osd_colors"][k])
		for k in self.OSK_COLORS:
			w = self.builder.get_object("cbosk_%s" % (k,))
			self._load_color(w, self.app.config["osk_colors"][k])
		theme = self.app.config.get("osd_color_theme", "None")
		self.set_cb(cbOSDColorPreset, theme)
		self.set_cb(cbOSDStyle, self.app.config.get("osd_style"))
	
	def load_autoswitch(self):
		""" Transfers autoswitch settings from config to UI """
		# TODO: This
		return
		'''
		tvItems = self.builder.get_object("tvItems")
		cbShowOSD = self.builder.get_object("cbShowOSD")
		conditions = AutoSwitcher.parse_conditions(self.app.config)
		model = tvItems.get_model()
		model.clear()
		for cond in conditions.keys():
			o = GObject.GObject()
			o.condition = cond
			o.action = conditions[cond]
			a_str = o.action.describe(Action.AC_SWITCHER)
			model.append((o, o.condition.describe(), a_str))
		self._recursing = True
		self.on_tvItems_cursor_changed()
		cbShowOSD.set_active(bool(self.app.config['autoswitch_osd']))
		self._recursing = False
		'''
	
	def load_osk(self):
		# TODO: This
		return
		'''
		cbStickAction = self.builder.get_object("cbStickAction")
		cbTriggersAction = self.builder.get_object("cbTriggersAction")
		profile = Profile(GuiActionParser())
		profile.load(find_profile(OSDKeyboard.OSK_PROF_NAME))
		self._recursing = True
		
		# Load triggers
		triggers = "%s|%s" % (
				profile.triggers[LEFT].to_string(),
				profile.triggers[RIGHT].to_string()
		)
		if not self.set_cb(cbTriggersAction, triggers, keyindex=1):
			self.add_custom(cbTriggersAction, triggers)
		
		# Load stick
		if not self.set_cb(cbStickAction, profile.stick.to_string(), keyindex=1):
			self.add_custom(cbStickAction, profile.stick.to_string())
		
		# Load sensitivity
		s = profile.pads[LEFT].compress().sensitivity
		self.builder.get_object("sclSensX").set_value(s[0])
		self.builder.get_object("sclSensY").set_value(s[1])
		
		self._recursing = False
		'''
	
	def add_custom(self, cb, key):
		for k in cb.get_model():
			if k[2]:
				k[1] = key
				self.set_cb(cb, key, keyindex=1)
				return
		cb.get_model().append(( _("(customized)"), key, True ))
		self.set_cb(cb, key, keyindex=1)
	
	def _load_osk_profile(self):
		"""
		Loads and returns on-screen keyboard profile.
		Used by methods that are changing it.
		"""
		profile = Profile(GuiActionParser())
		profile.load(find_profile(OSDKeyboard.OSK_PROF_NAME))
		return profile
	
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
		cbOSDColorPreset = self.builder.get_object("cbOSDColorPreset")
		striphex = lambda a: hex(a).strip("0x").zfill(2)
		tohex = lambda a: "".join([ striphex(int(x * 0xFF)) for x in a.to_floats() ])
		for k in self.OSD_COLORS:
			w = self.builder.get_object("cb%s" % (k,))
			if w:
				self.app.config["osd_colors"][k] = tohex(w.get_color())
		for k in self.OSK_COLORS:
			w = self.builder.get_object("cbosk_%s" % (k,))
			if w:
				self.app.config["osk_colors"][k] = tohex(w.get_color())
		self.app.config["osd_color_theme"] = "None"
		self.set_cb(cbOSDColorPreset, "None")
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
		# Store hard stuff
		tvItems = self.builder.get_object("tvItems")
		cbShowOSD = self.builder.get_object("cbShowOSD")
		cbEnableStatusIcon = self.builder.get_object("cbEnableStatusIcon")
		cbMinimizeToStatusIcon = self.builder.get_object("cbMinimizeToStatusIcon")
		conds = []
		for row in tvItems.get_model():
			conds.append({
				'condition' : row[0].condition.encode(),
				'action' : row[0].action.to_string()
			})
		# Apply status icon settings
		if self.app.config['gui']['enable_status_icon'] != cbEnableStatusIcon.get_active():
			self.app.config['gui']['enable_status_icon'] = cbEnableStatusIcon.get_active()
			cbMinimizeToStatusIcon.set_sensitive(not IS_UNITY and cbEnableStatusIcon.get_active())
			if cbEnableStatusIcon.get_active():
				self.app.setup_statusicon()
			else:
				self.app.destroy_statusicon()
		# Store rest
		self.app.config['autoswitch'] = conds
		self.app.config['autoswitch_osd'] = cbShowOSD.get_active()
		self.app.config['enable_sniffing'] = self.builder.get_object("cbInputTestMode").get_active()
		self.app.config['ignore_serials'] = not self.builder.get_object("cbEnableSerials").get_active()
		# self.app.config['output']['rumble'] = self.builder.get_object("cbEnableRumble").get_active()
		self.app.config['gui']['enable_status_icon'] = self.builder.get_object("cbEnableStatusIcon").get_active()
		self.app.config['gui']['minimize_to_status_icon'] = self.builder.get_object("cbMinimizeToStatusIcon").get_active()
		self.app.config['gui']['minimize_on_start'] = self.builder.get_object("cbMinimizeOnStart").get_active()
		self.app.config['gui']['autokill_daemon'] = self.builder.get_object("cbAutokillDaemon").get_active()
		self.app.config['gui']['news']['enabled'] = self.builder.get_object("cbNewRelease").get_active()
		
		# Save
		self.app.save_config()
	
	def on_cbShowOSD_toggled(self, cb):
		if self._recursing: return
		self.save_config()
	
	def on_btRestartEmulation_clicked(self, *a):
		rvRestartWarning = self.builder.get_object("rvRestartWarning")
		self.app.dm.stop()
		rvRestartWarning.set_reveal_child(False)
		GLib.timeout_add_seconds(1, self.app.dm.start)
	
	def on_restarting_checkbox_toggled(self, *a):
		if self._recursing: return
		self.on_random_checkbox_toggled()
		self._needs_restart()
	
	def _needs_restart(self):
		if self.app.dm.is_alive():
			rvRestartWarning = self.builder.get_object("rvRestartWarning")
			rvRestartWarning.set_reveal_child(True)
	
	DRIVER_DEPS = {
		'ds4drv' : ( "evdevdrv", "hiddrv" )
	}
	
	def on_cbEnableDriver_toggled(self, cb):
		if self._recursing: return
		drv = cb.get_name()
		self.app.config["drivers"][drv] = cb.get_active()
		if cb.get_active() and drv in self.DRIVER_DEPS:
			# Driver has dependencies, make sure at least one of them is active
			one_active = any([ self.app.config["drivers"].get(x)
									for x in self.DRIVER_DEPS[drv] ])
			if not one_active:
				# Nothing is, make everything active just to be sure
				self._recursing = True
				for x in self.DRIVER_DEPS[drv]:
					w = self.builder.get_object("cbEnableDriver_%s" % (x, ))
					if w : w.set_active(True)
					self.app.config["drivers"][x] = True
				self._recursing = False
		
		if not cb.get_active() and any([ drv in x for x in self.DRIVER_DEPS.values() ]):
			# Something depends on this driver,
			# disable anything that has no dependent drivers active
			self._recursing = True
			for x, deps in self.DRIVER_DEPS.items():
				w = self.builder.get_object("cbEnableDriver_%s" % (x, ))
				one_active = any([ self.app.config["drivers"].get(y)
										for y in self.DRIVER_DEPS[x] ])
				if not one_active and w:
					w.set_active(False)
					self.app.config["drivers"][x] = False
			self._recursing = False
		
		self.save_config()
		self._needs_restart()
	
	def on_random_checkbox_toggled(self, *a):
		if self._recursing: return
		self.save_config()
	
	def on_butEditKeyboardBindings_clicked(self, *a):
		e = OSKBindingEditor(self.app)
		e.show(self.window)
	
	def btEdit_clicked_cb(self, *a):
		""" Handler for "Edit condition" button """
		tvItems = self.builder.get_object("tvItems")
		cbProfile = self.builder.get_object("cbProfile")
		ce = self.builder.get_object("ConditionEditor")
		entTitle = self.builder.get_object("entTitle")
		entClass = self.builder.get_object("entClass")
		cbMatchTitle = self.builder.get_object("cbMatchTitle")
		cbMatchClass = self.builder.get_object("cbMatchClass")
		cbExactTitle = self.builder.get_object("cbExactTitle")
		cbRegExp = self.builder.get_object("cbRegExp")
		rbProfile = self.builder.get_object("rbProfile")
		rbTurnOff = self.builder.get_object("rbTurnOff")
		rbRestart = self.builder.get_object("rbRestart")
		# Grab data
		model, iter = tvItems.get_selection().get_selected()
		o = model.get_value(iter, 0)
		profile = model.get_value(iter, 2)
		condition = o.condition
		action = o.action
		
		# Clear editor
		for cb in (cbMatchTitle, cbMatchClass, cbExactTitle, cbRegExp):
			cb.set_active(False)
		for ent in (entClass, entTitle):
			ent.set_text("")
		# Setup action
		if isinstance(o.action, ChangeProfileAction):
			rbProfile.set_active(True)
			self.set_cb(cbProfile, o.action.profile)
		elif isinstance(o.action, TurnOffAction):
			rbTurnOff.set_active(True)
		elif isinstance(o.action, RestartDaemonAction):
			rbRestart.set_active(True)
		
		# Setup editor
		if condition.title:
			entTitle.set_text(condition.title or "")
			cbMatchTitle.set_active(True)
		elif condition.exact_title:
			entTitle.set_text(condition.exact_title or "")
			cbExactTitle.set_active(True)
			cbMatchTitle.set_active(True)
		elif condition.regexp:
			try:
				entTitle.set_text(condition.regexp.pattern)
			except:
				entTitle.set_text("")
			cbRegExp.set_active(True)
			cbMatchTitle.set_active(True)
		if condition.wm_class:
			entClass.set_text(condition.wm_class or "")
			cbMatchClass.set_active(True)
		
		# Show editor
		ce.show()
	
	def on_btSave_clicked(self, *a):
		tvItems = self.builder.get_object("tvItems")
		cbProfile = self.builder.get_object("cbProfile")
		entTitle = self.builder.get_object("entTitle")
		entClass = self.builder.get_object("entClass")
		cbMatchTitle = self.builder.get_object("cbMatchTitle")
		cbMatchClass = self.builder.get_object("cbMatchClass")
		cbExactTitle = self.builder.get_object("cbExactTitle")
		cbRegExp = self.builder.get_object("cbRegExp")
		rbProfile = self.builder.get_object("rbProfile")
		rbTurnOff = self.builder.get_object("rbTurnOff")
		rbRestart = self.builder.get_object("rbRestart")
		ce = self.builder.get_object("ConditionEditor")
		
		# Build condition
		data = {}
		if cbMatchTitle.get_active() and entTitle.get_text().decode("utf-8"):
			if cbExactTitle.get_active():
				data['exact_title'] = entTitle.get_text().decode("utf-8")
			elif cbRegExp.get_active():
				data['regexp'] = entTitle.get_text().decode("utf-8")
			else:
				data['title'] = entTitle.get_text().decode("utf-8")
		if cbMatchClass.get_active() and entClass.get_text().decode("utf-8"):
			data['wm_class'] = entClass.get_text().decode("utf-8")
		condition = Condition(**data)
		
		# Grab selected action
		model, iter = cbProfile.get_model(), cbProfile.get_active_iter()
		action = NoAction()
		if rbProfile.get_active():
			action = ChangeProfileAction(model.get_value(iter, 0))
		elif rbTurnOff.get_active():
			action = TurnOffAction()
		elif rbRestart.get_active():
			action = RestartDaemonAction()
		
		# Grab & update current row
		model, iter = tvItems.get_selection().get_selected()
		o = model.get_value(iter, 0)
		o.condition = condition
		o.action = action
		model.set_value(iter, 1, condition.describe())
		model.set_value(iter, 2, action.describe(Action.AC_SWITCHER))
		self.hide_dont_destroy(ce)
		self.save_config()
	
	def on_btAdd_clicked(self, *a):
		""" Handler for "Add Item" button """
		tvItems = self.builder.get_object("tvItems")
		model = tvItems.get_model()
		o = GObject.GObject()
		o.condition = Condition()
		o.action = NoAction()
		iter = model.append((o, o.condition.describe(), "None"))
		tvItems.get_selection().select_iter(iter)
		self.on_tvItems_cursor_changed()
		self.btEdit_clicked_cb()
	
	def on_btRemove_clicked(self, *a):
		""" Handler for "Remove Condition" button """
		tvItems = self.builder.get_object("tvItems")
		model, iter = tvItems.get_selection().get_selected()
		if iter is not None:
			model.remove(iter)
		self.save_config()
		self.on_tvItems_cursor_changed()
	
	def on_tvItems_cursor_changed(self, *a):
		"""
		Handles moving cursor in Item List.
		Basically just sets Edit Item and Remove Item buttons sensitivity.
		"""
		tvItems = self.builder.get_object("tvItems")
		btEdit = self.builder.get_object("btEdit")
		btRemove = self.builder.get_object("btRemove")
		
		model, iter = tvItems.get_selection().get_selected()
		btRemove.set_sensitive(iter is not None)
		btEdit.set_sensitive(iter is not None)
	
	def on_profiles_loaded(self, profiles):
		cb = self.builder.get_object("cbProfile")
		model = cb.get_model()
		model.clear()
		for f in profiles:
			name = f.get_basename()
			if name.endswith(".mod"):
				continue
			if name.endswith(".sccprofile"):
				name = name[0:-11]
			model.append((name, f, None))
		
		cb.set_active(0)
	
	def on_ConditionEditor_key_press_event(self, w, event):
		""" Checks if pressed key was escape and if yes, closes window """
		if event.keyval == Gdk.KEY_Escape:
			self.hide_dont_destroy(w)
	
	def on_cbExactTitle_toggled(self, tg):
		# Ensure that 'Match Title' checkbox is checked and only one of
		# 'match exact title' and 'use regexp' is checked
		if tg.get_active():
			cbMatchTitle = self.builder.get_object("cbMatchTitle")
			cbRegExp = self.builder.get_object("cbRegExp")
			cbMatchTitle.set_active(True)
			cbRegExp.set_active(False)
	
	def on_cbRegExp_toggled(self, tg):
		# Ensure that 'Match Title' checkbox is checked and only one of
		# 'match exact title' and 'use regexp' is checked
		if tg.get_active():
			cbMatchTitle = self.builder.get_object("cbMatchTitle")
			cbExactTitle = self.builder.get_object("cbExactTitle")
			cbMatchTitle.set_active(True)
			cbExactTitle.set_active(False)
	
	def on_btClearSensX_clicked(self, *a):
		self.builder.get_object("sclSensX").set_value(1.0)
	
	def on_btClearSensY_clicked(self, *a):
		self.builder.get_object("sclSensY").set_value(1.0)
	
	def on_sens_value_changed(self, *a):
		if self._recursing : return
		s = (self.builder.get_object("sclSensX").get_value(),
			self.builder.get_object("sclSensY").get_value())
		
		profile = self._load_osk_profile()
		if s == (1.0, 1.0):
			profile.pads[LEFT]  = OSKCursorAction(LEFT)
			profile.pads[RIGHT] = OSKCursorAction(RIGHT)
		else:
			profile.pads[LEFT]  = SensitivityModifier(s[0], s[1], OSKCursorAction(LEFT))
			profile.pads[RIGHT] = SensitivityModifier(s[0], s[1], OSKCursorAction(RIGHT))
		self._save_osk_profile(profile)
	
	def on_entTitle_changed(self, ent):
		cbRegExp = self.builder.get_object("cbRegExp")
		btSave = self.builder.get_object("btSave")
		cbMatchTitle = self.builder.get_object("cbMatchTitle")
		# Ensure that 'Match Title' checkbox is checked if its entry gets text
		if ent.get_text().decode("utf-8"):
			cbMatchTitle.set_active(True)
		if cbRegExp.get_active():
			# If regexp combobox is active, try to compile expression typed
			# in field and don't allow user to save unless expression is valid
			try:
				re.compile(ent.get_text().decode("utf-8"))
			except Exception, e:
				log.error(e)
				btSave.set_sensitive(False)
				return
		btSave.set_sensitive(True)
	
	def on_cbOSDColorPreset_changed(self, cb):
		theme = cb.get_model().get_value(cb.get_active_iter(), 0)
		if theme in (None, "None"): return
		filename = os.path.join(get_share_path(), "osd_styles", theme)
		data = json.loads(file(filename, "r").read())
		
		# Transfer values from json to config
		for grp in ("osd_colors", "osk_colors"):
			if grp in data:
				for subkey in self.OSD_COLORS:
					if subkey in data[grp]:
						self.app.config["osd_colors"][subkey] = data[grp][subkey]
				for subkey in self.OSK_COLORS:
					if subkey in data[grp]:
						self.app.config["osk_colors"][subkey] = data[grp][subkey]
		
		# Save
		self.app.config["osd_color_theme"] = theme
		self.app.save_config()
	
	def on_cbOSDStyle_changed(self, cb):
		color_keys = self.OSK_COLORS.union(self.OSD_COLORS)
		osd_style = cb.get_model().get_value(cb.get_active_iter(), 0)
		css_file = os.path.join(get_share_path(), "osd_styles", osd_style)
		first_line = file(css_file, "r").read().split("\n")[0]
		used_colors = None				# None means "all"
		if "Used colors:" in first_line:
			used_colors = set(first_line.split(":", 1)[1].strip(" */").split(" "))
			if "all" in used_colors:
				used_colors = None		# None means "all"
		
		for key in color_keys:
			cb = self.builder.get_object("cb%s" % (key, ))
			lbl = self.builder.get_object("lbl%s" % (key, ))
			if cb:  cb.set_sensitive ((used_colors is None) or (key in used_colors))
			if lbl: lbl.set_sensitive((used_colors is None) or (key in used_colors))
		self.app.config["osd_style"] = osd_style
		self.app.save_config()
	
	@staticmethod
	def _make_mi_instance(index):
		""" Helper method used by on_cbMI_toggled and load_cbMIs """
		# label,				class, icon, *init_parameters
		label, order, cls, icon, parameter = GlobalSettings.DEFAULT_MENU_OPTIONS[index]
		if cls == MenuItem:
			instance = MenuItem("item_i%s" % (index,), label, parameter, icon=icon)
		elif cls == Submenu:
			instance = Submenu(parameter, label, icon=icon)
		else:
			instance = cls(parameter)
			instance.icon = icon
			instance.label = label
		return instance
	
	def on_cbMI_toggled(self, widget):
		"""
		Called when one of 'Default Menu Items' checkboxes is toggled.
		This actually does kind of magic:
		- 1st, default menu file is loaded
		- 2nd, based on widget name, option from DEFAULT_MENU_OPTIONS is
		  selected
		- 3rd, if this option is not present in loaded menu and checkbox is
		  toggled on, option is added
		- (same for option that is present while checkbox was toggled off)
		- 4rd, default menu is saved
		"""
		if self._recursing: return
		try:
			data = MenuData.from_fileobj(
				open(find_menu("Default.menu"), "r"),
				GuiActionParser())
			index = int(widget.get_name().split("_")[-1])
			instance = GlobalSettings._make_mi_instance(index)
		except Exception, e:
			log.error(traceback.format_exc())
			self._recursing = True
			widget.set_active(not widget.get_active())
			self._recursing = False
			return
		
		present = instance.describe().strip(" >") in [ x.describe().strip(" >") for x in data ]
		if bool(present) == bool(widget.get_active()):
			# User requested to add menu item that's already there
			# (or remove one that's not there)
			return
		
		items = [ x for x in data ]
		if widget.get_active():
			# Add item to menu
			order = GlobalSettings.DEFAULT_MENU_OPTIONS[index][1]
			pos = 0
			if order == 1:
				# After last separator
				separators = [ x for x in items[1:] if isinstance(x, Separator) ]
				if len(separators) > 0:
					pos = items.index(separators[-1]) + 1
			elif order == 2:
				# At very end
				pos = len(items)
			if isinstance(instance, MenuGenerator):
				items.insert(pos, Separator(instance.label))
				pos += 1
			items.insert(pos, instance)
		else:
			if isinstance(instance, MenuGenerator):
				items = [ x for x in items
					if not (isinstance(x, Separator)
					and x.label == instance.label) ]
			items = [ x for x in items
				if instance.describe().strip(" >") != x.describe().strip(" >") ]
		
		path = os.path.join(get_menus_path(), "Default.menu")
		data = MenuData(*items)
		jstr = Encoder(sort_keys=True, indent=4).encode(data)
		open(path, "w").write(jstr)
		log.debug("Wrote menu file %s", path)
	
	def load_cbMIs(self):
		"""
		See above. This method just parses Default menu and checks
		boxes for present menu items.
		"""
		try:
			data = MenuData.from_fileobj(open(find_menu("Default.menu"), "r"))
		except Exception, e:
			# Shouldn't really happen
			log.error(traceback.format_exc())
			return
		self._recursing = True
		
		for index in xrange(0, len(GlobalSettings.DEFAULT_MENU_OPTIONS)):
			id = "cbMI_%s" % (index,)
			instance = GlobalSettings._make_mi_instance(index)
			present = ( instance.describe().strip(" >")
				in [ x.describe().strip(" >") for x in data ] )
			self.builder.get_object(id).set_active(present)
		
		# cbMI_5, 'Kill Current Window' is special case here. This checkbox
		# should be available only if xdotool utility is installed.
		cbMI_5 = self.builder.get_object("cbMI_5")
		if find_binary("xdotool") == "xdotool":
			# Not found
			cbMI_5.set_sensitive(False)
			cbMI_5.set_tooltip_text(_("Please, install xdotool package to use this feature"))
		else:
			cbMI_5.set_sensitive(True)
			cbMI_5.set_tooltip_text("")
	
	def on_btAddController_clicked(self, *a):
		from scc.gui.creg.dialog import ControllerRegistration
		cr = ControllerRegistration(self.app)
		cr.window.connect("destroy", self.load_controllers)
		cr.show(self.window)
	
	def on_btRemoveController_clicked(self, *a):
		tvControllers = self.builder.get_object("tvControllers")
		d = Gtk.MessageDialog(parent=self.window,
			flags = Gtk.DialogFlags.MODAL,
			type = Gtk.MessageType.WARNING,
			buttons = Gtk.ButtonsType.YES_NO,
			message_format = _("Unregister controller?"),
		)
		d.format_secondary_text(_("You'll lose all settings for it"))
		if d.run() == -8:
			# Yes
			model, iter = tvControllers.get_selection().get_selected()
			path = model[iter][0]
			try:
				os.unlink(path)
			except Exception, e:
				log.exception(e)
			self._needs_restart()
			self.load_controllers()
		d.destroy()
	
	def load_controllers(self, *a):
		lstControllers = self.builder.get_object("lstControllers")
		lstControllers.clear()
		for cid in self.app.config.get_controllers():
			if "-" in cid:
				drv, name = cid.split("-", 1)
				lstControllers.append((cid, name, self._get_gamepad_icon(drv)))

