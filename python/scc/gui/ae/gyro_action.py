#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Gyro -> Joystick or Mouse component
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.actions import Action, NoAction, MouseAction, MultiAction, RangeOP
from scc.actions import MouseAbsAction, CemuHookAction
from scc.actions import GyroAction, GyroAbsAction
from scc.actions import ModeModifier, SensitivityModifier
from scc.uinput import Axes, Rels
from scc.constants import SCButtons, STICK, YAW, ROLL
from scc.gui.parser import GuiActionParser
from scc.gui.ae import AEComponent
from scc.tools import nameof

import logging, re
log = logging.getLogger("AE.GyroAction")

__all__ = [ 'GyroActionComponent' ]
TRIGGERS = ( nameof(SCButtons.LT), nameof(SCButtons.RT) )


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
		(SCButtons.LPADPRESS,	_('Left Pad Pressed') ),
		(SCButtons.RPADPRESS,	_('Right Pad Pressed') ),
		(None, None),
		(SCButtons.LGRIP,		_('Left Grip') ),
		(SCButtons.RGRIP,		_('Right Grip') ),
		(STICK,					_('Stick Tilted') ),
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
				self._recursing = True
				self.builder.get_object("cbInvertGyro").set_active(bool(action.default))
				self._recursing = False
				b = action.mods.keys()[0]
				action = action.mods[b] or action.default
				self.select_gyro_button(b)
			else:
				self.select_gyro_button(None)
			if isinstance(action, SensitivityModifier) and isinstance(action.action, MouseAction):
				# Mouse (Desktop)
				self.select_gyro_output("mouse")
				if len(action.action.parameters) > 0 and action.action.parameters[0] == YAW:
					self.select_yaw_roll(YAW)
				else:
					self.select_yaw_roll(ROLL)
				self.editor.set_default_sensitivity(3.5, 3.5, 3.5)
				self.editor.set_sensitivity(*action.sensitivity)
			elif isinstance(action, MouseAction):
				# Mouse (Camera)
				self.select_gyro_output("mouse_cam")
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
				elif ap[0] == Rels.REL_Y and ap[-1] == Rels.REL_X:
					self.select_gyro_output("mouse_stick")
			elif isinstance(action, CemuHookAction):
					self.select_gyro_output("cemuhook")
			self.modifier_updated()
	
	
	def modifier_updated(self):
		cbInvertY = self.builder.get_object("cbInvertY")
		sens = self.editor.get_sensitivity()
		inverted = len(sens) >= 2 and sens[1] < 0
		if cbInvertY.get_active() != inverted:
			self._recursing = True
			cbInvertY.set_active(inverted)
			self._recursing = False

		self.update()
	
	
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
			action = action.mods.values()[0] or action.default
			if isinstance(action, SensitivityModifier):
				action = action.action
		if isinstance(action, GyroAction):	# Takes GyroAbsAction as well
			ap = action.parameters
			if (len(ap) == 3 and not ap[1]) or len(ap) == 2:
				if ap[0] == Axes.ABS_X and ap[-1] == Axes.ABS_Y:
					return True
				elif ap[0] == Axes.ABS_RX and ap[-1] == Axes.ABS_RY:
					return True
				elif ap[0] == Rels.REL_Y and ap[-1] == Rels.REL_X:
					return True
			return False
		if isinstance(action, (MouseAction, MouseAbsAction, CemuHookAction)):
			return True
		return False
	
	
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
	
	
	def select_gyro_button(self, item):
		""" Just sets combobox value """
		cb = self.builder.get_object("cbGyroButton")
		rvSoftLevel = self.builder.get_object("rvSoftLevel")
		sclSoftLevel = self.builder.get_object("sclSoftLevel")
		model = cb.get_model()
		self._recursing = True
		button = None
		if isinstance(item, RangeOP):
			button = nameof(item.what)
			sclSoftLevel.set_value(item.value)
			rvSoftLevel.set_reveal_child(True)
		elif item is not None:
			button = nameof(item.name)
		for row in model:
			if button == row[0] and row[1] != None:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return
		self._recursing = False
	
	
	def on_cbInvertGyro_toggled(self, cb, *a):
		lblGyroEnable = self.builder.get_object("lblGyroEnable")
		if cb.get_active():
			lblGyroEnable.set_label(_("Gyro Disable Button"))
		else:
			lblGyroEnable.set_label(_("Gyro Enable Button"))
		if not self._recursing:
			self.send()
	
	
	def on_sclSoftLevel_format_value(self, scale, value):
		return  "%s%%" % (int(value * 100.0),)
	
	
	def update(self, *a):
		cbMode = self.builder.get_object("cbMode")
		cbYawRoll = self.builder.get_object("cbYawRoll")
		lblYawRoll = self.builder.get_object("lblYawRoll")
		key = cbMode.get_model().get_value(cbMode.get_active_iter(), 2)
		cbYawRoll.set_sensitive(key != "cemuhook")
		lblYawRoll.set_sensitive(key != "cemuhook")	
	
	
	def hidden(self):
		self.editor.set_default_sensitivity(1, 1, 1)
	
	
	def send(self, *a):
		if self._recursing : return
		
		cbMode = self.builder.get_object("cbMode")
		cbYawRoll = self.builder.get_object("cbYawRoll")
		rvSoftLevel = self.builder.get_object("rvSoftLevel")
		sclSoftLevel = self.builder.get_object("sclSoftLevel")
		cbGyroButton = self.builder.get_object("cbGyroButton")
		cbInvertGyro = self.builder.get_object("cbInvertGyro")
		action = cbMode.get_model().get_value(cbMode.get_active_iter(), 0)
		key = cbMode.get_model().get_value(cbMode.get_active_iter(), 2)
		yawroll = cbYawRoll.get_model().get_value(cbYawRoll.get_active_iter(), 0)
		item = cbGyroButton.get_model().get_value(cbGyroButton.get_active_iter(), 0)
		rvSoftLevel.set_reveal_child(item in TRIGGERS)
		
		match = re.match(r"([^\[]+)\[([^\|]+)\|([^\]]+)\](.*)", action)
		if match:
			grps = match.groups()
			if yawroll == YAW:
				action = "%s%s%s" % (grps[0], grps[1], grps[3])
			else:
				action = "%s%s%s" % (grps[0], grps[2], grps[3])
		action = self.parser.restart(action).parse()
		
		if item and action:
			# TODO: Restore this
			"""
			if item in TRIGGERS:
				what = RangeOP(getattr(SCButtons, item), ">=", sclSoftLevel.get_value())
			elif item == STICK:
				what = RangeOP(item, ">=", sclSoftLevel.get_value())
			else:
				what = getattr(SCButtons, item)
			"""
			what = getattr(SCButtons, item)
			if cbInvertGyro.get_active():
				action = ModeModifier(what, NoAction(), action)
			else:
				action = ModeModifier(what, action)
		if key == "mouse":
			self.editor.set_default_sensitivity(3.5, 3.5, 3.5)
		else:
			self.editor.set_default_sensitivity(1, 1, 1)
		
		self.update()
		self.editor.set_action(action)


def is_gyro_enable(modemod):
	""" Returns True if ModeModifier instance is used to create "Gyro Enable Button" """
	if isinstance(modemod, ModeModifier):
		if len(modemod.mods) != 1:
			return False
		action = modemod.mods.values()[0]
		if modemod.default:
			if not action:
				# Possibly, default action is gyro and mode is NoAction.
				# That would mean that Gyro Disable button mode is used.
				action = modemod.default
			else:
				return False
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
		model.append(( None if button is None else nameof(button), text ))	
	cb.set_active(0)
