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
from scc.gui.svg_widget import SVGWidget, SVGEditor
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
		self._controller_image = None
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
	
	
	def load_buttons(self):
		cbControllerButtons = self.builder.get_object("cbControllerButtons")
		self._groups = {}
		model = cbControllerButtons.get_model()
		groups = json.loads(open(os.path.join(self.app.imagepath,
			"button-images", "groups.json"), "r").read())
		for group in groups:
			images = [ GdkPixbuf.Pixbuf.new_from_file(os.path.join(
				self.app.imagepath, "button-images", "%s.svg" % (b, )))
				for b in group['buttons'][0:4] ]
			model.append( [group['key']] + images )
			self._groups[group['key']] = group['buttons']
		cbControllerButtons.set_active(0)
	
	
	def on_btNext_clicked(self, button):
		stDialog = self.builder.get_object("stDialog")
		pages = stDialog.get_children()
		index = pages.index(stDialog.get_visible_child())
		if index == 0:
			stDialog.set_visible_child(pages[1])
			self.load_buttons()
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
	
	
	def fill_button_images(self, image, buttons):
		BUTTONS = [ "A", "B", "X", "Y", "BACK", "C", "START" ]
		e = image.edit()
		SVGEditor.update_parents(e)
		target = SVGEditor.get_element(e, "controller")
		for i in xrange(len(BUTTONS)):
			b = BUTTONS[i]
			try:
				elm = SVGEditor.get_element(e, "AREA_%s" % (b,))
				x, y = SVGEditor.get_position(elm)
				path = os.path.join(self.app.imagepath, "button-images",
					"%s.svg" % (buttons[i], ))
				img = SVGEditor.get_element(SVGEditor.load_from_file(path), "button")
				img.attrib["transform"] = "translate(%s, %s)" % (x, y)
				del img.attrib["id"]
				SVGEditor.add_element(target, img)
			except Exception, err:
				log.warning("Failed to add image for button %s", b)
				log.exception(err)
		e.commit()
	
	
	def refresh_controller_image(self, *a):
		cbControllerButtons = self.builder.get_object("cbControllerButtons")
		imgControllerType = self.builder.get_object("imgControllerType")
		cbControllerType = self.builder.get_object("cbControllerType")
		rvControllerType = self.builder.get_object("rvControllerType")
		
		group = cbControllerButtons.get_model()[cbControllerButtons.get_active()][0]
		controller = cbControllerType.get_model()[cbControllerType.get_active()][0]
		
		image = os.path.join(self.app.imagepath,
			"controller-images/%s.svg" % (controller, ))
		if self._controller_image:
			self._controller_image.set_image(image)
			self.fill_button_images(self._controller_image, self._groups[group])
			self._controller_image.hilight({})
		else:
			self._controller_image = SVGWidget(self.app, image)
			rvControllerType.add(self._controller_image)
		rvControllerType.set_reveal_child(True)
