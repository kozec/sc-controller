#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""

from scc.tools import _

from scc.gui.controller_widget import ControllerButton
from scc.gui.gdk_to_key import keyevent_to_key
from scc.gui.editor import Editor
from scc.actions import Action, ButtonAction, NoAction
from scc.macros import Macro, Repeat, SleepAction, PressAction, ReleaseAction
from scc.modifiers import ModeModifier
from scc.constants import SCButtons
from scc.profile import Profile
from scc.uinput import Keys

from gi.repository import Gtk, Gdk, GLib
import os, logging
log = logging.getLogger("KeyGrabber")

MODIFIERS = [ Keys.KEY_LEFTCTRL, Keys.KEY_LEFTMETA, Keys.KEY_LEFTALT,
	Keys.KEY_RIGHTALT, Keys.KEY_RIGHTMETA, Keys.KEY_RIGHTCTRL,
	Keys.KEY_LEFTSHIFT, Keys.KEY_RIGHTSHIFT
]


def merge_modifiers(mods):
	return "+".join([ key.name.split("_")[-1] for key in mods ])


# Just to speed shit up, KeyGrabber is singleton
class KeyGrabber(object):
	GLADE = "key_grabber.glade"
	_singleton = None
	
	def __new__(cls, *a):
		if cls._singleton is None:
			cls._singleton = object.__new__(cls, *a)
		return cls._singleton
	
	
	def __init__(self, app):
		self.app = app
		self.builder = None
		self.active_mods = []
	
	
	def grab(self, modal_for, action, callback):
		if self.builder is None:
			self.setup_widgets()
		self.callback = callback
		self.builder.get_object("lblKey").set_label("...")
		# TODO: Display 'action' in lblKey if possible
		for key in MODIFIERS:
			self.builder.get_object("tg" + key.name).set_active(False)
		self.active_mods = []
		self.window.set_transient_for(modal_for)
		self.window.set_modal(True)
		self.window.show()
		self.window.set_focus()
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.window = self.builder.get_object("KeyGrab")
		self.builder.connect_signals(self)
	
	
	def on_KeyGrab_destroy(self, *a):
		# Don't allow destroying
		return True
	
	
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
		
		if key in MODIFIERS:
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
		
		Calls callback if key is accepted
		"""
		key = keyevent_to_key(event)
		if key is not None:
			if key in MODIFIERS:
				if key in self.active_mods:
					if len(self.active_mods) == 1:
						# Releasing last modifier
						self.callback([key])
						self.window.hide()
						return
					self.active_mods.remove(key)
					self.builder.get_object("tg" + key.name).set_active(False)
				self.builder.get_object("lblKey").set_label("+".join([key.name.split("_")[-1] for key in self.active_mods]))
				return
			
			self.callback(self.active_mods + [key])
			self.window.hide()
	
	
	def on_tgkey_toggled(self, obj, *a):
		"""
		Handles when user clicks on modifier buttons in "Grab Key" dialog
		"""
		for key in MODIFIERS:
			if self.builder.get_object("tg" + key.name) == obj:
				if obj.get_active() and not key in self.active_mods:
					self.active_mods.append(key)
					self.builder.get_object("lblKey").set_label(merge_modifiers(self.active_mods))
				elif not obj.get_active() and key in self.active_mods:
					self.active_mods.remove(key)
					self.builder.get_object("lblKey").set_label(merge_modifiers(self.active_mods))
				return
