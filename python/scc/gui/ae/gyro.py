#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Gyro -> Per Axis component
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.actions import Action, NoAction, AxisAction, MultiAction
from scc.actions import GyroAction, GyroAbsAction, RangeOP
from scc.actions import ModeModifier
from scc.constants import SCButtons, STICK
from scc.tools import ensure_size, nameof
from scc.uinput import Axes
from scc.gui.ae.gyro_action import TRIGGERS, is_gyro_enable, fill_buttons
from scc.gui.ae import AEComponent, describe_action
from scc.gui.simple_chooser import SimpleChooser

import logging
log = logging.getLogger("AE.Gyro")

__all__ = [ 'GyroComponent' ]


class GyroComponent(AEComponent):
	GLADE = "ae/gyro.glade"
	NAME = "gyro"
	CTXS = Action.AC_GYRO
	PRIORITY = 2
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self._recursing = False
		self.axes = [ None, None, None ]
	
	
	def load(self):
		if self.loaded : return
		AEComponent.load(self)
		cbGyroButton = self.builder.get_object("cbGyroButton")
		self._recursing = True
		fill_buttons(cbGyroButton)
		self._recursing = False
		self.buttons = [ self.builder.get_object(x) for x in ("btPitch", "btYaw", "btRoll") ]
		self.cbs = [ self.builder.get_object(x) for x in ("cbPitchAbs", "cbYawAbs", "cbRollAbs") ]
		self.labels = [ self.builder.get_object(x) for x in ("lblPitch", "lblYaw", "lblRoll") ]
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			if isinstance(action, ModeModifier):
				self._recursing = True
				self.builder.get_object("cbInvertGyro").set_active(bool(action.default))
				self._recursing = False
				b = action.mods.keys()[0]
				action = action.mods[b] or action.default
				self.select_gyro_button(b)
			else:
				self.select_gyro_button(None)
			
			actions = [ action ]
			if isinstance(action, MultiAction):
				actions = action.actions
			
			self._recursing = True
			for a in actions:
				if isinstance(a, GyroAction):
					pars = ensure_size(3, a.parameters)
					for i in xrange(0, 3):
						if pars[i] is not None:
							self.axes[i] = pars[i]
							self.cbs[i].set_active(isinstance(a, GyroAbsAction))
			self.update()
			self._recursing = False
	
	
	def get_button_title(self):
		return _("Per Axis")
	
	
	def handles(self, mode, action):
		if is_gyro_enable(action):
			action = action.mods.values()[0]
		if isinstance(action, GyroAction):	# Takes GyroAbsAction as well
			return True
		if isinstance(action, MultiAction):
			for a in action.actions:
				if not isinstance(a, GyroAction):
					return False
			return True
		return False
	
	
	def on_select_axis(self, source, *a):
		i = self.buttons.index(source)
		def cb(action):
			self.axes[i] = action.parameters[0]
			self.update()
			self.send()
		b = SimpleChooser(self.app, "axis", cb)
		b.set_title(_("Select Axis"))
		b.hide_mouse()
		a = AxisAction(self.axes[i]) if self.axes[i] is not None else NoAction()
		b.display_action(Action.AC_STICK, a)
		b.show(self.editor.window)
	
	
	def on_abs_changed(self, source, *a):
		if self._recursing : return
		self.send()
	
	
	def select_gyro_button(self, item):
		""" Just sets combobox value """
		cb = self.builder.get_object("cbGyroButton")
		rvSoftLevel = self.builder.get_object("rvSoftLevel")
		sclSoftLevel = self.builder.get_object("sclSoftLevel")
		lblSoftLevel = self.builder.get_object("lblSoftLevel")
		model = cb.get_model()
		self._recursing = True
		button = None
		if isinstance(item, RangeOP):
			button = nameof(item.what)
			sclSoftLevel.set_value(item.value)
			rvSoftLevel.set_reveal_child(True)
			if item.what == STICK:
				lblSoftLevel.set_label(_("Stick deadzone"))
			else:
				lblSoftLevel.set_label(_("Trigger Pull Level"))
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
		for i in xrange(0, 3):
			self.labels[i].set_label(describe_action(Action.AC_STICK, AxisAction, self.axes[i]))
	
	
	def send(self, *a):
		if self._recursing : return
		
		rvSoftLevel = self.builder.get_object("rvSoftLevel")
		sclSoftLevel = self.builder.get_object("sclSoftLevel")
		cbGyroButton = self.builder.get_object("cbGyroButton")
		cbInvertGyro = self.builder.get_object("cbInvertGyro")
		item = cbGyroButton.get_model().get_value(cbGyroButton.get_active_iter(), 0)
		rvSoftLevel.set_reveal_child(item in TRIGGERS)
		
		normal, n_set    = [ None, None, None ], False
		absolute, a_set  = [ None, None, None ], False
		
		for i in xrange(0, 3):
			if self.axes[i] is not None:
				if self.cbs[i].get_active():
					absolute[i] = Axes(self.axes[i])
					a_set = True
				else:
					normal[i] = Axes(self.axes[i])
					n_set = True
		
		if n_set and a_set:
			action = MultiAction(GyroAction(*normal), GyroAbsAction(*absolute))
		elif n_set:
			action = GyroAction(*normal)
		elif a_set:
			action = GyroAbsAction(*absolute)
		else:
			action = NoAction()
		
		if item and action:
			what = getattr(SCButtons, item)
			# TODO: Restore this
			#if item in TRIGGERS:
			#	what = RangeOP(what, ">=", sclSoftLevel.get_value())
			if cbInvertGyro.get_active():
				action = ModeModifier(what, NoAction(), action)
			else:
				action = ModeModifier(what, action)
		
		self.editor.set_action(action)

