#!/usr/bin/env python2
"""
SC-Controller - BindingEditor

Base class for main application window and OSD Keyboard bindings editor.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.actions import ModeModifier, SensitivityModifier, FeedbackModifier
from scc.actions import DoubleclickModifier, HoldModifier
from scc.actions import NoAction, RingAction, MultiAction
from scc.actions import Macro, Type, Repeat, Cycle
from scc.constants import SCButtons, LEFT, RIGHT
from scc.profile import Profile
from scc.gui.controller_widget import TRIGGERS, PADS, STICKS, GYROS, BUTTONS, PRESSABLE
from scc.gui.controller_widget import ControllerPad, ControllerStick, ControllerGyro
from scc.gui.controller_widget import ControllerButton, ControllerTrigger
from scc.gui.modeshift_editor import ModeshiftEditor
from scc.gui.ae.buttons import is_button_togle, is_button_repeat
from scc.gui.ae.gyro_action import is_gyro_enable
from scc.gui.action_editor import ActionEditor
from scc.gui.macro_editor import MacroEditor
from scc.gui.ring_editor import RingEditor


class BindingEditor(object):
	
	def __init__(self, app):
		self.button_widgets = {}
		self.app = app
	
	
	def create_binding_buttons(self, use_icons=True, enable_press=True):
		"""
		Creates ControllerWidget instances for available Gtk.Buttons defined
		in glade file.
		"""
		for b in BUTTONS:
			w = self.builder.get_object("bt" + b.name)
			if w:
				self.button_widgets[b] = ControllerButton(self, b, use_icons, w)
		for b in TRIGGERS:
			w = self.builder.get_object("bt" + b)
			if w:
				self.button_widgets[b] = ControllerTrigger(self, b, use_icons, w)
		for b in PADS:
			w = self.builder.get_object("bt" + b)
			if w:
				self.button_widgets[b] = ControllerPad(self, b, use_icons, enable_press, w)
		for b in STICKS:
			w = self.builder.get_object("bt" + b)
			if w:
				self.button_widgets[b] = ControllerStick(self, b, use_icons, enable_press, w)
		w = self.builder.get_object("btSTICKPRESS")
		if w:
			self.button_widgets[SCButtons.STICKPRESS] = ControllerButton(self, SCButtons.STICKPRESS, use_icons, w)
		for b in GYROS:
			w = self.builder.get_object("bt" + b)
			if w:
				self.button_widgets[b] = ControllerGyro(self, b, use_icons, w)
	
	
	def on_action_chosen(self, id, action, mark_changed=True):
		"""
		Callback called when action editting is finished in editor.
		Should return None or action being replaced.
		"""
		raise TypeError("Non-overriden on_action_chosen")
	
	
	def set_action(self, profile, id, action):
		"""
		Stores action in profile.
		Returns formely stored action.
		"""
		before = NoAction()
		if id == SCButtons.STICKPRESS and Profile.STICK in self.button_widgets:
			before, profile.buttons[id] = profile.buttons[id], action
			self.button_widgets[Profile.STICK].update()
		elif id == SCButtons.CPADPRESS and Profile.CPAD in self.button_widgets:
			before, profile.buttons[id] = profile.buttons[id], action
			self.button_widgets[Profile.CPAD].update()
		elif id in PRESSABLE:
			before, profile.buttons[id] = profile.buttons[id], action
			self.button_widgets[id.name.replace("PRESS", "")].update()
		elif id in BUTTONS:
			before, profile.buttons[id] = profile.buttons[id], action
			self.button_widgets[id].update()
		elif id in TRIGGERS:
			# TODO: Use LT and RT in profile as well
			side = LEFT if id == "LT" else RIGHT
			before, profile.triggers[side] = profile.triggers[side], action
			self.button_widgets[id].update()
		elif id in GYROS:
			before, profile.gyro = profile.gyro, action
			self.button_widgets[id].update()
		elif id in STICKS + PADS:
			if id in STICKS:
				before, profile.stick = profile.stick, action
			elif id == Profile.LPAD:
				before, profile.pads[Profile.LEFT] = profile.pads[Profile.LEFT], action
			elif id == Profile.RPAD:
				before, profile.pads[Profile.RIGHT] = profile.pads[Profile.RIGHT], action
			else:
				before, profile.pads[Profile.CPAD] = profile.pads[Profile.CPAD], action
			self.button_widgets[id].update()
		return before
	
	
	def get_action(self, profile, id):
		"""
		Returns action for specified id.
		Returns None if id is not known.
		"""
		before = NoAction()
		if id in BUTTONS:
			return profile.buttons[id]
		elif id in PRESSABLE:
			return profile.buttons[id]
		elif id in TRIGGERS:
			# TODO: Use LT and RT in profile as well
			side = LEFT if id == "LT" else RIGHT
			return profile.triggers[side]
		elif id in GYROS:
			return profile.gyro
		elif id in STICKS + PADS:
			if id in STICKS:
				return profile.stick
			elif id == Profile.LPAD:
				return profile.pads[Profile.LEFT]
			elif id == Profile.RPAD:
				return profile.pads[Profile.RIGHT]
			else:
				return profile.pads[Profile.CPAD]
		return None
	
	
	def choose_editor(self, action, title, id=None):
		""" Chooses apropripate Editor instance for edited action """
		if isinstance(action, SensitivityModifier):
			action = action.action
		if isinstance(action, FeedbackModifier):
			action = action.action
		if id in GYROS:
			e = ActionEditor(self.app, self.on_action_chosen)
			e.set_title(title)
		elif isinstance(action, (ModeModifier, DoubleclickModifier, HoldModifier)) and not is_gyro_enable(action):
			e = ModeshiftEditor(self.app, self.on_action_chosen)
			e.set_title(_("Mode Shift for %s") % (title,))
		elif RingEditor.is_ring_action(action):
			e = RingEditor(self.app, self.on_action_chosen)
			e.set_title(title)
		elif isinstance(action, Type):
			# Type is subclass of Macro
			e = ActionEditor(self.app, self.on_action_chosen)
			e.set_title(title)
		elif isinstance(action, Macro) and not (is_button_togle(action) or is_button_repeat(action)):
			e = MacroEditor(self.app, self.on_action_chosen)
			e.set_title(_("Macro for %s") % (title,))
		else:
			e = ActionEditor(self.app, self.on_action_chosen)
			e.set_title(title)
		return e
	
	
	def hilight(self, button):
		""" Hilights button on image. Overriden by app. """
		pass
	
	
	def show_editor(self, id):
		raise TypeError("show_editor not overriden")
