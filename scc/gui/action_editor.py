#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Also doubles as Menu Item Editor in some cases
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.modifiers import Modifier, ClickModifier, ModeModifier
from scc.modifiers import SensitivityModifier, FeedbackModifier
from scc.modifiers import DeadzoneModifier
from scc.actions import Action, XYAction, NoAction
from scc.constants import HapticPos, SCButtons
from scc.special_actions import OSDAction
from scc.controller import HapticData
from scc.profile import Profile
from scc.macros import Macro
from scc.gui.controller_widget import PRESSABLE, TRIGGERS, PADS
from scc.gui.controller_widget import STICKS, GYROS, BUTTONS
from scc.gui.modeshift_editor import ModeshiftEditor
from scc.gui.macro_editor import MacroEditor
from scc.gui.parser import InvalidAction
from scc.gui.dwsnc import headerbar
from scc.gui.ae import AEComponent
from scc.gui.editor import Editor
import os, logging, importlib, types
log = logging.getLogger("ActionEditor")


COMPONENTS = (								# List of known modules (components) in scc.gui.ae package
	'axis',
	'axis_action',
	'gyro',
	'gyro_action',
	'buttons',
	'dpad',
	'per_axis',
	'trigger_ab',
	'special_action',
	'custom',
	# OSK-only components
	'osk_action',
	'osk_buttons',
)
XYZ = "XYZ"									# Sensitivity settings keys
AFP = ("Amplitude", "Frequency", "Period")	# Feedback settings keys
DZN = ("Lower", "Upper")					# Deadzone settings key
FEEDBACK_SIDES = [ HapticPos.LEFT, HapticPos.RIGHT, HapticPos.BOTH ]


class ActionEditor(Editor):
	GLADE = "action_editor.glade"
	ERROR_CSS = " #error {background-color:green; color:red;} "
	
	AEC_MENUITEM = -1

	def __init__(self, app, callback):
		self.app = app
		self.id = None
		self.components = []			# List of available components
		self.loaded_components = {}		# by class name
		self.c_buttons = {} 			# Component-to-button dict
		self.sens_widgets = []			# Sensitivity sliders, labels and 'clear' buttons
		self.feedback_widgets = []		# Feedback settings sliders, labels and 'clear' buttons, plus default value as last item
		self.deadzone_widgets = []		# Deadzone settings sliders and 'clear' buttons, plus default value as last item
		self.sens = [1.0] * 3			# Sensitivity slider values
		self.feedback = [0.0] * 3		# Feedback slider values, set later
		self.deadzone = [0] * 2			# Deadzone slider values, set later
		self.deadzone_enabled = False
		self.feedback_position = None	# None for 'disabled'
		self.click = False				# Click modifier value. None for disabled
		self.osd = False				# 'OSD enabled' value.
		self.setup_widgets()
		self.load_components()
		self.ac_callback = callback	# This is different callback than ButtonChooser uses
		Editor.install_error_css()
		self._action = NoAction()
		self._selected_component = None
		self._modifiers_enabled = True
		self._multiparams = [ None ] * 8
		self._mode = None
		self._recursing = False
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		headerbar(self.builder.get_object("header"))
		for i in (0, 1, 2):
			self.sens_widgets.append((
				self.builder.get_object("sclSens%s" % (XYZ[i],)),
				self.builder.get_object("lblSens%s" % (XYZ[i],)),
				self.builder.get_object("btClearSens%s" % (XYZ[i],)),
			))
		for key in AFP:
			i = AFP.index(key)
			self.feedback[i] = self.builder.get_object("sclF%s" % (key,)).get_value()
			self.feedback_widgets.append((
				self.builder.get_object("sclF%s" % (key,)),
				self.builder.get_object("lblF%s" % (key,)),
				self.builder.get_object("btClearF%s" % (key,)),
				self.feedback[i]	# default value
			))
		for key in DZN:
			i = DZN.index(key)
			self.deadzone[i] = self.builder.get_object("sclDZ%s" % (key,)).get_value()
			self.deadzone_widgets.append((
				self.builder.get_object("sclDZ%s" % (key,)),
				self.builder.get_object("btClearDZ%s" % (key,)),
				self.deadzone[i]	# default value
			))
	
	
	def load_components(self):
		""" Loads list of editor components """
		# Import and load components
		for c in COMPONENTS:
			self.load_component(c)
		self._selected_component = None
	
	
	def load_component(self, class_name):
		"""
		Loads and adds new component to editor.
		Returns component instance.
		"""
		if class_name in self.loaded_components:
			return self.loaded_components[class_name]
		mod = importlib.import_module("scc.gui.ae.%s" % (class_name,))
		for x in mod.__all__:
			cls = getattr(mod, x)
			if isinstance(cls, (type, types.ClassType)) and issubclass(cls, AEComponent):
				if cls is not AEComponent:
					instance = cls(self.app, self)
					self.loaded_components[class_name] = instance
					self.components.append(instance)
					return instance
	
	
	def on_Dialog_destroy(self, *a):
		if self._selected_component is not None:
			self._selected_component.hidden()
	
	
	def close(self):
		self.on_Dialog_destroy()
		Editor.close(self)
	
	
	def get_id(self):
		""" Returns ID of input that is being edited """
		return self.id
	
	
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
		if self._selected_component is not None:
			if self._selected_component != component:
				self._selected_component.hidden()
		self._selected_component = component
		self._selected_component.shown()
		stActionModes.set_visible_child(component.get_widget())
		
		stActionModes.show_all()
	
	
	def force_page(self, component, remove_rest=False):
		"""
		Forces action editor to display page with specified component.
		If 'remove_rest' is True, removes all other pages.
		
		Returns 'component'
		"""
		stActionModes = self.builder.get_object("stActionModes")
		component.load()
		for c in stActionModes.get_children():
			if c != component:
				stActionModes.remove(c)
		
		if component.get_widget() not in stActionModes.get_children():
			stActionModes.add(component.get_widget())
		
		component.set_action(self._mode, self._action)
		if self._selected_component is not None:
			if self._selected_component != component:
				self._selected_component.hidden()
		self._selected_component = component
		self._selected_component.shown()
		stActionModes.set_visible_child(component.get_widget())
		stActionModes.show_all()
		
		return component
	
	
	def get_name(self):
		""" Returns action name as set in editor entry """
		entName = self.builder.get_object("entName")
		return entName.get_text().strip(" \t")
	
	
	def get_current_page(self):
		""" Returns currently displayed page (component) """
		return self._selected_component
	
	
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
	
	
	def hide_modifiers(self):
		""" Hides (and disables) all modifiers """
		self.set_modifiers_enabled(False)
		self.builder.get_object("exMore").set_visible(False)
	
	
	def hide_require_click(self):
		"""
		Hides 'Require Click' checkbox.
		Used when editing everything but pad.
		"""
		self.builder.get_object("cbRequireClick").set_visible(False)
	
	
	def hide_enable_feedback(self):
		"""
		Hides 'Enable Feedback' checkbox.
		Used when editing buttons.
		"""
		self.builder.get_object("cbFeedback").set_visible(False)
	
	
	def hide_osd(self):
		"""
		Hides 'Display OSD' checkbox.
		Used randomly.
		"""
		self.builder.get_object("cbOSD").set_visible(False)
	
	
	def hide_hide_enable_deadzones(self):
		"""
		Hides 'Enable Deadzone' checkbox.
		Used when editing buttons.
		"""
		self.builder.get_object("cbDeadzone").set_visible(False)
	
	
	def hide_advanced_settings(self):
		"""
		Hides entire 'Advanced Settings' expander.
		"""
		self.hide_sensitivity()
		self.hide_require_click()
		self.builder.get_object("exMore").set_visible(False)
		self.builder.get_object("rvMore").set_visible(False)
	
	
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
	
	
	def hide_action_buttons(self):
		""" Hides action buttons, effectivelly disallowing user to change action type """
		for x in ("lblActionType", "vbActionButtons"):
			self.builder.get_object(x).set_visible(False)
		self.hide_modeshift()
		self.hide_macro()
	
	
	def hide_action_str(self):
		""" Hides bottom part with action displayed as string """
		self.builder.get_object("vbActionStr").set_visible(False)
		self.builder.get_object("grEditor").set_property("margin-bottom", 30)
		
	
	
	def hide_editor(self):
		""" Hides everything but action buttons and action name field """
		self.builder.get_object("stActionModes").set_visible(False)
		self.hide_action_str()
		self.hide_modeshift()
		self.hide_macro()
	
	
	def hide_name(self):
		"""
		Hides (and clears) name field.
		Used when displaying ActionEditor from MacroEditor
		"""
		self.builder.get_object("lblName").set_visible(False)
		self.builder.get_object("entName").set_visible(False)
		self.builder.get_object("entName").set_text("")
	
	
	def hide_clear(self):
		""" Hides clear buttton """
		self.builder.get_object("btClear").set_visible(False)
	
	
	def on_btClearSens_clicked(self, source, *a):
		for scale, label, button in self.sens_widgets:
			if source == button:
				scale.set_value(1.0)
	
	
	def on_btClearFeedback_clicked(self, source, *a):
		for scale, label, button, default in self.feedback_widgets:
			if source == button:
				scale.set_value(default)
	
	
	def on_btClearDeadzone_clicked(self, source, *a):
		for scale, button, default in self.deadzone_widgets:
			if source == button:
				scale.set_value(default)
	
	
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
			if self._mode == ActionEditor.AEC_MENUITEM:
				self.ac_callback(self.id, self)
			else:
				a = self.generate_modifiers(self._action, self._selected_component.NAME=="custom")
				self.ac_callback(self.id, a)
			if self._selected_component:
				self._selected_component.on_ok(a)
		self.close()
	
	
	def on_btModeshift_clicked(self, *a):
		""" Convert current action into modeshift and send it to ModeshiftEditor """
		e = ModeshiftEditor(self.app, self.ac_callback)
		action = ModeModifier(self.generate_modifiers(self._action, self._selected_component.NAME=="custom"))
		e.set_input(self.id, action, mode=self._mode)
		self.close()
		e.show(self.get_transient_for())
	
	
	def on_btMacro_clicked(self, *a):
		""" Convert current action into macro and send it to MacroEditor """
		e = MacroEditor(self.app, self.ac_callback)
		action = Macro(self.generate_modifiers(self._action, self._selected_component.NAME=="custom"))
		e.set_input(self.id, action, mode=self._mode)
		self.close()
		e.show(self.get_transient_for())
	
	
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
		Called when sensitivity, feedback or 'require click' setting changes.
		"""
		if self._recursing : return
		cbRequireClick = self.builder.get_object("cbRequireClick")
		cbFeedbackSide = self.builder.get_object("cbFeedbackSide")
		cbFeedback = self.builder.get_object("cbFeedback")
		rvFeedback = self.builder.get_object("rvFeedback")
		cbDeadzone = self.builder.get_object("cbDeadzone")
		rvDeadzone = self.builder.get_object("rvDeadzone")
		cbOSD = self.builder.get_object("cbOSD")
		
		set_action = False
		for i in xrange(0, len(self.sens)):
			if self.sens[i] != self.sens_widgets[i][0].get_value():
				self.sens[i] = self.sens_widgets[i][0].get_value()
				set_action = True
		
		for i in xrange(0, len(self.feedback)):
			if self.feedback[i] != self.feedback_widgets[i][0].get_value():
				self.feedback[i] = self.feedback_widgets[i][0].get_value()
				set_action = True
		
		for i in xrange(0, len(self.deadzone)):
			if self.deadzone[i] != self.deadzone_widgets[i][0].get_value():
				self.deadzone[i] = self.deadzone_widgets[i][0].get_value()
				set_action = True
		
		if self.deadzone_enabled != cbDeadzone.get_active():
			self.deadzone_enabled = cbDeadzone.get_active()
			set_action = True
		
		if cbFeedback.get_active():
			feedback_position = FEEDBACK_SIDES[cbFeedbackSide.get_active()]
		else:
			feedback_position = None
		if self.feedback_position != feedback_position:
			self.feedback_position = feedback_position
			set_action = True
		
		if self.click is not None:
			if cbRequireClick.get_active() != self.click:
				self.click = cbRequireClick.get_active()
				set_action = True
		
		if self.osd is not None:
			if cbOSD.get_active() != self.osd:
				self.osd = cbOSD.get_active()
				set_action = True
		
		rvFeedback.set_reveal_child(cbFeedback.get_active() and cbFeedback.get_sensitive())
		rvDeadzone.set_reveal_child(cbDeadzone.get_active() and cbDeadzone.get_sensitive())
		
		if set_action:
			self.set_action(self._action)
	
	
	def generate_modifiers(self, action, from_custom=False):
		if not self._modifiers_enabled and not from_custom:
			# Editing in custom aciton dialog, don't meddle with that
			return action
		
		# Strip 1.0's from sensitivity values
		sens = [] + self.sens
		while len(sens) > 0 and sens[-1] == 1.0:
			sens = sens[0:-1]
		
		# Strip defaults from feedback values
		feedback = [] + self.feedback
		while len(feedback) > 0 and feedback[-1] == self.feedback_widgets[len(feedback)-1][-1]:
			feedback = feedback[0:-1]
		
		if len(sens) > 0:
			# Build arguments
			sens.append(action)
			# Create modifier
			action = SensitivityModifier(*sens)
		
		if self.feedback_position != None:
			cbFeedbackSide = self.builder.get_object("cbFeedbackSide")
			cbFeedback = self.builder.get_object("cbFeedback")
			if from_custom or (cbFeedback.get_active() and cbFeedback.get_sensitive()):
				# Build FeedbackModifier arguments
				feedback = [ FEEDBACK_SIDES[cbFeedbackSide.get_active()] ] + feedback
				feedback += [ action ]
				# Create modifier
				action = FeedbackModifier(*feedback)
		
		if self.deadzone_enabled:
			action = DeadzoneModifier(self.deadzone[0], self.deadzone[1], action)
		
		if self.click:
			action = ClickModifier(action)
		
		if self.osd:
			action = OSDAction(action)
		
		return action
	
	@staticmethod
	def is_modifier(a):
		if isinstance(a, (ClickModifier, SensitivityModifier, DeadzoneModifier,
				FeedbackModifier)):
			return True
		if isinstance(a, OSDAction):
			if a.action is not None:
				return True
		return False
	
	
	def load_modifiers(self, action, index=-1):
		"""
		Parses action for modifiers and updates UI accordingly.
		Returns action without parsed modifiers.
		"""
		cbRequireClick = self.builder.get_object("cbRequireClick")
		cbFeedback = self.builder.get_object("cbFeedback")
		rvFeedback = self.builder.get_object("rvFeedback")
		cbFeedbackSide = self.builder.get_object("cbFeedbackSide")
		cbDeadzone = self.builder.get_object("cbDeadzone")
		rvDeadzone = self.builder.get_object("rvDeadzone")
		cbOSD = self.builder.get_object("cbOSD")
		
		while ActionEditor.is_modifier(action):
			if isinstance(action, OSDAction):
				self.osd = True
				action = action.action
			if isinstance(action, ClickModifier):
				self.click = True
				action = action.action
			if isinstance(action, FeedbackModifier):
				self.feedback_position = action.haptic.get_position()
				self.feedback[0] = action.haptic.get_amplitude()
				self.feedback[1] = action.haptic.get_frequency()
				self.feedback[2] = action.haptic.get_period()
				action = action.action
			if isinstance(action, DeadzoneModifier):
				self.deadzone_enabled = True
				self.deadzone[0] = action.lower
				self.deadzone[1] = action.upper
				action = action.action
			if isinstance(action, SensitivityModifier):
				if index < 0:
					for i in xrange(0, len(self.sens)):
						self.sens[i] = action.speeds[i]
				else:
					self.sens[index] = action.speeds[0]
				action = action.action
		
		self._recursing = True
		cbRequireClick.set_active(self.click)
		cbOSD.set_active(self.osd)
		for i in xrange(0, len(self.sens)):
			self.sens_widgets[i][0].set_value(self.sens[i])
		if self.feedback_position != None:
			cbFeedbackSide.set_active(FEEDBACK_SIDES.index(self.feedback_position))
			cbFeedback.set_active(True)
			rvFeedback.set_reveal_child(cbFeedback.get_sensitive())
			for i in xrange(0, len(self.feedback)):
				self.feedback_widgets[i][0].set_value(self.feedback[i])
		if self.deadzone_enabled:
			cbDeadzone.set_active(True)
			rvDeadzone.set_reveal_child(cbDeadzone.get_sensitive())
			for i in xrange(0, len(self.deadzone)):
				self.deadzone_widgets[i][0].set_value(self.deadzone[i])
		self._recursing = False
		
		return action
	
	
	def set_action(self, action, from_custom=False):
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
			# Check for XYAction and treat it specialy
			entAction.set_name("entAction")
			btOK.set_sensitive(True)
			self._action = action
			if isinstance(action, XYAction):
				entAction.set_text(self.generate_modifiers(action.x, from_custom).to_string())
				if not action.y:
					entActionY.set_text("")
				else:
					entActionY.set_text(self.generate_modifiers(action.y, from_custom).to_string())
				self._set_y_field_visible(True)
				action = self.generate_modifiers(action, from_custom)
			else:
				action = self.generate_modifiers(action, from_custom)
				
				if hasattr(action, 'string') and "\n" not in action.string:
					# Stuff generated by my special parser
					entAction.set_text(action.string)
				else:
					# Actions generated elsewhere
					entAction.set_text(action.to_string())
				self._set_y_field_visible(False)
			# Check if action supports feedback
			if action.set_haptic(HapticData(HapticPos.LEFT)):
				self.set_feedback_settings_enabled(True)
			else:
				self.set_feedback_settings_enabled(False)
		
		# Send changed action into selected component
		if self._selected_component is None:
			self._selected_component = None
			for component in reversed(sorted(self.components, key = lambda a : a.PRIORITY)):
				if (component.CTXS & self._mode) != 0:
					if component.handles(self._mode, action.strip()):
						self._selected_component = component
						break
			if isinstance(action, InvalidAction):
				c = self.load_component("custom")
				if c in self.components and (self._mode & c.CTXS) != 0:
					self._selected_component = c
			if self._selected_component:
				if self._selected_component in self.c_buttons:
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
			if (mode & component.CTXS) != 0:
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
		if vbActionButtons.get_visible():
			vbActionButtons.show_all()
	
	
	def set_input(self, id, action, mode=None):
		"""
		Setups action editor for editing specified input.
		Mode (buttton/axis/trigger...) is either provided or chosen based on id.
		Also sets title, but that can be overriden by calling set_title after.
		"""
		self.id = id
		if id in SCButtons or mode in (Action.AC_MENU, Action.AC_BUTTON):
			if id in PRESSABLE:
				self.set_title(_("%s Press") % (id.name,))
			elif id in SCButtons:
				self.set_title(id.name,)
			self._set_mode(action, mode or Action.AC_BUTTON)
			self.hide_sensitivity(0, 1, 2)
			self.hide_enable_feedback()
			self.hide_hide_enable_deadzones()
			self.hide_require_click()
			self.set_action(action)
		elif id in TRIGGERS:
			self.set_title(_("%s Trigger") % (id,))
			self._set_mode(action, mode or Action.AC_TRIGGER)
			self.hide_sensitivity(1, 2) # YZ
			self.hide_require_click()
			self.hide_hide_enable_deadzones()
			self.hide_osd()
			self.set_action(action)
			self.hide_macro()
		elif id in STICKS:
			self.set_title(_("Stick"))
			self._set_mode(action, mode or Action.AC_STICK)
			self.hide_sensitivity(2) # Z only
			self.hide_require_click()
			self.hide_osd()
			self.set_action(action)
			self.hide_macro()
			self.id = Profile.STICK
		elif id in GYROS:
			self.set_title(_("Gyro"))
			self._set_mode(action, mode or Action.AC_GYRO)
			self.set_action(action)
			self.hide_require_click()
			self.hide_hide_enable_deadzones()
			self.hide_osd()
			self.hide_macro()
			self.hide_modeshift()
			self.id = Profile.GYRO
		elif id in PADS:
			self._set_mode(action, mode or Action.AC_PAD)
			self.hide_sensitivity(2) # Z only
			self.set_action(action)
			self.hide_osd()
			self.hide_macro()
			if id == "LPAD":
				self.set_title(_("Left Pad"))
			else:
				self.set_title(_("Right Pad"))
		if mode == Action.AC_OSK:
			self.hide_osd()
			self.hide_name()
			self.hide_macro()
			self.hide_modeshift()
		elif mode == Action.AC_MENU:
			self.hide_modeshift()
			self.hide_macro()
	
	
	def set_menu_item(self, item, title_for_name_label=None):
		"""
		Setups action editor in way that allows editing only action name.
		
		In this mode, callback is called with editor instance instead of
		generated action as 2nd argument.
		"""
		entName = self.builder.get_object("entName")
		self._mode = ActionEditor.AEC_MENUITEM
		if hasattr(item, "label") and item.label:
			entName.set_text(item.label)
		else:
			entName.set_text("")
		self.hide_osd()
		self.hide_action_buttons()
		self.hide_modifiers()
		self.set_action(NoAction())
		self.id = item.id
		if title_for_name_label:
			self.builder.get_object("lblName").set_label(title_for_name_label)
	
	
	def set_feedback_settings_enabled(self, enabled):
		cbFeedback = self.builder.get_object("cbFeedback")
		rvFeedback = self.builder.get_object("rvFeedback")
		cbFeedback.set_sensitive(enabled)
		if enabled:
			rvFeedback.set_reveal_child(cbFeedback.get_active() and cbFeedback.get_sensitive())
		else:
			rvFeedback.set_reveal_child(False)
	
	
	def set_modifiers_enabled(self, enabled):
		exMore = self.builder.get_object("exMore")
		rvMore = self.builder.get_object("rvMore")
		if self._modifiers_enabled != enabled and not enabled:
			exMore.set_expanded(False)
			rvMore.set_reveal_child(False)
		exMore.set_sensitive(enabled)
		self._modifiers_enabled = enabled
