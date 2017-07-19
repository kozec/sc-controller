#!/usr/bin/env python2
"""
SC-Controller - Controller Registration 

Dialog that asks a lot of question to create configuration node in config file.
Most "interesting" thing here may be that this works 100% independently from
daemon.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import GdkPixbuf
from scc.gui.editor import Editor

import evdev
import sys, os, logging, json, traceback
log = logging.getLogger("CR")

class ControllerRegistration(Editor):
	GLADE = "controller_registration.glade"
	
	def __init__(self, app):
		Editor.__init__(self)
		self.app = app
		self.setup_widgets()
		self._gamepad_icon = GdkPixbuf.Pixbuf.new_from_file(
				os.path.join(self.app.imagepath, "controller-icons", "evdev-0.svg"))
		self._other_icon = GdkPixbuf.Pixbuf.new_from_file(
				os.path.join(self.app.imagepath, "controller-icons", "unknown.svg"))
		self.refresh_devices()
	
	
	@staticmethod
	def does_he_looks_like_a_gamepad(dev):
		"""
		Examines device capabilities and decides if it passes for gamepad.
		Device is considered gamepad-like if has at least 'A' button and at
		least two axes.
		"""
		# ... but some cheating first
		if "keyboard" in dev.name.lower():
			return False
		if "mouse" in dev.name.lower():
			return False
		if "gamepad" in dev.name.lower():
			return True
		caps = dev.capabilities(verbose=False)
		if evdev.ecodes.EV_ABS in caps: # Has axes
			if evdev.ecodes.EV_KEY in caps: # Has buttons
				for button in caps[evdev.ecodes.EV_KEY]:
					if button >= evdev.ecodes.BTN_0 and button <= evdev.ecodes.BTN_GEAR_UP:
						return True
		return False
	
	
	def on_btNext_clicked(self, button):
		stDialog = self.builder.get_object("stDialog")
		pages = stDialog.get_children()
		index = pages.index(stDialog.get_visible_child())
		if index == 0:
			stDialog.set_visible_child(pages[1])
			self.refresh_controller_image()
			button.set_sensitive(False)
	
	
	def refresh_devices(self, *a):
		lstDevices = self.builder.get_object("lstDevices")
		cbShowAllDevices = self.builder.get_object("cbShowAllDevices")
		lstDevices.clear()
		for fname in evdev.list_devices():
			dev = evdev.InputDevice(fname)
			is_gamepad = ControllerRegistration.does_he_looks_like_a_gamepad(dev)
			if not dev.phys:
				# Skipping over virtual devices so list doesn't show
				# gamepads emulated by SCC
				continue
			if is_gamepad or cbShowAllDevices.get_active():
				lstDevices.append(( fname, dev.name,
					self._gamepad_icon if is_gamepad else self._other_icon ))
	
	
	def refresh_controller_image(self, *a):
		cbControllerType = self.builder.get_object("cbControllerType")
		imgControllerType = self.builder.get_object("imgControllerType")
		rvControllerType = self.builder.get_object("rvControllerType")
		image_path = os.path.join(self.app.imagepath,
			"controller-images/%s.svg" % (
			cbControllerType.get_model()[cbControllerType.get_active()][0],)
		)
		imgControllerType.set_from_file(image_path)
		rvControllerType.set_reveal_child(True)
