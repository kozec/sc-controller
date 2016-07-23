#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Assigns emulated axis to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, MouseAction, MultiAction
from scc.modifiers import ModeModifier, SensitivityModifier
from scc.actions import GyroAction, GyroAbsAction
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
	CTXS = Action.AC_GYRO
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
		self._recursing = True
		cbGyroButton = self.builder.get_object("cbGyroButton")
		fill_buttons(cbGyroButton)
		self._recursing = False
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			if isinstance(action, NoAction):
				self.select_gyro_output("none")
				self.select_gyro_button(SCButtons.RPADTOUCH)
				return
			if isinstance(action, ModeModifier):
				b = action.order[0]
				action = action.mods[b]
				self.select_gyro_button(b)
			else:
				self.select_gyro_button(None)
			if isinstance(action, MouseAction):
				self.select_gyro_output("mouse")
				if len(action.parameters) > 0 and action.parameters[0] == YAW:
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
				elif ap[0] == Axes.ABS_RX and ap[-1] == Axes.ABS_RY:
					if isinstance(action, GyroAbsAction):
						self.select_gyro_output("right_abs")
					else:
						self.select_gyro_output("right")
			self.modifier_updated()
	
	
	def modifier_updated(self):
		cbInvertY = self.builder.get_object("cbInvertY")
		sens = self.editor.get_sensitivity()
		inverted = len(sens) >= 2 and sens[1] < 0
		if cbInvertY.get_active() != inverted:
			self._recursing = True
			cbInvertY.set_active(inverted)
			self._recursing = False
	
	
	def cbInvertY_toggled_cb(self, cb, *a):
		if self._recursing: return
		sens = list(self.editor.get_sensitivity())
		# Ensure that editor accepts Y sensitivity
		if len(sens) >= 2:
			sens[1] = abs(sens[1])
			if cb.get_active():
				# Ensure that Y sensitivity is negative
				sens[1] *= -1
		self.editor.set_sensitivity(*sens)
	
	
	def get_button_title(self):
		return _("Joystick or Mouse")
	
	
	def handles(self, mode, action):
		if isinstance(action, NoAction):
			return True
		if is_gyro_enable(action):
			action = action.mods[action.order[0]]
		if isinstance(action, GyroAction):	# Takes GyroAbsAction as well
			ap = action.parameters
			if (len(ap) == 3 and not ap[1]) or len(ap) == 2:
				if ap[0] == Axes.ABS_X and ap[-1] == Axes.ABS_Y:
					return True
				if ap[0] == Axes.ABS_RX and ap[-1] == Axes.ABS_RY:
					return True
			return False
		if isinstance(action, MultiAction):
			return False
		return True
	
	
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
		if button is not None:
			button = button.name
		for row in model:
			if button == row[0] and row[1] != None:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return
		self._recursing = False
	
	def update(self, *a):
		pass
	
	
	def send(self, *a):
		if self._recursing : return
		
		cbMode = self.builder.get_object("cbMode")
		cbYawRoll = self.builder.get_object("cbYawRoll")
		cbGyroButton = self.builder.get_object("cbGyroButton")
		action = cbMode.get_model().get_value(cbMode.get_active_iter(), 0)
		yawroll = cbYawRoll.get_model().get_value(cbYawRoll.get_active_iter(), 0)
		button = cbGyroButton.get_model().get_value(cbGyroButton.get_active_iter(), 0)
		
		match = re.match(r"([^\[]+)\[([^\|]+)\|([^\]]+)\](.*)", action)
		if match:
			grps = match.groups()
			if yawroll == YAW:
				action = "%s%s%s" % (grps[0], grps[1], grps[3])
			else:
				action = "%s%s%s" % (grps[0], grps[2], grps[3])
		action = self.parser.restart(action).parse()
		
		if button and action:
			action = ModeModifier(getattr(SCButtons, button), action)
		
		self.editor.set_action(action)


def is_gyro_enable(modemod):
	""" Returns True if ModeModifier instance is used to create "Gyro Enable Button" """
	if isinstance(modemod, ModeModifier):
		if modemod.default:
			return False
		if len(modemod.order) != 1:
			return False
		action = modemod.mods[modemod.order[0]]
		if isinstance(action, SensitivityModifier):
			action = action.action
		if isinstance(action, ModeModifier):
			return False
		if isinstance(action, MouseAction):
			return True
		if isinstance(action, GyroAction):	# Takes GyroAbsAction as well
			return True
		if isinstance(action, MultiAction):
			for a in action.actions:
				if not isinstance(a, GyroAction):
					return False
			return True
	return False


def fill_buttons(cb):
	cb.set_row_separator_func( lambda model, iter : model.get_value(iter, 1) is None )
	model = cb.get_model()
	for button, text in GyroActionComponent.BUTTONS:
		model.append(( None if button is None else button.name, text ))	
	cb.set_active(0)