#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button action.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.gui.svg_widget import SVGWidget
from scc.gui.parser import GuiActionParser
from scc.gui.gdk_to_key import keyevent_to_key
from scc.uinput import Keys
import os, sys, time, logging
log = logging.getLogger("ActionEditor")

class ActionEditor:
	
	IMAGE = "actions.svg"
	
	MODE_BUTTON = 1
	
	BUTTONS = [ 'TL', 'THUMBL', 'SELECT', 'TR', 'THUMBR', 'START', 'A', 'B', 'X', 'Y' ]
	AXES = [ 'ABS_Z', 'ABS_RZ' ]
	DPAD = {
		'DPAD_LEFT' : ('ABS_HAT0X', 0, -32767),
		'DPAD_RIGHT' : ('ABS_HAT0X', 0, 32767),
		'DPAD_UP' : ('ABS_HAT0Y', 0, -32767),
		'DPAD_DOWN' : ('ABS_HAT0Y', 0, 32767),
		
		'LSTICK_LEFT' : ('ABS_X', 0, -32767),
		'LSTICK_RIGHT' : ('ABS_X', 0, 32767),
		'LSTICK_UP' : ('ABS_Y', 0, -32767),
		'LSTICK_DOWN' : ('ABS_Y', 0, 32767),
		
		'RSTICK_LEFT' : ('ABS_RX', 0, -32767),
		'RSTICK_RIGHT' : ('ABS_RX', 0, 32767),
		'RSTICK_UP' : ('ABS_RY', 0, 32767),
		'RSTICK_DOWN' : ('ABS_RY', 0, -32767)
		 }
	MOUSE = [ 'Keys.BTN_LEFT', 'Keys.BTN_MIDDLE', 'Keys.BTN_RIGHT',
		'Rels.REL_WHEEL, 1', 'Rels.REL_WHEEL, -1',
		'Keys.BTN_LEFT', 'Keys.BTN_RIGHT',	# Button 6 and 7, not actually used
		'Keys.BTN_SIDE', 'Keys.BTN_EXTRA' ]
	MODIFIERS = [ Keys.KEY_LEFTCTRL, Keys.KEY_LEFTMETA, Keys.KEY_LEFTALT,
		Keys.KEY_RIGHTALT, Keys.KEY_RIGHTMETA, Keys.KEY_RIGHTCTRL,
		Keys.KEY_LEFTSHIFT, Keys.KEY_RIGHTSHIFT
	]
	
	def __init__(self, app):
		self.app = app
		self.mode = None
		self.id = None
		self.active_mods = []
		self.setup_widgets()
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, "action.glade"))
		self.window = self.builder.get_object("actionEditor")
		self.keygrab = self.builder.get_object("keyGrab")
		self.builder.connect_signals(self)
		
		vbKBorM = self.builder.get_object("vbKBorM")
		self.background = SVGWidget(self.app, os.path.join(self.app.iconpath, self.IMAGE))
		self.background.connect('hover', self.on_background_area_hover)
		self.background.connect('leave', self.on_background_area_hover, None)
		self.background.connect('click', self.on_background_area_click)
		vbKBorM.pack_start(self.background, True, True, 0)
		vbKBorM.show_all()
	
	
	def on_btnGrabKey_clicked(self, *a):
		self.active_mods = []
		self.keygrab.set_transient_for(self.window)
		self.keygrab.set_modal(True)
		self.builder.get_object("lblKey").set_label("...")
		for key in ActionEditor.MODIFIERS:
			self.builder.get_object("tg" + key.name).set_active(False)
		self.keygrab.show()
		self.keygrab.set_focus()
	
	
	def on_background_area_click(self, trash, area):
		entAction = self.builder.get_object("entAction")
		if area in ActionEditor.BUTTONS:
			entAction.set_text("button(Keys.BTN_%s)" % (area,))
			return
		if area in ActionEditor.AXES:
			entAction.set_text("axis(Axes.%s)" % (area,))
			return
		if area in ActionEditor.DPAD:
			entAction.set_text("axis(Axes.%s, %s, %s)" % ActionEditor.DPAD[area])
			return
		if area.startswith("MOUSE"):
			action = ActionEditor.MOUSE[int(area[5:]) - 1]
			if "Rels" in action:
				entAction.set_text("mouse(%s)" % (action,))
			else:
				entAction.set_text("button(%s)" % (action,))
			return
	
	
	def on_background_area_hover(self, trash, area):
		self.background.hilight(area, "#FFFF0000")
	
	
	def on_actionEditor_key_press_event(self, trash, event):
		# Check if pressed key was escape and if yes, close window
		if event.keyval == Gdk.KEY_Escape:
			self.window.destroy()
	
	
	def on_tgkey_toggled(self, obj, *a):
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
		key = keyevent_to_key(event)
		if key is not None:
			if key in ActionEditor.MODIFIERS:
				if key in self.active_mods:
					if len(self.active_mods) == 1:
						# Releasing last modifier
						self.key_grabbed([key])
						return
					self.active_mods.remove(key)
					self.builder.get_object("tg" + key.name).set_active(False)
				self.builder.get_object("lblKey").set_label("+".join([key.name.split("_")[-1] for key in self.active_mods]))
				return
			
			self.key_grabbed(self.active_mods + [key])
	
	
	def on_btOK_clicked(self, *a):
		entAction = self.builder.get_object("entAction")
		action = GuiActionParser(entAction.get_text()).parse()
		self.app.set_action(self.id, action)
		self.window.destroy()
	
	
	def key_grabbed(self, keys):
		entAction = self.builder.get_object("entAction")
		actions = [ 'key(Keys.%s)' % (key.name,) for key in keys ]
		entAction.set_text("; ".join(actions))
		self.keygrab.hide()
	
	
	def set_action(self, action):
		entAction = self.builder.get_object("entAction")
		entAction.set_text(action.string)
	
	
	def set_button(self, button):
		""" Setups action editor as editor for button action """
		self.mode = ActionEditor.MODE_BUTTON
		self.id = button
	
	
	def set_title(self, title):
		self.window.set_title(title)
		self.builder.get_object("header").set_title(title)
	
	
	def show(self, modal_for):
		self.window.set_transient_for(modal_for)
		self.window.set_modal(True)
		self.window.show()

def merge_modifiers(mods):
	return "+".join([ key.name.split("_")[-1] for key in mods ])