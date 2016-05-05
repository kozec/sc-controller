#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Assigns emulated axis to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, AxisAction, MouseAction, XYAction
from scc.actions import TrackballAction, TrackpadAction
from scc.uinput import Keys, Axes, Rels
from scc.gui.parser import GuiActionParser, InvalidAction
from scc.gui.ae import AEComponent

import os, logging
log = logging.getLogger("AE.AxisAction")

__all__ = [ 'AxisActionComponent' ]


class AxisActionComponent(AEComponent):
	GLADE = "ae/axis_action.glade"
	NAME = "axis_action"
	CTXS = Action.AC_STICK, Action.AC_PAD,
	PRIORITY = 3
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self._recursing = False
		self.parser = GuiActionParser()
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			if isinstance(action, TrackpadAction):
				self.select_axis_output("trackpad")
				self.set_sensitivity(action)
			elif isinstance(action, TrackballAction):
				self.select_axis_output("trackball")
				self.set_sensitivity(action)
			elif isinstance(action, XYAction):
				p = [ None, None ]
				for x in (0, 1):
					if len(action.actions[0].parameters) >= x:
						p[x] = action.actions[x].parameters[0]
				if p[0] == Axes.ABS_X and p[1] == Axes.ABS_Y:
					self.select_axis_output("lstick")
					self.set_sensitivity(action.actions[0])
				elif p[0] == Axes.ABS_RX and p[1] == Axes.ABS_RY:
					self.select_axis_output("rstick")
					self.set_sensitivity(action.actions[0])
				elif p[0] == Axes.ABS_HAT0X and p[1] == Axes.ABS_HAT0Y:
					self.select_axis_output("dpad")
				elif p[0] == Rels.REL_HWHEEL and p[1] == Rels.REL_WHEEL:
					self.select_axis_output("wheel")
					self.set_sensitivity(action.actions[0])
			else:
				self.select_axis_output("none")
				
	
	def get_button_title(self):
		return _("Joystick or Mouse")
	
	
	def handles(self, mode, action):
		if isinstance(action, (NoAction, TrackballAction, InvalidAction)):
			return True
		if isinstance(action, XYAction):
			p = [ None, None ]
			for x in (0, 1):
				if len(action.actions[0].parameters) >= x:
					p[x] = action.actions[x].parameters[0]
			if p[0] == Axes.ABS_X and p[1] == Axes.ABS_Y:
				return True
			elif p[0] == Axes.ABS_RX and p[1] == Axes.ABS_RY:
				return True
			elif p[0] == Axes.ABS_HAT0X and p[1] == Axes.ABS_HAT0Y:
				return True
			elif p[0] == Rels.REL_HWHEEL and p[1] == Rels.REL_WHEEL:
				return True
		return False
	
	
	def select_axis_output(self, key):
		""" Just sets combobox value """
		model = self.builder.get_object("lstOutputMode")
		cb = self.builder.get_object("cbAxisOutput")
		self._recursing = True
		for row in model:
			if key == row[2]:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return
		self._recursing = False
	
	
	def set_sensitivity(self, action):
		""" Sets value for sensitivity slider, if value is defined in action """
		try:
			sensitivity = float(action.parameters[1])
		except:
			try:
				sensitivity = float(action.parameters[0])
			except: return
		sens = self.builder.get_object("sclSensitivity")
		sens.set_value(sensitivity)
	
	
	def on_btScaleClear_clicked(self, *a):
		sens = self.builder.get_object("sclSensitivity")
		sens.set_value(1.0)
		self.on_cbAxisOutput_changed()
	
	
	def on_cbAxisOutput_changed(self, *a):
		if self._recursing : return
		cbAxisOutput = self.builder.get_object("cbAxisOutput")
		rvSensitivity = self.builder.get_object("rvSensitivity")
		sens = self.builder.get_object("sclSensitivity")
		action = cbAxisOutput.get_model().get_value(cbAxisOutput.get_active_iter(), 0)
		has_sensitivity = "sensitivity" in action
		action = action.replace("sensitivity", str(sens.get_value()))
		action = self.parser.restart(action).parse()
		rvSensitivity.set_reveal_child(has_sensitivity)
		
		self.editor.set_action(action)
