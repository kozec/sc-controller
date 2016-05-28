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
from scc.actions import AreaAction, WinAreaAction, RelAreaAction, RelWinAreaAction
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
		self.relative_area = False
		self.parser = GuiActionParser()
	
	
	def load(self):
		if self.loaded : return
		AEComponent.load(self)
		cbAreaType = self.builder.get_object("cbAreaType")
		cbAreaType.set_row_separator_func( lambda model, iter : model.get_value(iter, 0) == "-" )
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			if isinstance(action, TrackpadAction):
				self.select_action_type("trackpad")
			elif isinstance(action, TrackballAction):
				self.select_action_type("trackball")
			elif isinstance(action, CircularAction):
				self.select_action_type("circular")
			elif isinstance(action, AreaAction):
				self.load_area_action(action)
				self.select_action_type("area")
			elif isinstance(action, XYAction):
				p = [ None, None ]
				for x in (0, 1):
					if len(action.actions[0].strip().parameters) >= x:
						if len(action.actions[x].strip().parameters) > 0:
							p[x] = action.actions[x].strip().parameters[0]
				if p[0] == Axes.ABS_X and p[1] == Axes.ABS_Y:
					self.select_action_type("lstick")
				elif p[0] == Axes.ABS_RX and p[1] == Axes.ABS_RY:
					self.select_action_type("rstick")
				elif p[0] == Axes.ABS_HAT0X and p[1] == Axes.ABS_HAT0Y:
					self.select_action_type("dpad")
				elif p[0] == Rels.REL_HWHEEL and p[1] == Rels.REL_WHEEL:
					self.select_action_type("wheel")
			else:
				self.select_action_type("none")
	
	
	def load_area_action(self, action):
		"""
		Load AreaAction values into UI.
		"""
		cbAreaType = self.builder.get_object("cbAreaType")
		
		x1, y1, x2, y2 = action.coords
		self.relative_area = False
		if isinstance(action, RelAreaAction):
			key = "screensize"
			self.relative_area = True
			x1, y1, x2, y2 = x1 * 100.0, y1 * 100.0, x2 * 100.0, y2 * 100.0
		elif isinstance(action, RelWinAreaAction):
			key = "windowsize"
			self.relative_area = True
			x1, y1, x2, y2 = x1 * 100.0, y1 * 100.0, x2 * 100.0, y2 * 100.0
		else:
			t1 = "1" if x1 < 0 and x2 < 0 else "0"
			t2 = "1" if y1 < 0 and y2 < 0 else "0"
			x1, y1, x2, y2 = abs(x1), abs(y1), abs(x2), abs(y2)
			if x2 < x1 : x1, x2 = x2, x1
			if y2 < y1 : y1, y2 = y2, y1
			if isinstance(action, WinAreaAction):
				key = "window-%s%s" % (t1, t2)
			else:
				key = "screen-%s%s" % (t1, t2)
		self.builder.get_object("sbAreaX1").set_value(x1)
		self.builder.get_object("sbAreaY1").set_value(y1)
		self.builder.get_object("sbAreaX2").set_value(x2)
		self.builder.get_object("sbAreaY2").set_value(y2)
		
		self._recursing = True
		for row in cbAreaType.get_model():
			if key == row[1]:
				cbAreaType.set_active_iter(row.iter)
				break
		self._recursing = False
	
	
	def make_area_action(self):
		"""
		Loads values from UI into new AreaAction or subclass.
		"""
		# Prepare
		cbAreaType = self.builder.get_object("cbAreaType")
		# Read numbers
		x1 = self.builder.get_object("sbAreaX1").get_value()
		y1 = self.builder.get_object("sbAreaY1").get_value()
		x2 = self.builder.get_object("sbAreaX2").get_value()
		y2 = self.builder.get_object("sbAreaY2").get_value()
		# Determine exact action type by looking into Area Type checkbox
		# (this part may seem little crazy)
		# ... numbers
		key = cbAreaType.get_model().get_value(cbAreaType.get_active_iter(), 1)
		if "-" in key:
			if key[-2] == "1":
				# Before-last character ius "1", that means that X coords are
				# counted from other side and has to be negated
				x1, x2 = -x1, -x2
			if key[-1] == "1":
				# Key ends with "1". Same thing as above but for Y coordinate
				y1, y2 = -y1, -y2
		if "size" in key:
			x1, y1, x2, y2 = x1 / 100.0, y1 / 100.0, x2 / 100.0, y2 / 100.0
		# ... class 
		if "window-" in key:
			cls = WinAreaAction
			self.relative_area = False
		elif "screensize" == key:
			cls = RelAreaAction
			self.relative_area = True
		elif "windowsize" == key:
			cls = RelWinAreaAction
			self.relative_area = True
		else: # "screen" in key
			cls = AreaAction
			self.relative_area = False
		return cls(x1, y1, x2, y2)
	
	
	def get_button_title(self):
		return _("Joystick or Mouse")
	
	
	def handles(self, mode, action):
		if isinstance(action, (NoAction, TrackballAction, CircularAction,
					InvalidAction, AreaAction)):
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
	
	
	def select_action_type(self, key):
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
	
	
	def on_area_options_changed(self, *a):
		self.editor.set_action(self.make_area_action())
		for x in ('sbAreaX1', 'sbAreaX2', 'sbAreaY1', 'sbAreaY2'):
			spin = self.builder.get_object(x)
			if self.relative_area:
				spin.get_adjustment().set_upper(100)
			else:
				spin.get_adjustment().set_upper(1000)
			self.on_sbArea_output(spin)
	
	
	def on_sbArea_output(self, button, *a):
		if self.relative_area:
			button.set_text("%s %%" % (button.get_value()))
		else:
			button.set_text("%s px" % (button.get_value()))
	
	
	def on_sbArea_focus_out_event(self, button, *a):
		GLib.idle_add(self.on_sbArea_output, button)
	
	
	def on_sbArea_changed(self, button, *a):
		self.on_sbArea_output(button)
		self.on_area_options_changed(button)
	
	
	def on_cbAxisOutput_changed(self, *a):
		cbAxisOutput = self.builder.get_object("cbAxisOutput")
		stActionData = self.builder.get_object("stActionData")
		key = cbAxisOutput.get_model().get_value(cbAxisOutput.get_active_iter(), 2)
		if key == 'area':
			stActionData.set_visible_child(self.builder.get_object("grArea"))
			action = self.make_area_action()
		else:
			stActionData.set_visible_child(self.builder.get_object("nothing"))
			action = cbAxisOutput.get_model().get_value(cbAxisOutput.get_active_iter(), 0)
			action = self.parser.restart(action).parse()
		
		self.editor.set_action(action)
