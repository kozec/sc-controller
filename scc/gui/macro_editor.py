#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.controller_widget import ControllerButton
from scc.gui.action_editor import ActionEditor
from scc.gui.editor import Editor
from scc.actions import Action, ButtonAction, NoAction
from scc.macros import Macro, Repeat, SleepAction
from scc.modifiers import ModeModifier
from scc.constants import SCButtons
from scc.profile import Profile

from gi.repository import Gtk, Gdk, GLib
import os, logging
log = logging.getLogger("MacroEditor")

class MacroEditor(Editor):
	GLADE = "macro_editor.glade"
	
	def __init__(self, app, callback):
		self.app = app
		self.id = None
		self.mode = Action.AC_BUTTON
		self.ac_callback = callback
		self.setup_widgets()
		self.actions = []
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.window = self.builder.get_object("Dialog")
		self.builder.connect_signals(self)
	
	
	def update_action_field(self):
		""" Updates field on bottom """
		entAction = self.builder.get_object("entAction")
		entAction.set_text(self._make_action().to_string())
	
	
	def _make_action(self):
		""" Generates and returns Action instance """
		entName = self.builder.get_object("entName")
		cbMacroType = self.builder.get_object("cbMacroType")
		pars = [ x[0] for x in self.actions ]
		action = Macro(*pars)
		if len(pars) == 0:
			# No action is actually set
			action = NoAction()
		elif cbMacroType.get_active() == 1:
			action.repeat = True
		elif len(pars) == 1:
			# Only one action
			action = pars[0]
		if entName.get_text().strip() != "":
			action.name = entName.get_text().strip()
		return action
	
	
	def _add_action(self, action):
		""" Adds widgets for new action """
		grActions = self.builder.get_object("grActions")
		model = self.builder.get_object("lstPressClickOrHold")
		i = len(self.actions) + 1
		action.name = None
		
		# Buttons
		upb, downb, clearb = Gtk.Button(), Gtk.Button(), Gtk.Button()
		b = Gtk.Button.new_with_label(action.describe(self.mode))
		widgets = [upb, downb, clearb]
		
		# Action button
		b.set_property("hexpand", True)
		b.set_property("margin-left", 10)
		b.set_property("margin-right", 10)
		action_data = [ action, widgets ]
		
		if isinstance(action, ButtonAction):
			# Combobox
			c = Gtk.ComboBox()
			c.set_model(model)
			c.set_size_request(100, -1)
			renderer = Gtk.CellRendererText()
			c.pack_start(renderer, True)
			c.add_attribute(renderer, 'text', 1)
			c.set_active(0)
			
			widgets += [c, b]
			grActions.attach(c,			0, i, 1, 1)
			grActions.attach(b,			1, i, 1, 1)
		elif isinstance(action, SleepAction):
			# Label and scale
			l = Gtk.Label("")
			l.set_xalign(0.0)
			l.set_size_request(100, -1)
			s = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 5, 5000, 5)
			s.set_draw_value(False)
			s.connect('change_value', self.on_change_delay, action_data)
			s.set_value(action.delay * 1000)
			widgets += [l, s]
			grActions.attach(l,			0, i, 1, 1)
			grActions.attach(s,			1, i, 1, 1)
			self.on_change_delay(s, None, action.delay * 1000, action_data)
		else:
			# Placeholder
			l = Gtk.Label("")
			l.set_size_request(100, -1)
			
			widgets += [l, b]
			grActions.attach(l,			0, i, 1, 1)
			grActions.attach(b,			1, i, 1, 1)
		
		b.connect('clicked',		self.on_actionb_clicked, action_data)
		upb.connect('clicked',		self.on_moveb_clicked, -1, action_data)
		downb.connect('clicked',	self.on_moveb_clicked, 1, action_data)
		clearb.connect('clicked',	self.on_clearb_clicked, action_data)
		
		# Move Up button
		upb.set_image(Gtk.Image.new_from_stock("gtk-go-up", Gtk.IconSize.SMALL_TOOLBAR))
		upb.set_relief(Gtk.ReliefStyle.NONE)
		
		# Move Down button
		downb.set_image(Gtk.Image.new_from_stock("gtk-go-down", Gtk.IconSize.SMALL_TOOLBAR))
		downb.set_relief(Gtk.ReliefStyle.NONE)
		
		# Clear button
		clearb.set_image(Gtk.Image.new_from_stock("gtk-delete", Gtk.IconSize.SMALL_TOOLBAR))
		clearb.set_relief(Gtk.ReliefStyle.NONE)
		
		# Pack
		grActions.attach(upb,		2, i, 1, 1)
		grActions.attach(downb,		3, i, 1, 1)
		grActions.attach(clearb,	4, i, 1, 1)
		
		# Disable 'up' button on 1st aciton
		if len(self.actions) == 0:
			upb.set_sensitive(False)
		# Reenable 'down' button on last action
		if len(self.actions) > 0:
			self.actions[-1][1][1].set_sensitive(True)
		# Disable 'down' on added (now last) action
		downb.set_sensitive(False)
		
		self.actions.append(action_data)
		self.update_action_field()
		grActions.show_all()
	
	
	def on_moveb_clicked(self, trash, direction, data):
		""" Handler for 'move action' buttons """
		action = data[0]
		readd = [ x[0] for x in self.actions ]
		index = readd.index(action) + direction
		if index < 0:
			# Not possible to move 1st item up
			return
		if index > len(readd):
			# Not possible to move last item down
			return
		readd.remove(action)
		readd.insert(index, action)
		self._refill_grid(readd)
		self.update_action_field()
	
	
	def on_clearb_clicked(self, trash, data):
		""" Handler for 'delete action' button """
		self._clear_grid()
		self.actions.remove(data)
		readd = [ x[0] for x in self.actions ]
		self._refill_grid(readd)
		self.update_action_field()
	
	
	def on_cbMacroType_changed(self, *a):
		self.update_action_field()
	
	
	def _clear_grid(self):
		""" Removes everything from UI """
		grActions = self.builder.get_object("grActions")
		for child in [] + grActions.get_children():
			grActions.remove(child)
	
	
	def _refill_grid(self, new_actions):
		""" Removes everything from UI and then adds updated stuff back """
		self._clear_grid()
		self.actions = []
		for a in new_actions:
			self._add_action(a)
	
	
	def on_change_delay(self, scale, trash, value, data):
		""" Called when delay slider is moved """
		ms = int(value)
		action = data[0]
		label = data[-1][-2]
		action.delay = value / 1000.0
		if ms < 1000:
			label.set_markup(_("<b>Delay: %sms</b>") % (ms,))
		else:
			s = ms / 1000.0
			label.set_markup(_("<b>Delay: %0.2fs</b>") % (s,))
		self.update_action_field()
	
	
	def _setup_editor(self, ae, action):
		""" Setups editor used to edit subaction """
		if self.mode == Action.AC_BUTTON:
			ae.set_button(self.id, action)
		elif self.mode == Action.AC_TRIGGER:
			ae.set_trigger(self.id, action)
		elif self.mode == Action.AC_STICK:
			ae.set_stick(action)
		elif self.mode == Action.AC_PAD:
			ae.set_pad(self.id, action)
	
	
	def on_actionb_clicked(self, trash, data):
		""" Handler clicking on action name """
		action, widgets = data
		def on_chosen(id, action, reopen=False):
			data[0] = action
			self._refill_grid([ x[0] for x in self.actions ])
			self.update_action_field()
			if reopen: self.on_actionb_clicked(trash, data)
		
		ae = ActionEditor(self.app, on_chosen)
		ae.set_title(_("Edit Action"))
		self._setup_editor(ae, action)
		ae.hide_modeshift()
		ae.hide_macro()
		ae.hide_name()
		ae.show(self.window)
	
	
	def on_btAddAction_clicked(self, *a):
		""" Handler for Add Action button """
		self._add_action(NoAction())
	
	
	def on_btAddDelay_clicked(self, *a):
		""" Handler for Add Delay button """
		self._add_action(SleepAction(0.5))
	
	
	def on_btClear_clicked	(self, *a):
		""" Handler for clear button """
		action = NoAction()
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		a = self._make_action()
		if self.ac_callback is not None:
			self.ac_callback(self.id, a)
		self.close()
	
	
	def _set_mode(self, mode, id, action):
		""" Common part of editor setup """
		btDefault = self.builder.get_object("btDefault")
		entName = self.builder.get_object("entName")
		cbMacroType = self.builder.get_object("cbMacroType")
		self.id = id
		self.mode = mode
		if action.repeat:
			cbMacroType.set_active(1)
		for a in action.actions:
			self._add_action(a)
		if action.name is not None:
			entName.set_text(action.name)
	
	
	def set_button(self, id, action):
		""" Setups editor as editor for button action """
		self._set_mode(Action.AC_BUTTON, id, action)
	
	
	def set_trigger(self, id, action):
		""" Setups editor as editor for trigger action """
		self._set_mode(Action.AC_TRIGGER, id, action)
	
	
	def set_stick(self, action):
		""" Setups action editor as editor for stick action """
		self._set_mode(Action.AC_STICK, Profile.STICK, action)


	def set_pad(self, id, action):
		""" Setups action editor as editor for pad action """
		self._set_mode(Action.AC_PAD, id, action)
