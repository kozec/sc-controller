#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.gui.svg_widget import SVGWidget
from scc.gui.parser import GuiActionParser, InvalidAction
from scc.gui.gdk_to_key import keyevent_to_key
from scc.gui.area_to_action import AREA_TO_ACTION
from scc.uinput import Keys
import os, sys, time, logging
log = logging.getLogger("ActionEditor")

class ActionEditor:

	IMAGE1 = "actions.svg"
	IMAGE2 = "axistrigger.svg"

	MODE_BUTTON = 1
	MODE_TRIGGER = 3

	MODIFIERS = [ Keys.KEY_LEFTCTRL, Keys.KEY_LEFTMETA, Keys.KEY_LEFTALT,
		Keys.KEY_RIGHTALT, Keys.KEY_RIGHTMETA, Keys.KEY_RIGHTCTRL,
		Keys.KEY_LEFTSHIFT, Keys.KEY_RIGHTSHIFT
	]

	ERROR_CSS = " #error {background-color:green; color:red;} "
	PAGES = [
		('vbKeyBut',			'tgKeyBut',				[ MODE_BUTTON ]),
		('grKeyButByTrigger',	'tgKeyButByTrigger',	[ MODE_TRIGGER ]),
		('vbAxisTrigger',		'tgAxisTrigger',		[ MODE_TRIGGER ]),
		('vbCustom',			'tgCustom',				[ MODE_BUTTON, MODE_TRIGGER ]),
	]
	CUSTOM_PAGE = 'tgCustom'
	DEFAULT_PAGE = {
		MODE_BUTTON		: 'tgKeyBut',
		MODE_TRIGGER	: 'tgKeyButByTrigger'
	}

	css = None

	def __init__(self, app):
		self.app = app
		self.mode = None
		self.id = None
		self.parser = GuiActionParser()
		if ActionEditor.css is None:
			ActionEditor.css = Gtk.CssProvider()
			ActionEditor.css.load_from_data(str(ActionEditor.ERROR_CSS))
			Gtk.StyleContext.add_provider_for_screen(
					Gdk.Screen.get_default(),
					ActionEditor.css,
					Gtk.STYLE_PROVIDER_PRIORITY_USER)
		self._recursing = False
		self.active_mods = []
		self.setup_widgets()


	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, "action.glade"))
		self.window = self.builder.get_object("actionEditor")
		self.keygrab = self.builder.get_object("keyGrab")
		self.builder.connect_signals(self)

		for (p_id, img) in ( ("vbKeyBut", self.IMAGE1), ("vbAxisTrigger", self.IMAGE2) ):
			parent = self.builder.get_object(p_id)
			self.background = SVGWidget(self.app, os.path.join(self.app.iconpath, img))
			self.background.connect('hover', self.on_background_area_hover)
			self.background.connect('leave', self.on_background_area_hover, None)
			self.background.connect('click', self.on_background_area_click)
			parent.pack_start(self.background, True, True, 0)
			parent.show_all()

		entAction = self.builder.get_object("entAction")


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
				entAction.set_name("entAction")
				entAction.set_text(txt)


	def on_btnGrabKey_clicked(self, *a):
		"""
		Called when user clicks on 'Grab a Key' button.
		Displays additional dialog.
		"""
		self.active_mods = []
		self.keygrab.set_transient_for(self.window)
		self.keygrab.set_modal(True)
		self.builder.get_object("lblKey").set_label("...")
		for key in ActionEditor.MODIFIERS:
			self.builder.get_object("tg" + key.name).set_active(False)
		self.keygrab.show()
		self.keygrab.set_focus()


	def on_background_area_click(self, trash, area):
		"""
		Called when user clicks on defined area on gamepad image.
		Fills Action field on bottom with apropriate action code.
		"""
		entAction = self.builder.get_object("entAction")
		if area in AREA_TO_ACTION:
			cls, params = AREA_TO_ACTION[area][0], AREA_TO_ACTION[area][1:]
			self.set_action(cls(params))
		else:
			log.warning("Click on unknown area: %s" % (area,))
	
	
	def on_background_area_hover(self, background, area):
		background.hilight(area, "#FFFF0000")	# ARGB


	def on_actionEditor_key_press_event(self, trash, event):
		""" Checks if pressed key was escape and if yes, closes window """
		if event.keyval == Gdk.KEY_Escape:
			self.window.destroy()


	def on_tgkey_toggled(self, obj, *a):
		"""
		Handles when user clicks on modifier buttons in "Grab Key" dialog
		"""
		for key in ActionEditor.MODIFIERS:
			if self.builder.get_object("tg" + key.name) == obj:
				if obj.get_active() and not key in self.active_mods:
					self.active_mods.append(key)
					self.builder.get_object("lblKey").set_label(merge_modifiers(self.active_mods))
				elif not obj.get_active() and key in self.active_mods:
					self.active_mods.remove(key)
					self.builder.get_object("lblKey").set_label(merge_modifiers(self.active_mods))
				return


	def on_keyGrab_key_press_event(self, trash, event):
		"""
		Handles keypress on "Grab Key" dialog.
		
		Remembers modifiers and displays text in middle of dialog.
		Dialog is dismissed (and key is accepted) by key_release handler bellow.
		"""
		key = keyevent_to_key(event)
		if key is None:
			log.warning("Unknown keycode %s/%s" % (event.keyval, event.hardware_keycode))
			return

		if key in ActionEditor.MODIFIERS:
			self.active_mods.append(key)
			self.builder.get_object("tg" + key.name).set_active(True)
			self.builder.get_object("lblKey").set_label(merge_modifiers(self.active_mods))
			return

		label = merge_modifiers(self.active_mods)
		if len(self.active_mods) > 0:
			label = label + "+" + key.name
		else:
			label = key.name
		self.builder.get_object("lblKey").set_label(label)


	def on_keyGrab_key_release_event(self, trash, event):
		"""
		Handles keyrelease on "Grab Key" dialog.
		
		Key is accepted if either:
		- released key is not modifier
		- released key is modifier, but there is no other modifier key pressed
		
		Calls on_key_grabbed if key is accepted
		"""
		key = keyevent_to_key(event)
		if key is not None:
			if key in ActionEditor.MODIFIERS:
				if key in self.active_mods:
					if len(self.active_mods) == 1:
						# Releasing last modifier
						self.on_key_grabbed([key])
						return
					self.active_mods.remove(key)
					self.builder.get_object("tg" + key.name).set_active(False)
				self.builder.get_object("lblKey").set_label("+".join([key.name.split("_")[-1] for key in self.active_mods]))
				return

			self.on_key_grabbed(self.active_mods + [key])


	def on_btOK_clicked(self, *a):
		""" Handler for OK button ... """
		entAction = self.builder.get_object("entAction")
		action = self.parser.restart(entAction.get_text()).parse()
		self.app.set_action(self.id, action)
		self.window.destroy()


	def on_key_grabbed(self, keys):
		""" Handles selecting key using "Grab the Key" dialog """
		entAction = self.builder.get_object("entAction")
		actions = [ 'button(Keys.%s)' % (key.name,) for key in keys ]
		entAction.set_text("; ".join(actions))
		self.keygrab.hide()


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


	def _set_mode(self, mode):
		""" Hides 'action type' buttons that are not usable with current mode """
		self.mode = ActionEditor.MODE_BUTTON
		for (page, button, modes) in ActionEditor.PAGES:
			self.builder.get_object(button).set_visible(mode in modes)
		self.builder.get_object(ActionEditor.DEFAULT_PAGE[mode]).set_active(True)


	def set_button(self, button):
		""" Setups action editor as editor for button action """
		self._set_mode(ActionEditor.MODE_BUTTON)
		self.id = button


	def set_trigger(self, trigger):
		""" Setups action editor as editor for button action """
		self._set_mode(ActionEditor.MODE_TRIGGER)
		self.id = trigger


	def set_title(self, title):
		self.window.set_title(title)
		self.builder.get_object("header").set_title(title)


	def show(self, modal_for):
		self.window.set_transient_for(modal_for)
		self.window.set_modal(True)
		self.window.show()


def merge_modifiers(mods):
	return "+".join([ key.name.split("_")[-1] for key in mods ])
