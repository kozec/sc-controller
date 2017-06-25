#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Assigns emulated axis to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, AxisAction, MultiAction
from scc.actions import GyroAction, GyroAbsAction
from scc.modifiers import ModeModifier
from scc.constants import SCButtons
from scc.tools import ensure_size
from scc.gui.ae.gyro_action import is_gyro_enable, fill_buttons
from scc.gui.ae import AEComponent, describe_action
from scc.gui.simple_chooser import SimpleChooser

import os, logging, re
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
		cbGyroButton = self.builder.get_object("cbGyroButton")
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
				b = action.order[0]
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
						if pars[i]:
							self.axes[i] = pars[i]
							self.cbs[i].set_active(isinstance(a, GyroAbsAction))
			self.update()
			self._recursing = False
	
	
	def get_button_title(self):
		return _("Per Axis")
	
	
	def handles(self, mode, action):
		if is_gyro_enable(action):
			action = action.mods[action.order[0]]
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
		b.display_action(Action.AC_STICK, AxisAction(self.axes[i]))
		b.show(self.editor.window)
	
	
	def on_abs_changed(self, source, *a):
		if self._recursing : return
		self.send()
	
	
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
	
	
	def on_cbInvertGyro_toggled(self, cb, *a):
		lblGyroEnable = self.builder.get_object("lblGyroEnable")
		if cb.get_active():
			lblGyroEnable.set_label(_("Gyro Disable Button"))
		else:
			lblGyroEnable.set_label(_("Gyro Enable Button"))
		if not self._recursing:
			self.send()
	
	
	def update(self, *a):
		for i in xrange(0, 3):
			self.labels[i].set_label(describe_action(Action.AC_STICK, AxisAction, self.axes[i]))
	
	
	def send(self, *a):
		if self._recursing : return
		
		cbGyroButton = self.builder.get_object("cbGyroButton")
		cbInvertGyro = self.builder.get_object("cbInvertGyro")
		button = cbGyroButton.get_model().get_value(cbGyroButton.get_active_iter(), 0)
		
		normal, n_set    = [ None, None, None ], False
		absolute, a_set  = [ None, None, None ], False
		
		for i in xrange(0, 3):
			if self.axes[i] is not None:
				if self.cbs[i].get_active():
					absolute[i] = self.axes[i]
					a_set = True
				else:
					normal[i] = self.axes[i]
					n_set = True
		
		if n_set and a_set:
			action = MultiAction(GyroAction(*normal), GyroAbsAction(*absolute))
		elif n_set:
			action = GyroAction(*normal)
		elif a_set:
			action = GyroAbsAction(*absolute)
		else:
			action = NoAction()
		
		if button and action:
			if cbInvertGyro.get_active():
				action = ModeModifier(getattr(SCButtons, button), NoAction(), action)
			else:
				action = ModeModifier(getattr(SCButtons, button), action)
		
		self.editor.set_action(action)
