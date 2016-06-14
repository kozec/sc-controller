#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gdk, GObject, GLib
from scc.modifiers import SensitivityModifier
from scc.paths import get_profiles_path
from scc.constants import LEFT, RIGHT
from scc.tools import find_profile
from scc.actions import ACTIONS
from scc.profile import Profile
from scc.gui.osk_binding_editor import OSKBindingEditor
from scc.gui.userdata_manager import UserDataManager
from scc.gui.parser import GuiActionParser
from scc.gui.editor import Editor
from scc.gui import ComboSetter
from scc.x11.autoswitcher import Condition
from scc.osd.keyboard import Keyboard as OSDKeyboard
from scc.osd.osk_actions import OSK, OSKCursorAction

import re, os, logging
log = logging.getLogger("GS")

class GlobalSettings(Editor, UserDataManager, ComboSetter):
	GLADE = "global_settings.glade"
	
	def __init__(self, app):
		UserDataManager.__init__(self)
		self.app = app
		self.setup_widgets()
		self._recursing = False
		self.app.config.reload()
		ACTIONS['OSK'] = OSK
		self.load_settings()
		self.load_profile_list()
		self.osk_binding_editor = None
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
		del ACTIONS['OSK']
	
	
	def load_settings(self):
		self.load_autoswitch()
		self.load_osk()
	
	
	def load_autoswitch(self):
		""" Transfers autoswitch settings from config to UI """
		tvItems = self.builder.get_object("tvItems")
		cbShowOSD = self.builder.get_object("cbShowOSD")
		model = tvItems.get_model()
		model.clear()
		for x in self.app.config['autoswitch']:
			o = GObject.GObject()
			o.condition = Condition.parse(x['condition'])
			model.append((o, o.condition.describe(), x['profile']))
		self._recursing = True
		self.on_tvItems_cursor_changed()
		cbShowOSD.set_active(bool(self.app.config['autoswitch_osd']))
		self._recursing = False
	
	
	def load_osk(self):
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
		s = profile.pads[LEFT].compress().speed
		self.builder.get_object("sclSensX").set_value(s[0])
		self.builder.get_object("sclSensY").set_value(s[1])
		
		self._recursing = False
	
	
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
	
	
	def save_config(self):
		""" Transfers settings from UI back to config """
		tvItems = self.builder.get_object("tvItems")
		cbShowOSD = self.builder.get_object("cbShowOSD")
		conds = []
		for row in tvItems.get_model():
			conds.append(dict(
				condition = row[0].condition.encode(),
				profile = row[2]
			))
		self.app.config['autoswitch'] = conds
		self.app.config['autoswitch_osd'] = cbShowOSD.get_active()
		self.app.save_config()
	
	
	def on_cbShowOSD_toggled(self, cb):
		if self._recursing: return
		self.save_config()
	
	
	def on_butEditKeyboardBindings_clicked(self, *a):
		if not self.osk_binding_editor:
			self.osk_binding_editor = OSKBindingEditor(self.app)
		self.osk_binding_editor.show(self.window)
	
	
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
		# Grab data
		model, iter = tvItems.get_selection().get_selected()
		o = model.get_value(iter, 0)
		profile = model.get_value(iter, 2)
		condition = o.condition
		
		# Clear editor
		self.set_cb(cbProfile, profile)
		for cb in (cbMatchTitle, cbMatchClass, cbExactTitle, cbRegExp):
			cb.set_active(False)
		for ent in (entClass, entTitle):
			ent.set_text("")
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
		ce = self.builder.get_object("ConditionEditor")
		
		# Build condition
		data = {}
		if cbMatchTitle.get_active() and entTitle.get_text():
			if cbExactTitle.get_active():
				data['exact_title'] = entTitle.get_text()
			elif cbRegExp.get_active():
				data['regexp'] = entTitle.get_text()
			else:
				data['title'] = entTitle.get_text()
		if cbMatchClass.get_active() and entClass.get_text():
			data['wm_class'] = entClass.get_text()
		condition = Condition(**data)
		
		# Grab selected profile
		model, iter = cbProfile.get_model(), cbProfile.get_active_iter()
		profile = model.get_value(iter, 0)
		
		# Grab & update current row
		model, iter = tvItems.get_selection().get_selected()
		o = model.get_value(iter, 0)
		o.condition = condition
		model.set_value(iter, 1, condition.describe())
		model.set_value(iter, 2, profile)
		self.hide_dont_destroy(ce)
		self.save_config()
	
	
	def on_btAdd_clicked(self, *a):
		""" Handler for "Add Item" button """
		tvItems = self.builder.get_object("tvItems")
		model = tvItems.get_model()
		o = GObject.GObject()
		o.condition = Condition()
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
		if ent.get_text():
			cbMatchTitle.set_active(True)
		if cbRegExp.get_active():
			# If regexp combobox is active, try to compile expression typed
			# in field and don't allow user to save unless expression is valid
			try:
				re.compile(ent.get_text())
			except Exception, e:
				log.error(e)
				btSave.set_sensitive(False)
				return
		btSave.set_sensitive(True)
