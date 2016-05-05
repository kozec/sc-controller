#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Assigns emulated axis to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, MouseAction
from scc.actions import GyroAction, GyroAbsAction
from scc.modifiers import ModeModifier
from scc.uinput import Keys, Axes, Rels
from scc.constants import SCButtons, YAW, ROLL
from scc.gui.parser import GuiActionParser, InvalidAction
from scc.gui.ae import AEComponent

import os, logging, re
log = logging.getLogger("AE.GyroAction")

__all__ = [ 'GyroActionComponent' ]


class GyroActionComponent(AEComponent):
	GLADE = "ae/gyro_action.glade"
	NAME = "gyro_action"
	CTXS = Action.AC_GYRO,
	PRIORITY = 3
	
	BUTTONS = (	# in order as displayed in combobox
		(None,					_('Always Active')),
		(None, None),
		(SCButtons.LT,			_('Left Trigger') ),
		(SCButtons.RT,			_('Right Trigger') ),
		(SCButtons.LB,			_('Left Bumper') ),
		(SCButtons.RB,			_('Right Bumper') ),
		(None, None),
		(SCButtons.LPADTOUCH,	_('Left Pad Touched') ),
		(SCButtons.RPADTOUCH,	_('Right Pad Touched') ),
		(SCButtons.LPAD,		_('Left Pad Pressed') ),
		(SCButtons.RPAD,		_('Right Pad Pressed') ),
		(None, None),
		(SCButtons.LGRIP,		_('Left Grip') ),
		(SCButtons.RGRIP,		_('Right Grip') ),
		(None, None),
		(SCButtons.A,			_('A') ),
		(SCButtons.B,			_('B') ),
		(SCButtons.X,			_('X') ),
		(SCButtons.Y,			_('Y') ),
		(None, None),
		(SCButtons.BACK,		_('Back (select)') ),
		(SCButtons.C,			_('Center') ),
		(SCButtons.START,		_('Start') ),
	)
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self._recursing = False
		self.parser = GuiActionParser()
	
	
	def load(self):
		if self.loaded : return
		AEComponent.load(self)
		cbGyroButton = self.builder.get_object("cbGyroButton")
		cbGyroButton.set_row_separator_func( lambda model, iter : model.get_value(iter, 1) is None )
		model = cbGyroButton.get_model()
		for button, text in self.BUTTONS:
			model.append(( None if button is None else button.name, text ))	
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			if isinstance(action, ModeModifier):
				print self.mods.keys()
			else:
				self.select_gyro_button(None)
			if isinstance(action, MouseAction):
				self.select_gyro_output("mouse")
				if len(action.parameters) >= 2 and action.parameters[1] == YAW:
					self.select_yaw_roll(YAW)
				else:
					self.select_yaw_roll(ROLL)
			elif isinstance(action, GyroAction):
				ap = action.parameters
				if len(ap) == 2:
					self.select_yaw_roll(YAW)
				else:
					self.select_yaw_roll(ROLL)
				if ap[0] == Axes.ABS_X and ap[-1] == Axes.ABS_Y:
					if isinstance(action, GyroAbsAction):
						self.select_gyro_output("left_abs")
					else:
						self.select_gyro_output("left")
					self.select_yaw_roll(ROLL)
				elif ap[0] == Axes.ABS_RX and ap[-1] == Axes.ABS_RY:
					if isinstance(action, GyroAbsAction):
						self.select_gyro_output("right_abs")
					else:
						self.select_gyro_output("right")
					self.select_yaw_roll(ROLL)
	
	
	def get_button_title(self):
		return _("Joystick or Mouse")
	
	
	@staticmethod
	def is_gyro_enable(modemod):
		""" Returns True if ModeModifier instance is used to create "Gyro Enable Button" """
		if isinstance(modemod, ModeModifier):
			if modemod.default:
				return False
			if len(modemod.mods) != 0:
				return False
			action = modemod.mods[modemod.mods.keys()[0]]
			if isinstance(action, ModeModifier):
				return False
			return GyroActionComponent._handles(action)
		return False
	
	
	@staticmethod
	def _handles(action):
		if GyroActionComponent.is_gyro_enable(action):
			return True
		if isinstance(action, MouseAction):
			return True
		if isinstance(action, GyroAction):	# Takes GyroAbsAction as well
			ap = action.parameters
			if (len(ap) == 3 and not ap[1]) or len(ap) == 2:
				if ap[0] == Axes.ABS_X and ap[-1] == Axes.ABS_Y:
					return True
				if ap[0] == Axes.ABS_RX and ap[-1] == Axes.ABS_RY:
					return True
		return False
	
	
	def handles(self, mode, action):
		if isinstance(action, NoAction):
			return True
		return GyroActionComponent._handles(action)
	
	
	def select_gyro_output(self, key):
		""" Just sets combobox value """
		cb = self.builder.get_object("cbMode")
		model = cb.get_model()
		self._recursing = True
		for row in model:
			if key == row[2]:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return
		self._recursing = False
	
	
	def select_yaw_roll(self, yawroll):
		""" Just sets combobox value """
		cb = self.builder.get_object("cbYawRoll")
		model = cb.get_model()
		self._recursing = True
		for row in model:
			if yawroll == row[0]:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return
		self._recursing = False
	
	
	def select_gyro_button(self, button):
		""" Just sets combobox value """
		cb = self.builder.get_object("cbGyroButton")
		model = cb.get_model()
		self._recursing = True
		for row in model:
			if button == row[0] and row[1] != None:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return
		self._recursing = False
	
	
	def update(self, *a):
		if self._recursing : return
		
		cbMode = self.builder.get_object("cbMode")
		cbYawRoll = self.builder.get_object("cbYawRoll")
		cbGyroButton = self.builder.get_object("cbGyroButton")
		action = cbMode.get_model().get_value(cbMode.get_active_iter(), 0)
		yawroll = cbYawRoll.get_model().get_value(cbYawRoll.get_active_iter(), 0)
		
		match = re.match(r"([^\[]+)\[([^\|]+)\|([^\]]+)\](.*)", action)
		if match:
			grps = match.groups()
			if yawroll == YAW:
				action = "%s%s%s" % (grps[0], grps[1], grps[3])
			else:
				action = "%s%s%s" % (grps[0], grps[2], grps[3])
		
		action = self.parser.restart(action).parse()
		self.editor.set_action(action)
