#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.uinput import Keys
from scc.actions import Action, ButtonAction
from scc.gui.svg_widget import SVGWidget
from scc.gui.button_chooser import ButtonChooser
from scc.gui.area_to_action import AREA_TO_ACTION, action_to_area
from scc.gui.parser import GuiActionParser, InvalidAction
import os, sys, time, logging
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
		('vbAxisTrigger',		'tgAxisTrigger',		[ Action.AC_TRIGGER ]),
		('vbCustom',			'tgCustom',				[ Action.AC_BUTTON, Action.AC_TRIGGER ]),
	]
	CUSTOM_PAGE = 'tgCustom'
	DEFAULT_PAGE = {
		Action.AC_BUTTON		: 'tgKeyBut',
		Action.AC_TRIGGER		: 'tgKeyButByTrigger'
	}

	css = None

	def __init__(self, app):
		ButtonChooser.__init__(self, app, self.on_button_chooser_callback)
		self.id = None
		self.parser = GuiActionParser()
		if ActionEditor.css is None:
			ActionEditor.css = Gtk.CssProvider()
			ActionEditor.css.load_from_data(str(ActionEditor.ERROR_CSS))
			Gtk.StyleContext.add_provider_for_screen(
					Gdk.Screen.get_default(),
					ActionEditor.css,
					Gtk.STYLE_PROVIDER_PRIORITY_USER)
		self._multiparams = [ None ] * 4
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
			txt = entAction.get_text().split(";")
			txt = [ t.strip(" \t") for t in txt ]
			tbCustomAction.set_text("\n".join(txt))
		
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
		btOK = self.builder.get_object("btOK")

		# Get text from buffer
		txt = tbCustomAction.get_text(tbCustomAction.get_start_iter(), tbCustomAction.get_end_iter(), True)

		# Convert it to simpler text separated only with ';'
		txt = txt.replace(";", "\n").split("\n")
		txt = [ t.strip("\t ") for t in txt ]
		while "" in txt : txt.remove("")
		txt = "; ".join(txt)

		# Try to parse it as action
		if len(txt) > 0:
			action = self.parser.restart(txt).parse()
			if isinstance(action, InvalidAction):
				btOK.set_sensitive(False)
				entAction.set_name("error")
				entAction.set_text(str(action.error))
			else:
				btOK.set_sensitive(True)
				self.set_action(action)
	
	
	def on_button_chooser_callback(self, action):
		"""
		Called when user clicks on defined area on gamepad image
		or selects key using key grabber.
		Fills Action field on bottom with apropriate action code.
		"""
		entAction = self.builder.get_object("entAction")
		self.set_action(action)
	
	
	def on_actionEditor_key_press_event(self, trash, event):
		""" Checks if pressed key was escape and if yes, closes window """
		if event.keyval == Gdk.KEY_Escape:
			self.close()
	
	
	def on_btFullPress_clicked(self, *a):
		""" Fully Pressed Action handler """
		def cb(action):
			self._multiparams[0] = action.parameters[0]
			b.close()
			self.set_multiparams(ButtonAction, 2)
		b = ButtonChooser(self.app, cb)
		b.show(self.window)
	
	
	def on_btPartPressed_clicked(self, *a):
		""" Partialy Pressed Action handler """
		def cb(action):
			self._multiparams[1] = action.parameters[0]
			b.close()
			self.set_multiparams(ButtonAction, 2)
		b = ButtonChooser(self.app, cb)
		b.show(self.window)
	
	
	def on_on_btPartPressedClear_clicked(self, *a):
		self._multiparams[1] = None
		self.set_multiparams(ButtonAction, 2)
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button ... """
		entAction = self.builder.get_object("entAction")
		action = self.parser.restart(entAction.get_text()).parse()
		self.app.set_action(self.id, action)
		self.close()


	def on_slave_finished(self, slave, action):
		self._param2action = self.parser.restart(action).parse()
		slave.close()
	
	
	def set_action(self, action):
		""" Updates Action field on bottom """
		# TODO: Display action on image as well
		entAction = self.builder.get_object("entAction")
		if hasattr(action, 'string'):
			# Stuff generated by my special parser
			entAction.set_text(action.string)
		else:
			# Actions generated elsewhere
			entAction.set_text(action.to_string())
		area = action_to_area(action)
		if area is not None:
			self.set_active_area(area)

	def set_multiparams(self, cls, count):
		""" Handles creating actions with multiple parameters """
		if count >= 0:
			self.builder.get_object("lblFullPress").set_label(self.describe_action(cls, self._multiparams[0]))
		if count >= 1:
			self.builder.get_object("lblPartPressed").set_label(self.describe_action(cls, self._multiparams[1]))
		pars = self._multiparams[0:count]
		while len(pars) > 1 and pars[-1] is None:
			pars = pars[0:-1]
		self.set_action(cls(pars))


	def _set_mode(self, mode):
		""" Hides 'action type' buttons that are not usable with current mode """
		self._mode = mode
		for (page, button, modes) in ActionEditor.PAGES:
			self.builder.get_object(button).set_visible(mode in modes)
		self.builder.get_object(ActionEditor.DEFAULT_PAGE[mode]).set_active(True)


	def set_button(self, button):
		""" Setups action editor as editor for button action """
		self._set_mode(Action.AC_BUTTON)
		self.id = button


	def set_trigger(self, trigger):
		""" Setups action editor as editor for button action """
		self._set_mode(Action.AC_TRIGGER)
		self.id = trigger


	def describe_action(self, cls, v):
		"""
		Returns action description with 'v' as parameter, unless unless v is None.
		Returns "not set" if v is None
		"""
		if v is None:
			return _('(not set)')
		else:
			return (cls([v])).describe(self._mode)
			