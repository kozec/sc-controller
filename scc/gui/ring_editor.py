#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.controller_widget import ControllerButton
from scc.gui.controller_widget import STICKS, PADS
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
from scc.constants import SCButtons
from scc.modifiers import ModeModifier, DoubleclickModifier, HoldModifier
from scc.actions import Action, RingAction, NoAction
from scc.profile import Profile

from gi.repository import Gtk, Gdk, GLib
import os, logging
log = logging.getLogger("RingEditor")

class RingEditor(Editor):
	GLADE = "ring_editor.glade"
	
	def __init__(self, app, callback):
		Editor.__init__(self)
		self.app = app
		self.id = None
		self.mode = Action.AC_BUTTON
		self.ac_callback = callback
		self.radius = 0.5
		self.actions = [ NoAction(), NoAction() ]
		self.setup_widgets()
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		b = lambda a : self.builder.get_object(a)
		self.action_widgets = (
			# Order goes: Action Button, Clear Button
			( b('btInner'),		b('btClearInner') ),
			( b('btOuter'),		b('btClearOuter') )
		)
		headerbar(self.builder.get_object("header"))
	
	
	def on_adjRadius_value_changed(self, scale, *a):
		self.radius = scale.get_value()
	
	
	def on_sclRadius_format_value(self, scale, value):
		return "%s%%" % (int(value * 100),)
	
	
	def on_Dialog_destroy(self, *a):
		self.remove_added_widget()
	
	
	def on_btClearRadius_clicked(self, *a):
		self.radius = 0.5
		self._update()
	
	
	def _choose_editor(self, action, cb):
		if isinstance(action, ModeModifier):
			from scc.gui.modeshift_editor import ModeshiftEditor	# Cannot be imported @ top
			e = ModeshiftEditor(self.app, cb)
			e.set_title(_("Edit Action"))
		else:
			from scc.gui.action_editor import ActionEditor	# Cannot be imported @ top
			e = ActionEditor(self.app, cb)
			e.set_title(_("Edit Action"))
			e.hide_macro()
			e.hide_ring()
		return e
	
	
	def on_actionb_clicked(self, clicked_button):
		for i in xrange(0, len(self.action_widgets)):
			button, clearb = self.action_widgets[i]
			if button == clicked_button:
				def on_chosen(id, action):
					self.actions[i] = action
					self._update()
				
				ae = self._choose_editor(self.actions[i], on_chosen)
				ae.set_input(self.id, self.actions[i])
				ae.show(self.window)
				return
	
	
	def on_clearb_clicked(self, clicked_button):
		for i in xrange(0, len(self.action_widgets)):
			button, clearb = self.action_widgets[i]
			if clearb == clicked_button:
				self.actions[i] = NoAction()
				self._update()
				return
	
	
	def on_btClear_clicked(self, *a):
		""" Handler for clear button """
		action = NoAction()
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def on_btCustomActionEditor_clicked(self, *a):
		""" Handler for 'Custom Editor' button """
		from scc.gui.action_editor import ActionEditor	# Can't be imported on top
		e = ActionEditor(self.app, self.ac_callback)
		e.set_input(self.id, self._make_action(), mode = self.mode)
		e.hide_action_buttons()
		e.hide_advanced_settings()
		e.set_title(_("Custom Action"))
		e.force_page(e.load_component("custom"), True)
		self.send_added_widget(e)
		self.close()
		e.show(self.get_transient_for())
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		if self.ac_callback is not None:
			self.ac_callback(self.id, self._make_action())
		self.close()
	
	
	def _make_action(self):
		""" Generates and returns Action instance """
		return RingAction(self.radius, *self.actions)
	
	
	def _update(self):
		for i in xrange(0, len(self.action_widgets)):
			button, clearb = self.action_widgets[i]
			button.set_label(self.actions[i].describe(Action.AC_BUTTON))
		self.builder.get_object("sclRadius").set_value(self.radius)
	
	
	def set_input(self, id, action, mode=None):
		btDefault = self.builder.get_object("btDefault")
		lblPressAlone = self.builder.get_object("lblPressAlone")
		self.id = id
		
		if isinstance(action, RingAction):
			self.radius = action.radius
			self.actions = [ action.inner, action.outer ]
			self._update()
