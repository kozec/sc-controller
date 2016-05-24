#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Assigns emulated axis to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, AxisAction, MouseAction, XYAction
from scc.actions import TrackballAction, TrackpadAction, CircularAction
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
			elif isinstance(action, TrackballAction):
				self.select_axis_output("trackball")
			elif isinstance(action, CircularAction):
				self.select_axis_output("circular")
			elif isinstance(action, XYAction):
				p = [ None, None ]
				for x in (0, 1):
					if len(action.actions[0].strip().parameters) >= x:
						if len(action.actions[x].strip().parameters) > 0:
							p[x] = action.actions[x].strip().parameters[0]
				if p[0] == Axes.ABS_X and p[1] == Axes.ABS_Y:
					self.select_axis_output("lstick")
				elif p[0] == Axes.ABS_RX and p[1] == Axes.ABS_RY:
					self.select_axis_output("rstick")
				elif p[0] == Axes.ABS_HAT0X and p[1] == Axes.ABS_HAT0Y:
					self.select_axis_output("dpad")
				elif p[0] == Rels.REL_HWHEEL and p[1] == Rels.REL_WHEEL:
					self.select_axis_output("wheel")
			else:
				self.select_axis_output("none")
				
	
	def get_button_title(self):
		return _("Joystick or Mouse")
	
	
	def handles(self, mode, action):
		if isinstance(action, (NoAction, TrackballAction, CircularAction, InvalidAction)):
			return True
		if isinstance(action, XYAction):
			p = [ None, None ]
			for x in (0, 1):
				if len(action.actions[0].strip().parameters) >= x:
					if len(action.actions[x].strip().parameters) > 0:
						p[x] = action.actions[x].strip().parameters[0]
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
	
	
	def on_cbAxisOutput_changed(self, *a):
		if self._recursing : return
		cbAxisOutput = self.builder.get_object("cbAxisOutput")
		action = cbAxisOutput.get_model().get_value(cbAxisOutput.get_active_iter(), 0)
		action = self.parser.restart(action).parse()
		
		self.editor.set_action(action)
