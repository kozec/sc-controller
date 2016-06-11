#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gdk, GObject, GLib
from scc.x11.autoswitcher import Condition
from scc.gui.userdata_manager import UserDataManager
from scc.gui.editor import Editor

import re, logging
log = logging.getLogger("GS")

class GlobalSettings(Editor, UserDataManager):
	GLADE = "global_settings.glade"
	
	def __init__(self, app):
		UserDataManager.__init__(self)
		self.app = app
		self.setup_widgets()
		self.load_conditions()
		self.load_profile_list()
		self._eh_ids = (
			self.app.dm.connect('reconfigured', self.on_daemon_reconfigured),
		)
	
	
	def on_daemon_reconfigured(self, *a):
		# config is reloaded in main window 'reconfigured' handler.
		# Using GLib.idle_add here ensures that main window hanlder will run
		# *before* self.load_conditions
		GLib.idle_add(self.load_conditions)
	
	
	def on_Dialog_destroy(self, *a):
		for x in self._eh_ids:
			self.app.dm.disconnect(x)
		self._eh_ids = ()
	
	def load_conditions(self):
		""" Transfers autoswitch conditions from config to UI """
		tvItems = self.builder.get_object("tvItems")
		model = tvItems.get_model()
		model.clear()
		for x in self.app.config['autoswitch']:
			o = GObject.GObject()
			o.condition = Condition.parse(x['condition'])
			model.append((o, o.condition.describe(), x['profile']))
		self.on_tvItems_cursor_changed()
	
	
	def save_config(self):
		""" Transfers conditions from UI back to config """
		tvItems = self.builder.get_object("tvItems")
		conds = []
		for row in tvItems.get_model():
			conds.append(dict(
				condition = row[0].condition.encode(),
				profile = row[2]
			))
		self.app.config['autoswitch'] = conds
		self.app.save_config()
	
	
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
			entTitle.set_text(condition.title)
			cbMatchTitle.set_active(True)
		elif condition.exact_title:
			entTitle.set_text(condition.title)
			cbExactTitle.set_active(True)
			cbMatchTitle.set_active(True)
		elif condition.regexp:
			entTitle.set_text(condition.regexp.pattern)
			cbRegExp.set_active(True)
			cbMatchTitle.set_active(True)
		if condition.wm_class:
			entClass.set_text(condition.wm_class)
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
		self.on_ConditionEditor_destroy(ce)
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
			self.on_ConditionEditor_destroy(w)
	
	
	def on_ConditionEditor_destroy(self, w, *a):
		w.hide()
		return True
	
	
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
