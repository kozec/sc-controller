#!/usr/bin/python2
"""
SC-Controller - Slave Mapper

Mapper that is hooked to scc-daemon instance through socket instead of
using libusb directly.

Used by on-screen keyboard.
"""
from __future__ import unicode_literals

from collections import deque
from scc.constants import SCButtons, LEFT, RIGHT, STICK, TRIGGER_MAX
from scc.mapper import Mapper


import logging, time
log = logging.getLogger("SlaveMapper")

class SlaveMapper(Mapper):
	def __init__(self, profile, keyboard=b"SCController Keyboard", mouse=None):
		Mapper.__init__(self, profile, keyboard, mouse, None)
	
	def set_controller(self, c):
		""" Sets controller device, used by some (one so far) actions """
		raise TypeError("SlaveMapper doesn't connect to controller device")
	
	
	def get_controller(self):
		""" Returns assigned controller device or None if no controller is set """
		raise TypeError("SlaveMapper doesn't connect to controller device")
	
	
	def run_scheduled(self):
		"""
		Should be called periodically to keep timers going.
		Since SlaveMapper doesn't communicate with controller device, it is not
		possible to drive this automatically
		"""
		now = time.time()
		if len(self.scheduled_tasks) > 0 and self.scheduled_tasks[0][0] <= now:
			cb = self.scheduled_tasks[0][1]
			self.scheduled_tasks = self.scheduled_tasks[1:]
			cb(self)
	
	
	def handle_event(self, daemon, what, data):
		"""
		Handles event sent by scc-daemon.
		Without calling this, SlaveMapper basically does nothing.
		"""
		if what == STICK:
			self.profile.stick.whole(self, data[0], data[1], what)
		elif what == SCButtons.LT.name:
			self.profile.triggers[LEFT].trigger(self, *data)
		elif what == SCButtons.RT.name:
			self.profile.triggers[RIGHT].trigger(self, *data)
		elif hasattr(SCButtons, what) or what == "STICKPRESS":
			if what == "STICKPRESS":
				x = SCButtons.STICK
			else:
				x = getattr(SCButtons, what)
			self.old_buttons = self.buttons
			if data[0]:
				# Pressed
				self.buttons = self.buttons | x
				self.profile.buttons[x].button_press(self)
			else:
				self.buttons = self.buttons & ~x
				self.profile.buttons[x].button_release(self)
		elif what in (LEFT, RIGHT):
			self.profile.pads[what].whole(self, data[0], data[1], what)
		else:
			print ">>>", what, data
		self.generate_events()
