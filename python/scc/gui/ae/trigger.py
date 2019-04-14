#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Trigger-as-button Component

Assigns one or two emulated buttons to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.constants import TRIGGER_MIN, TRIGGER_HALF, TRIGGER_CLICK, TRIGGER_MAX
from scc.actions import TriggerAction, ButtonAction, AxisAction, MouseAction
from scc.actions import Action, NoAction, MultiAction
from scc.actions import FeedbackModifier
from scc.gui.ae import AEComponent, describe_action
from scc.gui.area_to_action import action_to_area
from scc.gui.simple_chooser import SimpleChooser
from scc.gui.binding_editor import BindingEditor
from scc.gui.parser import InvalidAction

import os, logging
log = logging.getLogger("AE.TriggerAB")

__all__ = [ 'TriggerComponent' ]


class TriggerComponent(AEComponent, BindingEditor):
	GLADE = "ae/trigger.glade"
	NAME = "trigger"
	CTXS = Action.AC_TRIGGER
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		BindingEditor.__init__(self, app)
		self._recursing = False
		self.half = NoAction()
		self.full = NoAction()
		self.analog = NoAction()
	
	
	def handles(self, mode, action):
		if isinstance(action, NoAction):
			return True
		sucess, half, full, analog = TriggerComponent._split(action)
		return sucess
	
	
	@staticmethod
	def _split(action):
		"""
		Splits passed action so it can be displayed in UI.
		Returns (sucess, half, full, analog), with three actions
		for each UI element.
		Note that each returned action may be TriggerAction.
		
		If passed action cannot be decoded,
		'sucess' element of tuple is set to False
		"""
		half, full, analog = NoAction(), NoAction(), NoAction()
		actions = action.actions if isinstance(action, MultiAction) else [ action ]
		for a in actions:
			effective = TriggerComponent._strip_trigger(a).strip()
			if isinstance(effective, AxisAction):
				if analog:
					# UI can do only one analog action per trigger
					return False, half, full, analog
				analog = a
			elif isinstance(effective, MouseAction):
				if analog:
					# UI can do only one analog action per trigger
					return False, half, full, analog
				analog = a
			elif isinstance(a, TriggerAction):
				if full and half:
					# UI can handle only one full and
					# one half-press action
					return False, half, full, analog
				if a.release_level == TRIGGER_MAX:
					if full and a.press_level < full.press_level:
						if half:
							# UI can handle only one half-press action
							return False, half, full, analog
						half = a
					elif full:
						if half:
							# UI can handle only one half-press action
							return False, half, full, analog
						half, full = full, a
					else:
						full = a
				else:
					if half:
						# UI can handle only one half-press action
						return False, half, full, analog
					half = a
			elif isinstance(a, NoAction):
				# Ignore theese
				pass
			else:
				# Unhandled action type
				return False, half, full, analog
		if full and not half:
			full, half = NoAction(), full
		return True, half, full, analog
	
	
	@staticmethod
	def _strip_trigger(action):
		"""
		If passed action is TriggerAction, returns its child action.
		Returns passed action otherwise.
		"""
		if isinstance(action, TriggerAction):
			return action.child
		return action
	
	
	def get_button_title(self):
		return _("Key or Button")
	
	
	def set_action(self, mode, action):
		self.half, self.full, self.analog = NoAction(), NoAction(), NoAction()
		sucess, half, full, analog = TriggerComponent._split(action)
		if sucess:
			self._recursing = True
			self.half, self.full, self.analog = (TriggerComponent._strip_trigger(x) for x in (half, full, analog))
			if half:
				self.builder.get_object("sclPartialLevel").set_value(half.press_level)
				self.builder.get_object("cbReleasePartially").set_active(half.release_level < TRIGGER_MAX)
			if full:
				self.builder.get_object("sclFullLevel").set_value(full.press_level)
			if isinstance(analog, TriggerAction):
				self.builder.get_object("sclARangeStart").set_value(analog.press_level)
				self.builder.get_object("sclARangeEnd").set_value(analog.release_level)
			
			self._recursing = False
		self.update()
	
	
	def update(self):
		self.builder.get_object("lblPartPressed").set_label(describe_action(Action.AC_BUTTON, ButtonAction, self.half))
		self.builder.get_object("lblFullPressed").set_label(describe_action(Action.AC_BUTTON, ButtonAction, self.full))
		self.builder.get_object("lblAnalog").set_label(describe_action(Action.AC_BUTTON, AxisAction, self.analog))
	
	
	def send(self):
		actions = []
		half_level = int(self.builder.get_object("sclPartialLevel").get_value())
		full_level = int(self.builder.get_object("sclFullLevel").get_value())
		release = self.builder.get_object("cbReleasePartially").get_active()
		
		if self.half:
			if self.full and release:
				actions.append(TriggerAction(half_level, full_level, self.half))
			else:
				actions.append(TriggerAction(half_level, TRIGGER_MAX, self.half))
		if self.full:
			actions.append(TriggerAction(full_level, TRIGGER_MAX, self.full))
		
		if self.analog:
			analog_start = int(self.builder.get_object("sclARangeStart").get_value())
			analog_end   = int(self.builder.get_object("sclARangeEnd").get_value())
			if analog_start == TRIGGER_MIN and analog_end == TRIGGER_MAX:
				actions.append(self.analog)
			else:
				actions.append(TriggerAction(analog_start, analog_end, self.analog))
		
		self.editor.set_action(MultiAction.make(*actions))
	
	
	def on_btFullPressedClear_clicked(self, *a):
		self.full = NoAction()
		self.update()
		self.send()
	
	
	def on_btAnalogClear_clicked(self, *a):
		self.analog = NoAction()
		self.update()
		self.send()
	
	
	def on_ui_value_changed(self, *a):
		if not self._recursing:
			self.send()
	
	
	def on_btPartPressed_clicked(self, *a):
		""" 'Partialy Pressed Action' handler """
		ae = self.choose_editor(self.half, "")
		ae.set_title(_("Select Partialy Pressed Action"))
		ae.hide_name()
		ae.set_input("half", self.half, mode = Action.AC_BUTTON)
		ae.show(self.editor.window)
	
	
	def on_btFullPress_clicked(self, *a):
		""" 'Fully Pressed Action' handler """
		ae = self.choose_editor(self.full, "")
		ae.set_title(_("Select Fully Pressed Action"))
		ae.hide_name()
		ae.set_input("full", self.full, mode = Action.AC_BUTTON)
		ae.show(self.editor.window)
	
	
	def on_btAnalog_clicked(self, *a):
		""" 'Analog Output' handler """
		b = SimpleChooser(self.app, "axis", lambda action: self.on_action_chosen("analog", action) )
		b.set_title(_("Select Analog Axis"))
		b.display_action(Action.AC_STICK, self.analog)
		b.show(self.editor.window)
	
	
	def on_action_chosen(self, i, action, mark_changed=True):
		if i == "full":
			self.full = action
		elif i == "half":
			self.half = action
		else:
			self.analog = action
		self.update()
		self.send()
	
	
	def on_btFullyPresedClear_clicked(self, *a):
		self.builder.get_object("sclFullLevel").set_value(TRIGGER_CLICK)
	
	
	def on_btPartPresedClear_clicked(self, *a):
		self.builder.get_object("sclPartialLevel").set_value(TRIGGER_HALF)
	
	
	def on_btARangeStartClear_clicked(self, *a):
		self.builder.get_object("sclARangeStart").set_value(TRIGGER_MIN)
	
	
	def on_btARangeEndClear_clicked(self, *a):
		self.builder.get_object("sclARangeEnd").set_value(TRIGGER_MAX)
