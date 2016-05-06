#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.modifiers import Modifier, ClickModifier, ModeModifier, SensitivityModifier
from scc.actions import Action, XYAction, NoAction
from scc.profile import Profile
from scc.macros import Macro
from scc.gui.modeshift_editor import ModeshiftEditor
from scc.gui.macro_editor import MacroEditor
from scc.gui.parser import InvalidAction
from scc.gui.dwsnc import headerbar
from scc.gui.ae import AEComponent
from scc.gui.editor import Editor
import os, logging, importlib, types
log = logging.getLogger("ActionEditor")


class ActionEditor(Editor):
	GLADE = "action_editor.glade"
	ERROR_CSS = " #error {background-color:green; color:red;} "
	COMPONENTS = (
		'axis',
		'axis_action',
		'gyro',
		'gyro_action',
		'buttons',
		'dpad',
		'per_axis',
		'trigger_ab',
		'custom',
	)
	css = None

	def __init__(self, app, callback):
		self.app = app
		self.id = None
		self.components = []	# List of available components
		self.c_buttons = {} 	# Component-to-button dict
		self.sens_widgets = []	# Sensitivity sliders, labels and 'clear' buttons
		self.sens = [1.0] * 3	# Sensitivity slider values
		self.click = False		# Click modifier value. None for disabled
		self.setup_widgets()
		self.load_components()
		self.ac_callback = callback	# This is different callback than ButtonChooser uses
		if ActionEditor.css is None:
			ActionEditor.css = Gtk.CssProvider()
			ActionEditor.css.load_from_data(str(ActionEditor.ERROR_CSS))
			Gtk.StyleContext.add_provider_for_screen(
					Gdk.Screen.get_default(),
					ActionEditor.css,
					Gtk.STYLE_PROVIDER_PRIORITY_USER)
		self._action = NoAction()
		self._multiparams = [ None ] * 8
		self._mode = None
		self._recursing = False
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.window = self.builder.get_object("Dialog")
		self.builder.connect_signals(self)
		headerbar(self.builder.get_object("header"))
		XYZ = "XYZ"	# duh
		for i in (0, 1, 2):
			self.sens_widgets.append((
				self.builder.get_object("sclSens%s" % (XYZ[i],)),
				self.builder.get_object("lblSens%s" % (XYZ[i],)),
				self.builder.get_object("btClearSens%s" % (XYZ[i],)),
			))
	
	
	def load_components(self):
		""" Loads list of editor components """
		# Import and load components
		for c in self.COMPONENTS:
			mod = importlib.import_module("scc.gui.ae.%s" % (c,))
			for x in dir(mod):
				cls = getattr(mod, x)
				if isinstance(cls, (type, types.ClassType)) and issubclass(cls, AEComponent):
					if cls is not AEComponent:
						self.components.append(cls(self.app, self))
		self._selected_component = None
	
	
	def on_action_type_changed(self, obj):
		"""
		Called when user clicks on one of Action Type buttons.
		"""
		# Prevent recurson
		if self._recursing : return
		self._recursing = True
		# Don't allow user to deactivate buttons - I'm using them as
		# radio button and you can't 'uncheck' radiobutton by clicking on it
		if not obj.get_active():
			obj.set_active(True)
			self._recursing = False
			return
		
		component = None
		for c in self.c_buttons:
			b = self.c_buttons[c]
			if obj == b:
				component = c
			else:
				b.set_active(False)
		self._recursing = False
		
		stActionModes = self.builder.get_object("stActionModes")
		component.set_action(self._mode, self._action)
		self._selected_component = component
		stActionModes.set_visible_child(component.get_widget())
		
		stActionModes.show_all()
	
	
	def _set_title(self):
		""" Copies title from text entry into action instance """
		entName = self.builder.get_object("entName")
		self._action.name = entName.get_text().strip(" \t\r\n")
		if len(self._action.name) < 1:
			self._action.name = None
	
	
	def hide_sensitivity(self, *indexes):
		"""
		Hides sensitivity settings for one or more axes.
		Used when editing whatever is not a gyro.
		"""
		for i in (0, 1, 2):
			for widget in self.sens_widgets[i]:
				widget.set_sensitive(i not in indexes)
				widget.set_visible(i not in indexes)
		self.sens = self.sens[0:len(indexes)+1]
		self.builder.get_object("lblSensitivityHeader").set_visible(len(indexes) < 3)
	
	
	def hide_require_click(self):
		"""
		Hides 'Require Click' checkbox.
		Used when editing everythin but pad.
		"""
		self.builder.get_object("cbRequireClick").set_visible(False)
	
	
	def hide_advanced_settings(self):
		"""
		Hides entire 'Advanced Settings' expander.
		"""
		self.hide_sensitivity()
		self.hide_require_click()
		self.builder.get_object("exMore").set_visible(False)
		self.builder.get_object("rvMore").set_visible(False)
	
	
	def on_btClearSens_clicked(self, source, *a):
		for scale, label, button in self.sens_widgets:
			if source == button:
				scale.set_value(1.0)
	
	
	def on_btClear_clicked	(self, *a):
		""" Handler for clear button """
		action = NoAction()
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		if self.ac_callback is not None:
			self._set_title()
			self.ac_callback(self.id, self.generate_modifiers(self._action))
		self.close()
	
	
	def on_btModeshift_clicked(self, *a):
		""" Asks main window to close this one and display modeshift editor """
		if self.ac_callback is not None:
			# Convert current action into modeshift and send it to main window
			action = ModeModifier(self.generate_modifiers(self._action))
			self.close()
			self.ac_callback(self.id, action, reopen=True)
	
	
	def on_btMacro_clicked(self, *a):
		""" Asks main window to close this one and display macro editor """
		if self.ac_callback is not None:
			# Convert current action into modeshift and send it to main window
			self._set_title()
			action = Macro(self.generate_modifiers(self._action))
			action.name = action.actions[0].name
			action.actions[0].name = None
			self.close()
			self.ac_callback(self.id, action, reopen=True)
	
	
	def on_exMore_activate(self, ex, *a):
		rvMore = self.builder.get_object("rvMore")
		rvMore.set_reveal_child(not ex.get_expanded())
	
	
	def _set_y_field_visible(self, visible):
		if visible:
			self.builder.get_object("rvlXLabel").set_reveal_child(True)
			self.builder.get_object("rvlYaction").set_reveal_child(True)
		else:
			self.builder.get_object("rvlXLabel").set_reveal_child(False)
			self.builder.get_object("rvlYaction").set_reveal_child(False)
			self.builder.get_object("entActionY").set_text("")
	
	
	def update_modifiers(self, *a):
		"""
		Called when sensitivity or 'require click' combobox value changes.
		"""
		if self._recursing : return
		cbRequireClick = self.builder.get_object("cbRequireClick")
		
		set_action = False
		for i in xrange(0, len(self.sens)):
			if self.sens[i] != self.sens_widgets[i][0].get_value():
				self.sens[i] = self.sens_widgets[i][0].get_value()
				set_action = True
				
		if self.click is not None:
			if cbRequireClick.get_active() != self.click:
				self.click = cbRequireClick.get_active()
				set_action = True
		
		if set_action:
			self.set_action(self._action)
	
	
	def generate_modifiers(self, action, index=-1):
		# Strip 1.0's from sensitivity values
		sens = [] + self.sens
		while len(sens) > 0 and sens[-1] == 1.0: sens = sens[0:-1]
		
		if isinstance(action, XYAction):
			# XYAction has to be topmost
			return XYAction(
				self.generate_modifiers(action.x, 0),
				self.generate_modifiers(action.y, 1),
			)
		if len(sens) > 0 and index < 0:
			# Not called for XYAction parameter
			sens.append(action)
			action = SensitivityModifier(*sens)
		elif len(sens) > index:
			# Called for XYAction parameter and sensitivity is specified
			action = SensitivityModifier(sens[index], action)
		
		if self.click:
			action = ClickModifier(action)
		return action
	
	
	def load_modifiers(self, action, index=-1):
		"""
		Parses action for modifiers and updates UI accordingly.
		Returns action without parsed modifiers.
		"""
		cbRequireClick = self.builder.get_object("cbRequireClick")
		
		while isinstance(action, (ClickModifier, SensitivityModifier)):
			if isinstance(action, ClickModifier):
				self.click = True
				action = action.action
			if isinstance(action, SensitivityModifier):
				for i in xrange(0, len(self.sens)):
					self.sens[i] = action.speeds[i]
				action = action.action
		
		self._recursing = True
		cbRequireClick.set_active(self.click)
		for i in xrange(0, len(self.sens)):
			self.sens_widgets[i][0].set_value(self.sens[i])
		self._recursing = False
		
		return action
	
	
	def set_action(self, action):
		"""
		Updates Action field(s) on bottom and recolors apropriate image area,
		if such area exists.
		"""
		entAction = self.builder.get_object("entAction")
		entActionY = self.builder.get_object("entActionY")
		btOK = self.builder.get_object("btOK")
		
		# Load modifiers and update UI if needed
		action = self.load_modifiers(action)
		
		# Check for InvalidAction and display error message if found
		if isinstance(action, InvalidAction):
			btOK.set_sensitive(False)
			entAction.set_name("error")
			entAction.set_text(str(action.error))
			self._set_y_field_visible(False)
		else:
			# Treat XYAction specialy
			entAction.set_name("entAction")
			btOK.set_sensitive(True)
			self._action = action
			action = self.generate_modifiers(action)
		
			if isinstance(action, XYAction):
				entAction.set_text(action.actions[0].to_string())
				if len(action.actions) < 2:
					entActionY.set_text("")
				else:
					entActionY.set_text(action.actions[1].to_string())
				self._set_y_field_visible(True)
			else:
				if hasattr(action, 'string') and "\n" not in action.string:
					# Stuff generated by my special parser
					entAction.set_text(action.string)
				else:
					# Actions generated elsewhere
					entAction.set_text(action.to_string())
				self._set_y_field_visible(False)
		
		# Send changed action into selected component
		if self._selected_component is None:
			self._selected_component = None
			for component in reversed(sorted(self.components, key = lambda a : a.PRIORITY)):
				if component.CTXS == Action.AC_ALL or self._mode in component.CTXS:
					if component.handles(self._mode, action.strip()):
						self._selected_component = component
						break
			if self._selected_component:
				self.c_buttons[self._selected_component].set_active(True)
				if isinstance(action, InvalidAction):
					self._selected_component.set_action(self._mode, action)
		elif not self._selected_component.handles(self._mode, action.strip()):
			log.warning("selected_component no longer handles edited action")
			log.warning(self._selected_component)
			log.warning(action.to_string())
	
	
	def _set_mode(self, action, mode):
		""" Common part of editor setup """
		self._mode = mode
		# Clear pages and 'action type' buttons
		entName = self.builder.get_object("entName")		
		vbActionButtons = self.builder.get_object("vbActionButtons")
		stActionModes = self.builder.get_object("stActionModes")
		stActionModes = self.builder.get_object("stActionModes")
		
		# Go throgh list of components and display buttons that are usable
		# with this mode
		self.c_buttons = {}
		for component in reversed(sorted(self.components, key = lambda a : a.PRIORITY)):
			if component.CTXS == Action.AC_ALL or mode in component.CTXS:
				b = Gtk.ToggleButton.new_with_label(component.get_button_title())
				vbActionButtons.pack_start(b, True, True, 2)
				b.connect('toggled', self.on_action_type_changed)
				self.c_buttons[component] = b
				
				component.load()
				if component.get_widget() not in stActionModes.get_children():
					stActionModes.add(component.get_widget())
				
		if action.name is None:
			entName.set_text("")
		else:
			entName.set_text(action.name)
		vbActionButtons.show_all()	
	
	
	def set_button(self, button, action):
		""" Setups action editor as editor for button action """
		self._set_mode(action, Action.AC_BUTTON)
		self.hide_advanced_settings()
		self.set_action(action)
		self.id = button

	
	def set_trigger(self, trigger, action):
		""" Setups action editor as editor for trigger action """
		self._set_mode(action, Action.AC_TRIGGER)
		self.hide_sensitivity(1, 2) # YZ
		self.hide_require_click()
		self.set_action(action)
		self.hide_macro()
		self.id = trigger
	
	
	def set_stick(self, action):
		""" Setups action editor as editor for stick action """
		self._set_mode(action, Action.AC_STICK)
		self.hide_sensitivity(2) # Z only
		self.hide_require_click()
		self.set_action(action)
		self.hide_macro()
		self.id = Profile.STICK
	
	
	def set_gyro(self, action):
		""" Setups action editor as editor for stick action """
		self._set_mode(action, Action.AC_GYRO)
		self.set_action(action)
		self.hide_require_click()
		self.hide_macro()
		self.hide_modeshift()
		self.id = Profile.GYRO
	
	
	def set_pad(self, id, action):
		""" Setups action editor as editor for pad action """
		self._set_mode(action, Action.AC_PAD)
		self.hide_sensitivity(2) # Z only
		self.set_action(action)
		self.hide_macro()
		self.id = id
	
	
	def hide_modeshift(self):
		"""
		Hides Mode Shift button.
		Used when displaying ActionEditor from ModeshiftEditor
		"""
		self.builder.get_object("btModeshift").set_visible(False)
	
	
	def hide_macro(self):
		"""
		Hides Macro button.
		Used when displaying ActionEditor from MacroEditor
		"""
		self.builder.get_object("btMacro").set_visible(False)
	
	
	def hide_name(self):
		"""
		Hides (and clears) name field.
		Used when displaying ActionEditor from MacroEditor
		"""
		self.builder.get_object("lblName").set_visible(False)
		self.builder.get_object("entName").set_visible(False)
		self.builder.get_object("entName").set_text("")
