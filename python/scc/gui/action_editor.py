#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Also doubles as Menu Item Editor in some cases
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, RingAction, TriggerAction
from scc.actions import OSDAction, Macro
from scc.actions import SmoothModifier, NameModifier, BallModifier
from scc.actions import Modifier, ClickedModifier, ModeModifier
from scc.actions import SensitivityModifier, FeedbackModifier
from scc.actions import DeadzoneModifier, RotateInputModifier
from scc.actions import HapticData
from scc.constants import HapticPos, SCButtons
from scc.constants import CUT, ROUND, LINEAR, MINIMUM
from scc.profile import Profile
from scc.tools import nameof
from scc.gui.controller_widget import PRESSABLE, TRIGGERS, PADS
from scc.gui.controller_widget import STICKS, GYROS, BUTTONS
from scc.gui.modeshift_editor import ModeshiftEditor
from scc.gui.parser import InvalidAction, GuiActionParser
from scc.gui.simple_chooser import SimpleChooser
from scc.gui.macro_editor import MacroEditor
from scc.gui.ring_editor import RingEditor
from scc.gui.dwsnc import headerbar
from scc.gui.ae import AEComponent
from scc.gui.editor import Editor
import os, logging, math, importlib, types
log = logging.getLogger("ActionEditor")


COMPONENTS = (								# List of known modules (components) in scc.gui.ae package
	'axis',
	'axis_action',
	'buttons',
	'custom',
	'dpad',
	'gesture',
	'gyro',
	'gyro_action',
	'per_axis',
	'special_action',
	'tilt',
	'trigger',
	# OSK-only components
	'osk_action',
	'osk_buttons',
)
XYZ = "XYZ"									# Sensitivity settings keys
AFP = ("Amplitude", "Frequency", "Period")	# Feedback settings keys
SMT = ("Level", "Weight", "Filter")			# Smoothing setting keys
DZN = ("Lower", "Upper")					# Deadzone settings key
FEEDBACK_SIDES = [ HapticPos.LEFT, HapticPos.RIGHT, HapticPos.BOTH ]
DEADZONE_MODES = [ CUT, ROUND, LINEAR, MINIMUM ]


class ActionEditor(Editor):
	GLADE = "action_editor.glade"
	ERROR_CSS = " #error {background-color:green; color:red;} "
	
	AEC_MENUITEM = -1
	
	MODE_TO_MODS = {
		# Specified which modifiers are compatibile with which editor mode.
		# That way, stuff like Rotation settings is not shown when editor
		# is used to edit menu actions.
		Action.AC_BUTTON	: Action.AF_MOD_OSD | Action.AF_MOD_FEEDBACK,
		Action.AC_TRIGGER	: Action.AF_MOD_OSD | Action.AF_MOD_SENSITIVITY | Action.AF_MOD_FEEDBACK,
		Action.AC_STICK		: Action.AF_MOD_OSD | Action.AF_MOD_CLICK | Action.AF_MOD_DEADZONE | Action.AF_MOD_ROTATE | Action.AF_MOD_SENSITIVITY | Action.AF_MOD_FEEDBACK | Action.AF_MOD_SMOOTH,
		Action.AC_PAD		: Action.AF_MOD_OSD | Action.AF_MOD_CLICK | Action.AF_MOD_DEADZONE | Action.AF_MOD_ROTATE | Action.AF_MOD_SENSITIVITY | Action.AF_MOD_FEEDBACK | Action.AF_MOD_SMOOTH | Action.AF_MOD_BALL,
		Action.AC_GYRO		: Action.AF_MOD_OSD | Action.AF_MOD_SENSITIVITY | Action.AF_MOD_SENS_Z | Action.AF_MOD_DEADZONE | Action.AF_MOD_FEEDBACK,
		Action.AC_OSK		: 0,
		Action.AC_MENU		: Action.AF_MOD_OSD,
		AEC_MENUITEM		: 0,
	}
	
	
	def __init__(self, app, callback):
		Editor.__init__(self)
		self.app = app
		self.id = None
		self.components = []			# List of available components
		self.loaded_components = {}		# by class name
		self.c_buttons = {} 			# Component-to-button dict
		self.sens_widgets = []			# Sensitivity sliders, labels and 'clear' buttons
		self.feedback_widgets = []		# Feedback settings sliders, labels and 'clear' buttons, plus default value as last item
		self.smoothing_widgets = []		# Smoothing settings sliders, labels and 'clear' buttons, plus default value as last item
		self.deadzone_widgets = []		# Deadzone settings sliders, labels and 'clear' buttons, plus default value as last item
		self.sens = [1.0] * 3			# Sensitivity slider values
		self.sens_defaults = [1.0] * 3	# Clear button clears to this
		self.feedback = [0.0] * 3		# Feedback slider values, set later
		self.deadzone = [0] * 2			# Deadzone slider values, set later
		self.deadzone_mode = None		# None for 'disabled'
		self.feedback_position = None	# None for 'disabled'
		self.smoothing = None			# None for 'disabled'
		self.friction = -1				# -1 for 'disabled'
		self.click = False				# Click modifier value. None for disabled
		self.rotation_angle = 0			# RotateInputModifier angle
		self.osd = False				# 'OSD enabled' value.
		self.first_page_allowed = False
		self.setup_widgets()
		self.load_components()
		self.ac_callback = callback		# This is different callback than ButtonChooser uses
		Editor.install_error_css()
		self._action = NoAction()
		self._replaced_action = None
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
				self.builder.get_object("cbSensInvert%s" % (XYZ[i],)),
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
		for key in SMT:
			i = SMT.index(key)
			self.smoothing_widgets.append((
				self.builder.get_object("lblSmooth%s" % (key,)),
				self.builder.get_object("sclSmooth%s" % (key,)),
				self.builder.get_object("btClearSmooth%s" % (key,)),
				self.builder.get_object("sclSmooth%s" % (key,)).get_value()
			))
		for key in DZN:
			i = DZN.index(key)
			self.deadzone[i] = self.builder.get_object("sclDZ%s" % (key,)).get_value()
			self.deadzone_widgets.append((
				self.builder.get_object("lblDZ%s" % (key,)),
				self.builder.get_object("sclDZ%s" % (key,)),
				self.builder.get_object("btClearDZ%s" % (key,)),
				self.deadzone[i]	# default value
			))
		
		if self.app.osd_mode:
			self.builder.get_object("entName").set_sensitive(False)
	
	
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
		cbPreview = self.builder.get_object("cbPreview")
		cbPreview.set_active(False)
		self.remove_added_widget()
		if self._selected_component is not None:
			self._selected_component.hidden()
	
	
	def on_Dialog_key_press_event(self, window, event):
		if self.app.osd_mode and event.keyval == 65471:
			self.on_btOK_clicked()
	
	
	def set_osd_enabled(self, value):
		"""
		Sets value of OSD modifier checkbox, without firing any more events.
		"""
		self._recursing = True
		self.osd = value
		self.builder.get_object("cbOSD").set_active(value)
		self._recursing = False
	
	
	def show(self, transient_for):
		Editor.show(self, transient_for)
	
	
	def close(self):
		self.on_Dialog_destroy()
		Editor.close(self)
	
	
	def get_id(self):
		""" Returns ID of input that is being edited """
		return self.id
	
	
	def on_link(self, link):
		parser = GuiActionParser()
		if link.startswith("quick://"):
			action = parser.restart(link[8:]).parse()
			self.reset_active_component()
			self.set_action(action, from_custom=True)
		elif link == "grab://trigger_button":
			def cb(action):
				action = TriggerAction(254, 255, action)
				self.set_action(action, from_custom=True)
				self.force_page("trigger")
			b = SimpleChooser(self.app, "buttons", cb)
			b.set_title(_("Select Button"))
			b.hide_axes()
			b.show(self.window)
		elif link.startswith("page://"):
			def cb():
				self.force_page(link[7:])
			GLib.timeout_add(0.1, cb)
		elif link.startswith("advanced://"):
			exMore = self.builder.get_object("exMore")
			rvMore = self.builder.get_object("rvMore")
			ntbMore = self.builder.get_object("ntbMore")
			assert exMore.get_visible()
			exMore.set_expanded(True)
			rvMore.set_reveal_child(True)
			if "#" in link:
				link, name = link.split("#")
				self.blink_widget(name)
			ntbMore.set_current_page(int(link.split("/")[-1]))
		else:
			log.warning("Activated unknown link: %s", link)
	
	def on_action_type_changed(self, clicked_button):
		"""
		Called when user clicks on one of Action Type buttons.
		"""
		# Prevent recurson
		if self._recursing : return
		self._recursing = True
		# Don't allow user to deactivate buttons - I'm using them as
		# radio button and you can't 'uncheck' radiobutton by clicking on it
		if not clicked_button.get_active():
			clicked_button.set_active(True)
			self._recursing = False
			return
		
		component = None
		for c in self.c_buttons:
			b = self.c_buttons[c]
			if clicked_button == b:
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
		if type(component) in (unicode, str):
			component = self.load_component(component)
			return self.force_page(component, remove_rest)
		
		stActionModes = self.builder.get_object("stActionModes")
		component.load()
		if remove_rest:
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
		return entName.get_text().decode("utf-8").strip(" \t")
	
	
	def get_current_page(self):
		""" Returns currently displayed page (component) """
		return self._selected_component
	
	
	def blink_widget(self, name, time=500):
		GROUPS = {
			'cbBallMode': ('cbBallMode', 'lblFriction', 'sclFriction', 'btClearFriction')
		}
		
		def blink(widgets, count):
			count = count - 1
			for widget in widgets:
				widget.set_opacity(1.0 if count % 2 == 0 else 0.1)
			if count > 0:
				GLib.timeout_add(time, blink, widgets, count)
		
		if name in GROUPS:
			blink([self.builder.get_object(x) for x in GROUPS[name]], 7)
		else:
			blink([self.builder.get_object(name)], 7)
	
	
	def hide_modifiers(self):
		""" Hides (and disables) all modifiers """
		self.set_modifiers_enabled(False)
		self.builder.get_object("exMore").set_visible(False)
	
	
	def hide_advanced_settings(self):
		"""
		Hides entire 'Advanced Settings' expander.
		"""
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
		Used when editing macro of pad/stick bindings.
		"""
		self.builder.get_object("btMacro").set_visible(False)
	
	
	def hide_ring(self):
		"""
		Hides Ring Bindings button.
		Used when editing anything but pad.
		"""
		self.builder.get_object("btInnerRing").set_visible(False)
	
	
	def hide_action_buttons(self):
		""" Hides action buttons, effectivelly disallowing user to change action type """
		for x in ("lblActionType", "vbActionButtons"):
			self.builder.get_object(x).set_visible(False)
		self.hide_modeshift()
		self.hide_macro()
		self.hide_ring()
	
	
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
		self.hide_ring()
	
	
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
	
	
	def on_btClearRotation_clicked(self, *a):
		self.builder.get_object("sclRotation").set_value(0.0)
	
	
	def on_btClearSens_clicked(self, source, *a):
		i = 0
		for scale, label, button, checkbox in self.sens_widgets:
			if source == button:
				scale.set_value(self.sens_defaults[i])
				i += 1
	
	
	def on_btClearFeedback_clicked(self, source, *a):
		for scale, label, button, default in self.feedback_widgets:
			if source == button:
				scale.set_value(default)
	
	
	def on_btClearSmoothing_clicked(self, source, *a):
		for label, scale, button, default in self.smoothing_widgets:
			if source == button:
				scale.set_value(default)
	
	
	def on_btClearDeadzone_clicked(self, source, *a):
		for label, scale, button, default in self.deadzone_widgets:
			if source == button:
				scale.set_value(default)
	
	
	def on_btClear_clicked(self, *a):
		""" Handler for clear button """
		action = NoAction()
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		if self.ac_callback is not None:
			if self._mode == ActionEditor.AEC_MENUITEM:
				self.ac_callback(self.id, self)
			else:
				entName = self.builder.get_object("entName")
				a = self.generate_modifiers(self._action, self._selected_component.NAME=="custom")
				name = entName.get_text().decode("utf-8").strip(" \t\r\n")
				if name:
					a = NameModifier(name, a or NoAction())
				self.ac_callback(self.id, a)
				self.ac_callback = None
			if self._selected_component:
				self._selected_component.on_ok(a)
		self.close()
	
	
	def on_btModeshift_clicked(self, *a):
		""" Convert current action into modeshift and send it to ModeshiftEditor """
		e = ModeshiftEditor(self.app, self.ac_callback)
		action = ModeModifier(self.generate_modifiers(self._action, self._selected_component.NAME=="custom"))
		e.set_input(self.id, action, mode=self._mode)
		self.send_added_widget(e)
		self.close()
		e.show(self.get_transient_for())
	
	
	def on_btMacro_clicked(self, *a):
		""" Convert current action into macro and send it to MacroEditor """
		e = MacroEditor(self.app, self.ac_callback)
		action = Macro(self.generate_modifiers(self._action, self._selected_component.NAME=="custom"))
		e.set_input(self.id, action, mode=self._mode)
		self.send_added_widget(e)
		self.close()
		e.show(self.get_transient_for())
	
	
	def on_btInnerRing_clicked(self, *a):
		""" Convert current action into ring bindings and send it to RingEditor """
		e = RingEditor(self.app, self.ac_callback)
		action = RingAction(self.generate_modifiers(self._action, self._selected_component.NAME=="custom"))
		e.set_input(self.id, action, mode=self._mode)
		self.send_added_widget(e)
		self.close()
		e.show(self.get_transient_for())
	
	
	def on_exMore_activate(self, ex, *a):
		rvMore = self.builder.get_object("rvMore")
		rvMore.set_reveal_child(not ex.get_expanded())


	def update_modifiers(self, *a):
		"""
		Called when sensitivity, feedback or other modifier setting changes.
		"""
		if self._recursing : return
		cbRequireClick = self.builder.get_object("cbRequireClick")
		cbFeedbackSide = self.builder.get_object("cbFeedbackSide")
		cbFeedback = self.builder.get_object("cbFeedback")
		grFeedback = self.builder.get_object("grFeedback")
		cbDeadzone = self.builder.get_object("cbDeadzone")
		cbDeadzoneMode = self.builder.get_object("cbDeadzoneMode")
		cbSmoothing = self.builder.get_object("cbSmoothing")
		rvSmoothing = self.builder.get_object("rvSmoothing")
		sclRotation = self.builder.get_object("sclRotation")
		sclFriction = self.builder.get_object("sclFriction")
		cbBallMode = self.builder.get_object("cbBallMode")
		cbOSD = self.builder.get_object("cbOSD")
		set_action = False
		
		# Friction
		if not self.builder.get_object("cbBallMode").get_active():
			friction = -1
		elif sclFriction.get_value() == 0:
			friction = 0
		else:
			friction = ((10.0 ** sclFriction.get_value()) / 1000.0)
		if self.friction != friction:
			self.friction = friction
			set_action = True
		
		# Sensitivity
		for i in xrange(0, len(self.sens)):
			target = self.sens_widgets[i][0].get_value()
			if self.sens_widgets[i][3].get_active():
				target = -target
			if self.sens[i] != target:
				self.sens[i] = target
				set_action = True
		
		# Feedback
		if cbFeedback.get_active():
			feedback_position = FEEDBACK_SIDES[cbFeedbackSide.get_active()]
		else:
			feedback_position = None
		if self.feedback_position != feedback_position:
			self.feedback_position = feedback_position
			set_action = True
		
		for i in xrange(0, len(self.feedback)):
			if self.feedback[i] != self.feedback_widgets[i][0].get_value():
				self.feedback[i] = self.feedback_widgets[i][0].get_value()
				set_action = True
		
		for i in xrange(0, len(self.feedback)):
			if self.feedback[i] != self.feedback_widgets[i][0].get_value():
				self.feedback[i] = self.feedback_widgets[i][0].get_value()
				set_action = True
		
		# Deadzone
		mode = (DEADZONE_MODES[cbDeadzoneMode.get_active()]
					if cbDeadzone.get_active() else None)
		if self.deadzone_mode != mode:
			self.deadzone_mode = mode
			set_action = True
		
		for i in xrange(0, len(self.deadzone)):
			if self.deadzone[i] != self.deadzone_widgets[i][1].get_value():
				self.deadzone[i] = self.deadzone_widgets[i][1].get_value()
				set_action = True
		
		
		# Smoothing
		if cbSmoothing.get_active():
			smoothing = (
				int(self.smoothing_widgets[0][1].get_value()),
				self.smoothing_widgets[1][1].get_value(),
				int(self.smoothing_widgets[2][1].get_value()),
			)
		else:
			smoothing = None
		if self.smoothing != smoothing:
			self.smoothing = smoothing
			set_action = True
		
		
		# Rest
		if self.click is not None:
			if cbRequireClick.get_active() != self.click:
				self.click = cbRequireClick.get_active()
				set_action = True
		
		if self.osd is not None:
			if cbOSD.get_active() != self.osd:
				self.osd = cbOSD.get_active()
				set_action = True
		
		if self.rotation_angle != sclRotation.get_value():
			self.rotation_angle = sclRotation.get_value()
			set_action = True
		
		if set_action:
			self.set_action(self._action)
			self._selected_component.modifier_updated()
	
	
	def generate_modifiers(self, action, from_custom=False):
		"""
		Returns Action with all modifiers from UI applied.
		"""
		if not self._modifiers_enabled and not from_custom:
			# Editing in custom aciton dialog, don't meddle with that
			return action
		
		if isinstance(action, ModeModifier):
			args = []
			for k in action.mods:
				if action.mods[k] is not None:
					args += [ k, self.generate_modifiers(ActionEditor.strip_modifiers(action.mods[k])) ]
			if action.default:
				args += [ self.generate_modifiers(ActionEditor.strip_modifiers(action.default)) ]
			return ModeModifier(*args)
		
		cm = action.get_compatible_modifiers()
		
		if (cm & Action.AF_MOD_BALL) != 0:
			if self.friction >= 0:
				action = BallModifier(round(self.friction, 3), action)
		
		if (cm & Action.AF_MOD_SENSITIVITY) != 0:
			# Strip 1.0's from sensitivity values
			sens = [] + self.sens
			while len(sens) > 0 and sens[-1] == 1.0:
				sens = sens[0:-1]
			
			if len(sens) > 0:
				# Build arguments
				sens.append(action)
				# Create modifier
				action = SensitivityModifier(*sens)
		
		if (cm & Action.AF_MOD_FEEDBACK) != 0:
			if self.feedback_position != None:
				# Strip defaults from feedback values
				feedback = [] + self.feedback
				while len(feedback) > 0 and feedback[-1] == self.feedback_widgets[len(feedback)-1][-1]:
					feedback = feedback[0:-1]
				
				cbFeedbackSide = self.builder.get_object("cbFeedbackSide")
				cbFeedback = self.builder.get_object("cbFeedback")
				grFeedback = self.builder.get_object("grFeedback")
				if from_custom or (cbFeedback.get_active() and grFeedback.get_sensitive()):
					# Build FeedbackModifier arguments
					feedback = [ FEEDBACK_SIDES[cbFeedbackSide.get_active()] ] + feedback
					feedback += [ action ]
					# Create modifier
					action = FeedbackModifier(*feedback)
		
		if (cm & Action.AF_MOD_SMOOTH) != 0:
			if self.smoothing != None:
				action = SmoothModifier(*( list(self.smoothing) + [ action ]))
		
		if (cm & Action.AF_MOD_DEADZONE) != 0:
			if self.deadzone_mode is not None:
				action = DeadzoneModifier(self.deadzone_mode, self.deadzone[0], self.deadzone[1], action)
		
		if (cm & Action.AF_MOD_ROTATE) != 0:
			if self.rotation_angle != 0.0:
				action = RotateInputModifier(self.rotation_angle, action)
		
		if (cm & Action.AF_MOD_OSD) != 0:
			if self.osd:
				action = OSDAction(action)
		
		if (cm & Action.AF_MOD_CLICK) != 0:
			if self.click:
				action = ClickedModifier(action)
		
		return action
	
	@staticmethod
	def is_editable_modifier(action):
		"""
		Returns True if provided action is instance of modifier that
		ActionEditor can display and edit.
		Returns False for everything else, even if it is instalce of Modifier
		subclass.
		"""
		if isinstance(action, (ClickedModifier, SensitivityModifier,
				DeadzoneModifier, FeedbackModifier, RotateInputModifier,
				SmoothModifier, BallModifier)):
			return True
		if isinstance(action, OSDAction):
			if action.action is not None:
				return True
		return False
	
	
	@staticmethod
	def strip_modifiers(action):
		"""
		Returns action stripped of all modifiers that are editable by editor.
		"""
		while action:
			if ActionEditor.is_editable_modifier(action):
				action = action.action
			else:
				return action
		return action
	
	
	def load_modifiers(self, action, index=-1):
		"""
		Parses action for modifiers and updates UI accordingly.
		Returns action without parsed modifiers.
		"""
		cbRequireClick = self.builder.get_object("cbRequireClick")
		sclRotation = self.builder.get_object("sclRotation")
		cbOSD = self.builder.get_object("cbOSD")
		
		while ActionEditor.is_editable_modifier(action):
			if isinstance(action, RotateInputModifier):
				self.rotation_angle = action.angle
				action = action.action
			if isinstance(action, OSDAction):
				self.osd = True
				action = action.action
			if isinstance(action, ClickedModifier):
				self.click = True
				action = action.action
			if isinstance(action, FeedbackModifier):
				self.feedback_position = action.get_haptic().get_position()
				self.feedback[0] = action.get_haptic().get_amplitude()
				self.feedback[1] = action.get_haptic().get_frequency()
				self.feedback[2] = action.get_haptic().get_period()
				action = action.action
			if isinstance(action, SmoothModifier):
				self.smoothing = ( action.level, action.multiplier, action.filter)
				action = action.action
			if isinstance(action, DeadzoneModifier):
				self.deadzone_mode = action.mode
				self.deadzone[0] = action.lower
				self.deadzone[1] = action.upper
				action = action.action
			if isinstance(action, SensitivityModifier):
				if index < 0:
					for i in xrange(0, len(self.sens)):
						self.sens[i] = action.sensitivity[i]
				else:
					self.sens[index] = action.sensitivity[0]
				action = action.action
			if isinstance(action, BallModifier):
				self.friction = action.friction
				action = action.action
		
		self._recursing = True
		cbRequireClick.set_active(self.click)
		cbOSD.set_active(self.osd)
		sclRotation.set_value(self.rotation_angle)
		for i in xrange(0, len(self.sens)):
			self.sens_widgets[i][3].set_active(self.sens[i] < 0)
			self.sens_widgets[i][0].set_value(abs(self.sens[i]))
		# Feedback
		cbFeedbackSide = self.builder.get_object("cbFeedbackSide")
		lblFeedbackSide = self.builder.get_object("lblFeedbackSide")
		if self.feedback_position != None:
			cbFeedback = self.builder.get_object("cbFeedback")
			cbFeedbackSide.set_active(FEEDBACK_SIDES.index(self.feedback_position))
			cbFeedback.set_active(True)
			for i in xrange(0, len(self.feedback)):
				self.feedback_widgets[i][0].set_value(self.feedback[i])
		for grp in self.feedback_widgets:
			for w in grp[0:-1]:
				w.set_sensitive(self.feedback_position is not None)
		lblFeedbackSide.set_sensitive(self.feedback_position is not None)
		cbFeedbackSide.set_sensitive(self.feedback_position is not None)
		
		# Smoothing
		cbSmoothing = self.builder.get_object("cbSmoothing")
		if self.smoothing:
			cbSmoothing.set_active(True)
			for i in xrange(0, len(self.smoothing_widgets)):
				self.smoothing_widgets[i][1].set_value(self.smoothing[i])
		for grp in self.smoothing_widgets:
			for w in grp[0:-1]:
				w.set_sensitive(cbSmoothing.get_active())
		
		# Ball
		sclFriction = self.builder.get_object("sclFriction")
		cbBallMode = self.builder.get_object("cbBallMode")
		if self.friction < 0:
			cbBallMode.set_active(False)
		elif self.friction == 0:
			cbBallMode.set_active(True)
			sclFriction.set_value(0)
		else:
			cbBallMode.set_active(True)
			sclFriction.set_value(math.log(self.friction * 1000.0, 10))
		
		# Deadzone
		cbDeadzoneMode = self.builder.get_object("cbDeadzoneMode")
		lblDeadzoneMode = self.builder.get_object("lblDeadzoneMode")
		if self.deadzone_mode is not None:
			cbDeadzone = self.builder.get_object("cbDeadzone")
			cbDeadzone.set_active(True)
			cbDeadzoneMode.set_active(DEADZONE_MODES.index(self.deadzone_mode))
			for i in xrange(0, len(self.deadzone)):
				self.deadzone_widgets[i][1].set_value(self.deadzone[i])
		
		for grp in self.deadzone_widgets:
			for w in grp[0:-1]:
				w.set_sensitive(self.deadzone_mode is not None)
		lblDeadzoneMode.set_sensitive(self.deadzone_mode is not None)
		cbDeadzoneMode.set_sensitive(self.deadzone_mode is not None)
		
		self._recursing = False
		
		return action
	
	
	def allow_first_page(self):
		"""
		Allows first page to be used
		"""
		self.first_page_allowed = True
	
	
	def reset_active_component(self):
		"""
		Forgets what component was selected so next call to set_action
		selects new one.
		"""
		self._selected_component = None
	
	
	def set_action(self, action, from_custom=False):
		"""
		Updates Action field(s) on bottom and recolors apropriate image area,
		if such area exists.
		"""
		entAction = self.builder.get_object("entAction")
		cbPreview = self.builder.get_object("cbPreview")
		btOK = self.builder.get_object("btOK")
		
		# Load modifiers and update UI if needed
		action = self.load_modifiers(action)
		
		# Check for InvalidAction and display error message if found
		if isinstance(action, InvalidAction):
			btOK.set_sensitive(False)
			entAction.set_name("error")
			entAction.set_text(str(action.error))
		else:
			entAction.set_name("entAction")
			btOK.set_sensitive(True)
			self._action = action
			action = self.generate_modifiers(action, from_custom)
			
			if isinstance(action, InvalidAction) and "\n" not in action.string:
				# Stuff generated by my special parser
				entAction.set_text(action.string)
			else:
				# Actions generated elsewhere
				entAction.set_text(action.to_string())
			self.enable_modifiers(self._action)
			self.enable_preview(self._action)
		
		# Send changed action into selected component
		if self._selected_component is None:
			for component in reversed(sorted(self.components, key = lambda a : a.PRIORITY)):
				if (component.CTXS & self._mode) != 0:
					if component.handles(self._mode, ActionEditor.strip_modifiers(action)):
						self._selected_component = component
						break
			if isinstance(action, InvalidAction):
				c = self.load_component("custom")
				if c in self.components and (self._mode & c.CTXS) != 0:
					self._selected_component = c
			elif not action and self.first_page_allowed:
				self._selected_component = self.load_component("first_page")
				stActionModes = self.builder.get_object("stActionModes")
				self._selected_component.load()
				self._selected_component.shown()
				stActionModes.add(self._selected_component.get_widget())
				stActionModes.set_visible_child(self._selected_component.get_widget())
			if self._selected_component:
				if self._selected_component in self.c_buttons:
					self.c_buttons[self._selected_component].set_active(True)
			if isinstance(action, InvalidAction):
				self._selected_component.set_action(self._mode, action)
		elif not self._selected_component.handles(self._mode, ActionEditor.strip_modifiers(action)):
			log.warning("selected_component no longer handles edited action")
			log.warning(self._selected_component)
			log.warning(ActionEditor.strip_modifiers(action).to_string())
			log.warning("(%s)", action.to_string())
		
		if cbPreview.get_sensitive() and cbPreview.get_active():
			self.apply_preview(action)
	
	
	def apply_preview(self, action):
		if self._replaced_action is None:
			self._replaced_action = self.ac_callback(self.id, action, mark_changed=False)
		else:
			self.ac_callback(self.id, action, mark_changed=False)
	
	
	def on_cbPreview_toggled(self, cb):
		if cb.get_active():
			a = self.generate_modifiers(self._action, self._selected_component.NAME=="custom")
			self.apply_preview(a)
		elif self._replaced_action is not None:
			if self.ac_callback:
				# Is None if OK button handler was executed
				self.ac_callback(self.id, self._replaced_action, mark_changed=False)
			self._replaced_action = None
	
	
	def enable_preview(self, action):
		"""
		Enables or disables and hides 'preview immediately' option, based on
		if currently selected action supports it.
		"""
		cbPreview = self.builder.get_object("cbPreview")
		
		enabled = action.strip().get_previewable()
		cbPreview.set_sensitive(enabled)
	
	
	def enable_modifiers(self, action):
		"""
		Enables or disables and hides modifier settings according to what
		is applicable for specified action AND what's allowed for current
		editor mode.
		
		Uses value returned by action.get_compatible_modifiers.
		"""
		cm = action.get_compatible_modifiers() & ActionEditor.MODE_TO_MODS[self._mode]
		
		# Feedback
		grFeedback = self.builder.get_object("grFeedback")
		grFeedback.set_sensitive((cm & Action.AF_MOD_FEEDBACK) != 0)
		
		# Smoothing
		grSmoothing = self.builder.get_object("grSmoothing")
		grSmoothing.set_sensitive((cm & Action.AF_MOD_SMOOTH) != 0)
		
		# Deadzone
		grDeadzone = self.builder.get_object("grDeadzone")
		grDeadzone.set_sensitive((cm & Action.AF_MOD_DEADZONE) != 0)
		
		# Sensitivity
		grSensitivity = self.builder.get_object("grSensitivity")
		grSensitivity.set_sensitive((cm & Action.AF_MOD_SENSITIVITY) != 0)
		for w in self.sens_widgets[2]:
			w.set_visible((cm & Action.AF_MOD_SENS_Z) != 0)
		
		# Rotation
		for w in ("lblRotationHeader", "lblRotation", "sclRotation", "btClearRotation"):
			self.builder.get_object(w).set_sensitive((cm & Action.AF_MOD_ROTATE) != 0)
		
		# Click
		cbRequireClick = self.builder.get_object("cbRequireClick")
		cbRequireClick.set_sensitive((cm & Action.AF_MOD_CLICK) != 0)
		
		# Ball
		cbBallMode = self.builder.get_object("cbBallMode")
		cbBallMode.set_sensitive((cm & Action.AF_MOD_BALL) != 0)
		for w in ("sclFriction", "lblFriction", "btClearFriction"):
			self.builder.get_object(w).set_sensitive(cbBallMode.get_active() and ((cm & Action.AF_MOD_BALL) != 0))
		if cm & Action.AF_MOD_BALL == 0:
			self.builder.get_object("cbBallMode").set_active(False)
		
		# OSD
		cbOSD = self.builder.get_object("cbOSD")
		cbOSD.set_sensitive(cm & Action.AF_MOD_OSD != 0)


	def set_sensitivity(self, x, y=1.0, z=1.0):
		""" Sets sensitivity for edited action """
		self._recursing = True
		xyz = [ x, y, z ]
		for i in xrange(0, len(self.sens)):
			self.sens[i] = xyz[i]
			self.sens_widgets[i][3].set_active(self.sens[i] < 0)
			self.sens_widgets[i][0].set_value(abs(self.sens[i]))
		self._recursing = False
		self.set_action(self._action)
		self._selected_component.modifier_updated()
	
	
	def get_sensitivity(self):
		""" Returns sensitivity currently set in editor """
		return tuple(self.sens)
	
	
	def set_default_sensitivity(self, x, y=1.0, z=1.0):
		"""
		Sets default sensitivity values and, if sensitivity
		is currently set to defaults, updates it to these values
		"""
		xyz = x, y, z
		update = False
		self._recursing = True
		for i in (0, 1, 2):
			if self.sens[i] == self.sens_defaults[i]:
				self.sens[i] = xyz[i]
				self.sens_widgets[i][0].set_value(xyz[i])
				update = True
			self.sens_defaults[i] = xyz[i]
		self._recursing = False
		if update:
			self.update_modifiers()
	
	
	def get_mode(self):
		return self._mode
	
	
	def _set_mode(self, action, mode):
		""" Common part of editor setup """
		self._mode = mode
		# Clear pages and 'action type' buttons
		entName = self.builder.get_object("entName")
		vbActionButtons = self.builder.get_object("vbActionButtons")
		stActionModes = self.builder.get_object("stActionModes")
		
		if isinstance(action, NameModifier):
			entName.set_text(action.name)
			print "_NameModifier: ", action, "->", action.child
			action = action.child
		else:
			entName.set_text("")
		
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
		
		if vbActionButtons.get_visible():
			vbActionButtons.show_all()
		
		return action
	
	def on_sclFFrequency_format_value(self, scale, value):
		if value == 1:
			# Special case
			return " %0.2fHz" % (1.0/value,)
		return "%0.2fmHz" % (100.0/value,)
	
	
	def on_sclFriction_format_value(self, scale, value):
		if value <= 0:
			return "%0.3f" % (0,)
		elif value >= 6:
			return "%0.3f" % (1000.00,)
		else:
			return "%0.3f" % ((10.0**value)/1000.0)
	
	
	def on_btClearFriction_clicked(self, *a):
		sclFriction = self.builder.get_object("sclFriction")
		sclFriction.set_value(math.log(10 * 1000.0, 10))
	
	
	def set_input(self, id, action, mode=None):
		"""
		Setups action editor for editing specified input.
		Mode (buttton/axis/trigger...) is either provided or chosen based on id.
		Also sets title, but that can be overriden by calling set_title after.
		"""
		self.id = id
		if id in SCButtons or mode in (Action.AC_MENU, Action.AC_BUTTON):
			if id in PRESSABLE:
				self.set_title(_("%s Press") % (nameof(id),))
			elif id in SCButtons:
				self.set_title(nameof(id),)
			action = self._set_mode(action, mode or Action.AC_BUTTON)
			self.hide_modifiers()
			self.set_action(action)
		elif id in TRIGGERS:
			self.set_title(_("%s Trigger") % (id,))
			action = self._set_mode(action, mode or Action.AC_TRIGGER)
			self.set_action(action)
			self.hide_macro()
			self.hide_ring()
		elif id in STICKS:
			self.set_title(_("Stick"))
			action = self._set_mode(action, mode or Action.AC_STICK)
			self.set_action(action)
			self.hide_macro()
			self.id = Profile.STICK
		elif id in GYROS:
			self.set_title(_("Gyro"))
			action = self._set_mode(action, mode or Action.AC_GYRO)
			self.set_action(action)
			self.hide_modeshift()
			self.hide_macro()
			self.hide_ring()
			self.id = Profile.GYRO
		elif id in PADS:
			action = self._set_mode(action, mode or Action.AC_PAD)
			self.set_action(action)
			self.hide_macro()
			if id == Profile.LPAD:
				self.set_title(_("Left Pad"))
			elif id == Profile.RPAD:
				self.set_title(_("Right Pad"))
			else:
				self.set_title(_("Touch Pad"))
		if mode == Action.AC_OSK:
			self.hide_name()
			self.hide_modeshift()
			self.hide_macro()
			self.hide_ring()
			# self.hide_rotation()
		elif mode == Action.AC_MENU:
			self.hide_modeshift()
			self.hide_macro()
			self.hide_ring()
	
	
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
		# self.hide_osd()
		self.hide_action_buttons()
		self.hide_modifiers()
		self.set_action(NoAction())
		self.id = item.id
		if title_for_name_label:
			self.builder.get_object("lblName").set_label(title_for_name_label)
	
	
	def set_modifiers_enabled(self, enabled):
		exMore = self.builder.get_object("exMore")
		rvMore = self.builder.get_object("rvMore")
		if self._modifiers_enabled != enabled and not enabled:
			exMore.set_expanded(False)
			rvMore.set_reveal_child(False)
		exMore.set_sensitive(enabled)
		self._modifiers_enabled = enabled
