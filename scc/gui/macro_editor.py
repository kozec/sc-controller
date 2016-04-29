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
from scc.actions import Action, ButtonAction, NoAction, SleepAction
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
	
	
	def _add_action(self, action):
		grActions = self.builder.get_object("grActions")
		model = self.builder.get_object("lstPressClickOrHold")
		i = len(self.actions) + 1
		
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
		
		b.connect('clicked', self.on_actionb_clicked, action_data)
		
		# Move Up button
		upb.set_image(Gtk.Image.new_from_stock("gtk-go-up", Gtk.IconSize.SMALL_TOOLBAR))
		upb.set_relief(Gtk.ReliefStyle.NONE)
		
		# Move Down button
		downb.set_image(Gtk.Image.new_from_stock("gtk-go-down", Gtk.IconSize.SMALL_TOOLBAR))
		downb.set_relief(Gtk.ReliefStyle.NONE)
		
		# Clear button
		clearb.set_image(Gtk.Image.new_from_stock("gtk-delete", Gtk.IconSize.SMALL_TOOLBAR))
		clearb.set_relief(Gtk.ReliefStyle.NONE)
		clearb.connect('clicked', self.on_clearb_clicked, action_data)
		
		# Pack
		grActions.attach(downb,		2, i, 1, 1)
		grActions.attach(upb,		3, i, 1, 1)
		grActions.attach(clearb,	4, i, 1, 1)
		
		self.actions.append(action_data)
		grActions.show_all()
	
	
	def on_clearb_clicked(self, trash, data):
		grActions = self.builder.get_object("grActions")
		self.actions.remove(data)
		for child in [] + grActions.get_children():
			grActions.remove(child)
		readd = [ x[0] for x in self.actions ]
		self.actions = []
		for a in readd:
			self._add_action(a)
	
	
	def _setup_editor(self, ae, action):
		if self.mode == Action.AC_BUTTON:
			ae.set_button(self.id, action)
		elif self.mode == Action.AC_TRIGGER:
			ae.set_trigger(self.id, action)
		elif self.mode == Action.AC_STICK:
			ae.set_stick(action)
		elif self.mode == Action.AC_PAD:
			ae.set_pad(self.id, action)		
	
	
	def on_change_delay(self, scale, trash, value, data):
		ms = int(value)
		label = data[-1][-2]
		if ms < 1000:
			label.set_markup(_("<b>Delay: %sms</b>") % (ms,))
		else:
			s = ms / 1000.0
			label.set_markup(_("<b>Delay: %0.2fs</b>") % (s,))
	
	
	def on_actionb_clicked(self, trash, clicked_button):
		for i in self.actions:
			button, action, l, b, clearb = i
			if button == clicked_button:
				def on_chosen(id, action):
					b.set_label(action.describe(self.mode))
					i[1] = action
				
				ae = ActionEditor(self.app, on_chosen)
				ae.set_title(_("Edit Action"))
				ae.hide_modeshift()
				self._setup_editor(ae, action)
				ae.show(self.window)
				return
	

	def on_btAddAction_clicked(self, *a):
		self._add_action(NoAction())
	
	
	def on_btAddDelay_clicked(self, *a):
		self._add_action(SleepAction(0.5))
	
	
	def on_btClear_clicked	(self, *a):
		""" Handler for clear button """
		action = NoAction()
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		pars = []
		for button, action, l, b, clearb in self.actions:
			pars += [ button, action ]
		if self.default:
			pars += [ self.default ]
		action = ModeModifier(*pars)
		if len(pars) == 0:
			# No action is actually set
			action = NoAction()
		elif len(pars) == 1:
			# Only default action left
			action = self.default
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def _set_mode(self, mode, id, action):
		btDefault = self.builder.get_object("btDefault")
		self.id = id
		self.mode = mode
		for a in action.actions:
			self._add_action(a)
	
	
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
