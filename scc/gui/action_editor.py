#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.uinput import Keys, Axes, Rels
from scc.actions import AxisAction, MouseAction, ButtonAction
from scc.actions import RAxisAction, TrackballAction, TrackpadAction
from scc.actions import DPadAction, DPad8Action
from scc.actions import Action, XYAction, NoAction
from scc.modifiers import Modifier, ClickModifier
from scc.actions import TRIGGER_HALF, TRIGGER_CLICK
from scc.profile import Profile
from scc.gui.area_to_action import AREA_TO_ACTION, action_to_area
from scc.gui.parser import GuiActionParser, InvalidAction
from scc.gui.button_chooser import ButtonChooser
from scc.gui.axis_chooser import AxisChooser
from scc.gui.svg_widget import SVGWidget
import os, logging
log = logging.getLogger("ActionEditor")

class ActionEditor(ButtonChooser):
	GLADE = "action_editor.glade"
	IMAGES = {
		"vbKeyBut"		: "buttons.svg",
		"vbAxisTrigger"	: "axistrigger.svg"
	}
	
	ERROR_CSS = " #error {background-color:green; color:red;} "
	PAGES = [
		('vbKeyBut',			'tgKeyBut',				[ Action.AC_BUTTON ]),
		('grKeyButByTrigger',	'tgKeyButByTrigger',	[ Action.AC_TRIGGER ]),
		('vbAxisMouseByStick',	'tgAxisMouseByStick',	[ Action.AC_STICK, Action.AC_PAD ]),
		('grDPAD',				'tgDPAD',				[ Action.AC_STICK, Action.AC_PAD ]),
		('vbAxisTrigger',		'tgAxisTrigger',		[ Action.AC_TRIGGER ]),
		('vbPerAxis',			'tgPerAxis',			[ Action.AC_STICK, Action.AC_PAD ]),
		('vbCustom',			'tgCustom',				[ Action.AC_BUTTON, Action.AC_STICK, Action.AC_PAD, Action.AC_TRIGGER ]),
	]
	CUSTOM_PAGE = 'tgCustom'
	DEFAULT_PAGE = {
		Action.AC_BUTTON		: 'tgKeyBut',
		Action.AC_TRIGGER		: 'tgKeyButByTrigger',
		Action.AC_STICK			: 'tgAxisMouseByStick',
		Action.AC_PAD			: 'tgAxisMouseByStick'
	}
	DPAD8_WIDGETS = [ 'btDPAD7', 'btDPAD9', 'btDPAD1', 'btDPAD3' ]

	css = None

	def __init__(self, app, callback):
		ButtonChooser.__init__(self, app, self.on_button_chooser_callback)
		self.id = None
		self.ac_callback = callback	# This is different callback than ButtonChooser uses
		self.parser = GuiActionParser()
		if ActionEditor.css is None:
			ActionEditor.css = Gtk.CssProvider()
			ActionEditor.css.load_from_data(str(ActionEditor.ERROR_CSS))
			Gtk.StyleContext.add_provider_for_screen(
					Gdk.Screen.get_default(),
					ActionEditor.css,
					Gtk.STYLE_PROVIDER_PRIORITY_USER)
		self._multiparams = [ None ] * 8
		self._mode = None
		self._recursing = False
		self.allow_axes()
	
	
	def setup_widgets(self):
		ButtonChooser.setup_widgets(self)
	
	
	def on_action_mode_changed(self, obj):
		"""
		Called when user clicks on one of Actio Type buttons.
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
		
		#  Uncheck all other Action Buttons
		active = None
		for (page, button, modes) in ActionEditor.PAGES:
			if obj == self.builder.get_object(button):
				active = (page, button)
			else:
				self.builder.get_object(button).set_active(False)
		self._recursing = False
		
		# Special handling for 'Custom Action' page.
		# Text area on it needs to be filled with action code before
		# page is shown
		if active[1] == ActionEditor.CUSTOM_PAGE:
			tbCustomAction = self.builder.get_object("tbCustomAction")
			entAction = self.builder.get_object("entAction")
			entActionY = self.builder.get_object("entActionY")
			if len(entActionY.get_text()) > 0:
				x = self.parser.restart(entAction.get_text()).parse()
				y = self.parser.restart(entActionY.get_text()).parse()
				txt = XYAction(x, y).to_string(True)
			else:
				txt = self.parser.restart(entAction.get_text()).parse().to_string(True)
			tbCustomAction.set_text(txt)
		
		# Switch to apropriate page
		stActionModes = self.builder.get_object("stActionModes")
		stActionModes.set_visible_child(self.builder.get_object(active[0]))
	
	
	def on_tbCustomAction_changed(self, tbCustomAction, *a):
		"""
		Converts text from Custom Action text area into text
		that can be displayed in Action field on bottom
		"""
		txCustomAction = self.builder.get_object("txCustomAction")
		entAction = self.builder.get_object("entAction")
		entActionY = self.builder.get_object("entActionY")
		btOK = self.builder.get_object("btOK")
		
		# Get text from buffer
		txt = tbCustomAction.get_text(tbCustomAction.get_start_iter(), tbCustomAction.get_end_iter(), True)
		txt.strip(" \t\r")
		
		# Convert it to simpler text separated only with ';'
		def convert_newlines(t):
			return t
			t = [ x.strip(" \t") for x in t.split("\n") ]
			t = [
				x + ";" if (" " + x)[-1] not in "(;," else x
				for x in t
			]
			while "" in t : t.remove("")
			print "-" + "\n-".join(t)
			return " ".join(t)
		
		if txt.startswith("X:"):
			# Special case, there are two separate actions for X and Y axis defined
			index = txt.find("Y:")
			if index == -1:
				# There is actions for X axis but not for Y
				txt = "XY(" + convert_newlines(txt[2:]) + ")"
			else:
				# Both X and Y actions are defined
				x = convert_newlines(txt[2:index])
				y = convert_newlines(txt[index+2:])
				txt = "XY(" + x + "," + y + ")"
		else:
			txt = convert_newlines(txt)
		
		# Try to parse it as action
		if len(txt) > 0:
			action = self.parser.restart(txt).parse()
			if isinstance(action, InvalidAction):
				btOK.set_sensitive(False)
				entAction.set_name("error")
				entAction.set_text(str(action.error))
				self._set_y_field_visible(False)
			else:
				self.set_action(action)
	
	
	def on_cbDPADType_changed(self, *a):
		cb = self.builder.get_object("cbDPADType")
		for i in self.DPAD8_WIDGETS:
			self.builder.get_object(i).set_visible(cb.get_active() == 1)
		cls, num = (DPadAction, 4) if cb.get_active() == 0 else (DPad8Action, 8)
		mods = []
		if self.builder.get_object("cbDPADNeedsClick").get_active():
			mods.append(ClickModifier)
		self.set_multiparams(cls, num, mods)
	
	
	def on_btDPAD_clicked(self, b):
		""" 'Select DPAD Left Action' handler """
		cb = self.builder.get_object("cbDPADType")
		cls, num = (DPadAction, 4) if cb.get_active() == 0 else (DPad8Action, 8)
		mods = []
		if self.builder.get_object("cbDPADNeedsClick").get_active():
			mods.append(ClickModifier)
		param = int(b.get_name())
		self._grab_multiparam_action(cls, param, num,
			allow_axes=True, store_as_action=True, modifiers=mods)
	
	
	def on_cbDPADNeedsClick_toggled(self, *a):
		self.on_cbDPADType_changed()
	
	
	def on_button_chooser_callback(self, action):
		"""
		Called when user clicks on defined area on gamepad image
		or selects key using key grabber.
		Fills Action field on bottom with apropriate action code.
		"""
		entAction = self.builder.get_object("entAction")
		self.set_action(action)
	
	
	def _grab_multiparam_action(self, cls, param, count, allow_axes=False, store_as_action=False, modifiers=[]):
		def cb(action):
			if store_as_action:
				self._multiparams[param] = action
			else:
				self._multiparams[param] = action.parameters[0]
			b.close()
			self.set_multiparams(cls, count, modifiers)
		
		b, area = None, None
		if cls == XYAction:
			b = AxisChooser(self.app, cb)
			b.set_title(_("Select Axis"))
			area = action_to_area(self._multiparams[param])
		elif store_as_action:
			b = ButtonChooser(self.app, cb)
			b.set_title(_("Select Action"))
			area = action_to_area(self._multiparams[param])
		elif cls == ButtonAction:
			b = ButtonChooser(self.app, cb)
			b.set_title(_("Select Button"))
			action = cls([self._multiparams[param]])
			area = action_to_area(action)
		
		if allow_axes:
			b.allow_axes()
		if area is not None:
			b.set_active_area(area)
		b.show(self.window)
	
	
	def on_btFullPress_clicked(self, *a):
		""" 'Select Fully Pressed Action' handler """
		self._grab_multiparam_action(ButtonAction, 0, 4)
	
	
	def on_btPartPressed_clicked(self, *a):
		""" 'Select Partialy Pressed Action' handler """
		self._grab_multiparam_action(ButtonAction, 1, 4)
	
	
	def on_triggerSclchange_value(self, *a):
		self._multiparams[2] = int(self.builder.get_object("sclPartialLevel").get_value() + 0.1)
		self._multiparams[3] = int(self.builder.get_object("sclFullLevel").get_value() + 0.1)
		self.set_multiparams(ButtonAction, 4)
	
	
	def on_btPartPresedClear_clicked(self, *a):
		self.builder.get_object("sclPartialLevel").set_value(TRIGGER_HALF)
	
	
	def on_btFullyPresedClear_clicked(self, *a):
		self.builder.get_object("sclFullLevel").set_value(TRIGGER_CLICK)
	
	
	def on_btAxisX_clicked(self, *a):
		""" 'Select X Axis Action' handler """
		self._grab_multiparam_action(XYAction, 0, 2, True, True)
	
	
	def on_btAxisY_clicked(self, *a):
		""" 'Select Y Axis Action' handler """
		self._grab_multiparam_action(XYAction, 1, 2, True, True)
	
	
	def on_btPartPressedClear_clicked(self, *a):
		self._multiparams[1] = None
		self.set_multiparams(ButtonAction, 2)
	
	
	def on_btClear_clicked	(self, *a):
		""" Handler for clear button """
		action = NoAction()
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		entAction = self.builder.get_object("entAction")
		entActionY = self.builder.get_object("entActionY")
		action = self.parser.restart(entAction.get_text()).parse()
		if len(entActionY.get_text()) > 0:
			actionY = self.parser.restart(entActionY.get_text()).parse()
			action = XYAction(action, actionY)
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def on_btModeSwitch_clicked(self, *a):
		""" Asks main window to close this one and display mode switch editor """
		pass
	
	def on_cbAxisOutput_changed(self, *a):
		if self._recursing : return
		cbAxisOutput = self.builder.get_object("cbAxisOutput")
		rvSensitivity = self.builder.get_object("rvSensitivity")
		sens = self.builder.get_object("sclSensitivity")
		action = cbAxisOutput.get_model().get_value(cbAxisOutput.get_active_iter(), 0)
		has_sensitivity = "sensitivity" in action
		action = action.replace("sensitivity", str(sens.get_value()))
		action = self.parser.restart(action).parse()
		rvSensitivity.set_reveal_child(has_sensitivity)
		if isinstance(action, XYAction):
			self._multiparams[0] = action.actions[0]
			self._multiparams[1] = action.actions[1]
			self.set_multiparams(XYAction, 2)
		else:
			self.set_action(action)
	
	
	def on_btScaleClear_clicked(self, *a):
		sens = self.builder.get_object("sclSensitivity")
		sens.set_value(1.0)
		self.on_cbAxisOutput_changed()
	
	
	def _set_y_field_visible(self, visible):
		if visible:
			self.builder.get_object("rvlXLabel").set_reveal_child(True)
			self.builder.get_object("rvlYaction").set_reveal_child(True)
		else:
			self.builder.get_object("rvlXLabel").set_reveal_child(False)
			self.builder.get_object("rvlYaction").set_reveal_child(False)
			self.builder.get_object("entActionY").set_text("")
	
	
	def _select_axis_output(self, key):
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
	
	
	def _set_sensitivity(self, action):
		""" Sets value for sensitivity slider, if value is defined in action """
		try:
			sensitivity = float(action.parameters[1])
		except:
			try:
				sensitivity = float(action.parameters[0])
			except: return
		sens = self.builder.get_object("sclSensitivity")
		sens.set_value(sensitivity)
	
	
	def set_action(self, action):
		"""
		Updates Action field(s) on bottom and recolors apropriate image area,
		if such area exists.
		"""
		entAction = self.builder.get_object("entAction")
		entActionY = self.builder.get_object("entActionY")
		btOK = self.builder.get_object("btOK")
		entAction.set_name("entAction")
		btOK.set_sensitive(True)
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
		
		area = action_to_area(action)
		if area is not None:
			self.set_active_area(area)
	
	
	def set_multiparams(self, cls, count, modifiers=[]):
		""" Handles creating actions with multiple parameters """
		# TODO: This is getting messy, maybe find way how to put it into a loop
		if count >= 0:
			self.builder.get_object("lblFullPress").set_label(self.describe_action(cls, self._multiparams[0]))
			self.builder.get_object("lblDPADUp").set_label(self.describe_action(ButtonAction, self._multiparams[0]))
			self.builder.get_object("lblAxisX").set_label(self.describe_action(cls, self._multiparams[0]))
		if count >= 1:
			self.builder.get_object("lblPartPressed").set_label(self.describe_action(cls, self._multiparams[1]))
			self.builder.get_object("lblDPADDown").set_label(self.describe_action(ButtonAction, self._multiparams[1]))
			self.builder.get_object("lblAxisY").set_label(self.describe_action(cls, self._multiparams[1]))
		if count >= 2:
			self.builder.get_object("lblDPADLeft").set_label(self.describe_action(ButtonAction, self._multiparams[2]))
			if type(self._multiparams[2]) in (float, int):
				self.builder.get_object("sclPartialLevel").set_value(self._multiparams[2])
		if count >= 3:
			self.builder.get_object("lblDPADRight").set_label(self.describe_action(ButtonAction, self._multiparams[3]))
			if type(self._multiparams[3]) in (float, int):
				self.builder.get_object("sclFullLevel").set_value(self._multiparams[3])
		if count >= 4:
			self.builder.get_object("btDPAD7").set_label(self.describe_action(ButtonAction, self._multiparams[4]))
		if count >= 5:
			self.builder.get_object("btDPAD9").set_label(self.describe_action(ButtonAction, self._multiparams[5]))
		if count >= 6:
			self.builder.get_object("btDPAD1").set_label(self.describe_action(ButtonAction, self._multiparams[6]))
		if count >= 7:
			self.builder.get_object("btDPAD3").set_label(self.describe_action(ButtonAction, self._multiparams[7]))
		pars = self._multiparams[0:count]
		while len(pars) > 1 and pars[-1] is None:
			pars = pars[0:-1]
		
		a = cls(pars)
		for mod in modifiers: a = mod(a)
		self.set_action(a)
	
	
	def _set_mode(self, mode, activate_default=True):
		""" Hides 'action type' buttons that are not usable with current mode """
		self._mode = mode
		for (page, button, modes) in ActionEditor.PAGES:
			self.builder.get_object(button).set_visible(mode in modes)
			self.builder.get_object(page).set_visible(mode in modes)
		for i in ("lblX", "boxY"):
			self.builder.get_object(i).set_visible(self._mode in (Action.AC_STICK, Action.AC_PAD))
		if activate_default:
			self.builder.get_object(ActionEditor.DEFAULT_PAGE[mode]).set_active(True)
	
	
	def set_button(self, button, action):
		""" Setups action editor as editor for button action """
		self._set_mode(Action.AC_BUTTON)
		self.set_action(action)
		self.id = button
	
	
	def set_trigger(self, trigger, action):
		""" Setups action editor as editor for trigger action """
		self._set_mode(Action.AC_TRIGGER)
		self.set_action(action)
		self.id = trigger
		if isinstance(action, AxisAction):
			self.builder.get_object("tgAxisTrigger").set_active(True)
		elif isinstance(action, MouseAction):
			self.builder.get_object("tgAxisTrigger").set_active(True)
		elif isinstance(action, ButtonAction):
			for x in xrange(0, len(action.parameters)):
				self._multiparams[x] = action.parameters[x]
			self.set_multiparams(ButtonAction, 4)
	
	
	def set_stick(self, stickdata):
		""" Setups action editor as editor for stick action """
		self._set_mode(Action.AC_STICK)
		action = None
		if Profile.WHOLE in stickdata:
			action = stickdata[Profile.WHOLE]
		else:
			x = stickdata[Profile.X] if Profile.X in stickdata else None
			y = stickdata[Profile.Y] if Profile.Y in stickdata else None
			action = XYAction(x, y)
		self.set_action(action)
		if isinstance(action, ClickModifier):
			self.builder.get_object("cbDPADNeedsClick").set_active(True)
		while isinstance(action, Modifier):
			action = action.action
		if isinstance(action, DPadAction):
			for x in xrange(0, len(action.actions)):
				self._multiparams[x] = action.actions[x]
			self.set_multiparams(DPadAction, 4)
			if isinstance(action, DPad8Action):
				self.builder.get_object("cbDPADType").set_active(1)
			self.builder.get_object("tgDPAD").set_active(True)
		elif isinstance(action, TrackballAction):
			self._select_axis_output("trackball")
			self._set_sensitivity(action)
		elif isinstance(action, TrackpadAction):
			self._select_axis_output("trackpad")
			self._set_sensitivity(action)
		elif isinstance(action, XYAction):
			mfp = isinstance(action.actions[1], RAxisAction)	# mfp for 'may be first page'
			mfp = mfp or isinstance(action.actions[1], MouseAction)
			p = [ None, None ]
			for x in (0, 1):
				if len(action.actions[0].parameters) >= x:
					self._multiparams[x] = action.actions[x]
					p[x] = self._multiparams[x].parameters[0]
				else:
					self._multiparams[x] = None
			self.set_multiparams(XYAction, 2)
			if len(action.actions) < 2:
				self.builder.get_object("tgCustom").set_active(True)
			elif mfp and p[0] == Axes.ABS_X and p[1] == Axes.ABS_Y:
				self._select_axis_output("lstick")
				self._set_sensitivity(action.actions[0])
			elif mfp and p[0] == Axes.ABS_RX and p[1] == Axes.ABS_RY:
				self._select_axis_output("rstick")
				self._set_sensitivity(action.actions[0])
			elif mfp and p[0] == Axes.ABS_HAT0X and p[1] == Axes.ABS_HAT0Y:
				self._select_axis_output("dpad")
			elif mfp and p[0] == Rels.REL_HWHEEL and p[1] == Rels.REL_WHEEL:
				self._select_axis_output("wheel")
				self._set_sensitivity(action.actions[0])
			else:
				self.builder.get_object("tgPerAxis").set_active(True)
		self.id = Profile.STICK
	
	
	def set_pad(self, id, paddata):
		""" Setups action editor as editor for pad action """
		self.set_stick(paddata)
		self._set_mode(Action.AC_PAD, False)
		self.id = id
	
	
	def describe_action(self, cls, v):
		"""
		Returns action description with 'v' as parameter, unless unless v is None.
		Returns "not set" if v is None
		"""
		if v is None or type(v) in (int, float, str, unicode):
			return _('(not set)')
		elif isinstance(v, Action):
			if cls == XYAction:
				return v.describe(Action.AC_STICK)
			else:
				return v.describe(Action.AC_BUTTON)
		else:
			return (cls(v)).describe(self._mode)
