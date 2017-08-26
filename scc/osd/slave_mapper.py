#!/usr/bin/python2
"""
SC-Controller - Slave Mapper

Mapper that is hooked to scc-daemon instance through socket instead of
using libusb directly. Relies to Observe or Lock message being sent by client.

Used by on-screen keyboard.
"""
from __future__ import unicode_literals

from collections import deque
from scc.constants import SCButtons, LEFT, RIGHT, STICK, TRIGGER_MAX
from scc.mapper import Mapper

import logging, time
log = logging.getLogger("SlaveMapper")

class SlaveMapper(Mapper):
	def __init__(self, profile, keyboard=b"SCC OSD Keyboard", mouse=None):
		Mapper.__init__(self, profile, keyboard, mouse, None)
		self._feedback_cb = None
	
	
	def set_controller(self, c):
		""" Sets controller device, used by some (one so far) actions """
		raise TypeError("SlaveMapper doesn't connect to controller device")
	
	
	def get_controller(self):
		""" Returns assigned controller device or None if no controller is set """
		raise TypeError("SlaveMapper doesn't connect to controller device")
	
	
	def set_feedback_callback(self, cb):
		"""
		Sets callback called to process haptic feedback effects.
		
		If callback is set, it's called as callback(hapticdata) every time
		when feedback would happen normally.
		
		Callback is used here instead of signal so this module doesn't
		depends on GLib
		"""
		self._feedback_cb = cb
	
	
	def send_feedback(self, hapticdata):
		"""
		Simply calls self._feedback_cb, if set. See docstring above.
		"""
		if self._feedback_cb:
			self._feedback_cb(hapticdata)
	
	
	def run_scheduled(self):
		"""
		Should be called periodically to keep timers going.
		Since SlaveMapper doesn't communicate with controller device, it is not
		possible to drive this automatically
		"""
		now = time.time()
		Mapper.run_scheduled(self, now)
		return True
	
	
	def handle_event(self, daemon, what, data):
		"""
		Handles event sent by scc-daemon.
		Without calling this, SlaveMapper basically does nothing.
		"""
		self.old_buttons = self.buttons
		if what == STICK:
			self.profile.stick.whole(self, data[0], data[1], what)
		elif what == SCButtons.LT.name:
			self.profile.triggers[LEFT].trigger(self, *data)
		elif what == SCButtons.RT.name:
			self.profile.triggers[RIGHT].trigger(self, *data)
		elif hasattr(SCButtons, what) or what == "STICKPRESS":
			if what == "STICKPRESS":
				x = SCButtons.STICKPRESS
			else:
				x = getattr(SCButtons, what)
			if data[0]:
				# Pressed
				self.buttons = self.buttons | x
				self.profile.buttons[x].button_press(self)
			else:
				self.buttons = self.buttons & ~x
				self.profile.buttons[x].button_release(self)
				if what == "LPADTOUCH":
					self.profile.pads[LEFT].whole(self, 0, 0, LEFT)
				elif what == "RPADTOUCH":
					self.profile.pads[RIGHT].whole(self, 0, 0, RIGHT)
		elif what in (LEFT, RIGHT):
			self.profile.pads[what].whole(self, data[0], data[1], what)
		else:
			print ">>>", what, data
		self.generate_events()
