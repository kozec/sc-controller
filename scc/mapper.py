#!/usr/bin/python2
from __future__ import unicode_literals

import traceback
from scc.uinput import Gamepad, Keyboard, Mouse
from scc.profile import Profile
from scc.events import ButtonPressEvent, ButtonReleaseEvent, StickEvent
from scc.events import PadEvent, TriggerEvent
from scc.events import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import SCStatus, SCButtons, SCI_NULL
from scc.constants import CI_NAMES, ControllerInput

import logging
log = logging.getLogger("Mapper")

class Mapper(object):
	DEBUG = False
	
	def __init__(self, profile):
		self.profile = profile
		
		# Create virtual devices
		log.debug("Creating virtual devices")
		self.gamepad = Gamepad()
		log.debug("Gamepad:  %s" % (self.gamepad, ))
		self.keyboard = Keyboard()
		log.debug("Keyboard: %s" % (self.keyboard, ))
		self.mouse = Mouse()
		log.debug("Mouse:    %s" % (self.mouse, ))
		self.mouse.updateParams(
			friction=Mouse.DEFAULT_FRICTION,
			xscale=Mouse.DEFAULT_XSCALE,
			yscale=Mouse.DEFAULT_YSCALE)
		self.mouse.updateScrollParams(
			friction=Mouse.DEFAULT_SCR_FRICTION,
			xscale=Mouse.DEFAULT_SCR_XSCALE,
			yscale=Mouse.DEFAULT_SCR_XSCALE
		)
		
		# Set emulation
		self.keypress_list = []
		self.keyrelease_list = []
		self.syn_list = set()
		self.old_state = SCI_NULL
		self.state = SCI_NULL
		self.force_event = set()
		self.bpe =					ButtonPressEvent(self)
		self.bre =					ButtonReleaseEvent(self)
		self.se  = { x :			StickEvent(self, Profile.STICK_AXES[x], None, SCButtons.LPAD) for x in Profile.STICK_AXES }
		self.lpe = { x :			PadEvent(self, Profile.LPAD_AXES[x], None, SCButtons.LPAD, SCButtons.LPADTOUCH) for x in Profile.LPAD_AXES }
		self.rpe = { x :			PadEvent(self, Profile.RPAD_AXES[x], None, SCButtons.RPAD, SCButtons.RPADTOUCH) for x in Profile.RPAD_AXES }
		self.se[Profile.WHOLE]  =	StickEvent(self, "lpad_x", "lpad_y", SCButtons.LPAD)
		self.lpe[Profile.WHOLE] =	PadEvent(self, "lpad_x", "lpad_y", SCButtons.LPAD, SCButtons.LPADTOUCH)
		self.rpe[Profile.WHOLE] =	PadEvent(self, "rpad_x", "rpad_y", SCButtons.RPAD, SCButtons.RPADTOUCH)
		self.lte = 					TriggerEvent(self, "ltrig")
		self.rte = 					TriggerEvent(self, "rtrig")
	
	
	def sync(self):
		# Syncs generated events
		if len(self.syn_list):
			for dev in self.syn_list:
				dev.synEvent()
			self.syn_list = set()
	
	
	def callback(self, controller, sci):
		# Store state
		#print sci
		if sci.status != SCStatus.INPUT:
			return
		self.old_state = self.state
		self.state = sci
		fe = self.force_event
		self.force_event = set()
		
		# Check buttons
		xor = self.old_state.buttons ^ sci.buttons
		btn_rem = xor & self.old_state.buttons
		btn_add = xor & sci.buttons
		
		if btn_add or btn_rem:
			# At least one button was pressed
			for x in self.profile.buttons:
				if x & btn_add:
					self.profile.buttons[x].execute(self.bpe)
				elif x & btn_rem:
					self.profile.buttons[x].execute(self.bre)
		
		# Check stick
		if not sci.buttons & SCButtons.LPADTOUCH:
			if FE_STICK in fe or self.old_state.lpad_x != sci.lpad_x or self.old_state.lpad_y != sci.lpad_y:
				# STICK
				if Profile.WHOLE in self.profile.stick:
					self.profile.stick[Profile.WHOLE].execute(self.se[Profile.WHOLE])
				else:
					for x in Profile.STICK_AXES:
						if x in self.profile.stick:
							self.profile.stick[x].execute(self.se[x])
		
		# Check triggers
		if FE_TRIGGER in fe or sci.ltrig != self.old_state.ltrig:
			if Profile.LEFT in self.profile.triggers:
				self.profile.triggers[Profile.LEFT].execute(self.lte)
		if FE_TRIGGER in fe or sci.rtrig != self.old_state.rtrig:
			if Profile.RIGHT in self.profile.triggers:
				self.profile.triggers[Profile.RIGHT].execute(self.rte)
		
		# Check pads
		if FE_PAD in fe or sci.buttons & SCButtons.RPADTOUCH or SCButtons.RPADTOUCH & btn_rem:
			# RPAD
			if Profile.WHOLE in self.profile.pads[Profile.RIGHT]:
				self.profile.pads[Profile.RIGHT][Profile.WHOLE].execute(self.rpe[Profile.WHOLE])
			else:
				for x in Profile.RPAD_AXES:
					if x in self.profile.pads[Profile.RIGHT]:
						self.profile.pads[Profile.RIGHT][x].execute(self.rpe[x])
		
		if FE_PAD in fe or sci.buttons & SCButtons.LPADTOUCH or SCButtons.LPADTOUCH & btn_rem:
			# LPAD
			if Profile.WHOLE in self.profile.pads[Profile.LEFT]:
				self.profile.pads[Profile.LEFT][Profile.WHOLE].execute(self.lpe[Profile.WHOLE])
			else:
				for x in Profile.LPAD_AXES:
					if x in self.profile.pads[Profile.LEFT]:
						self.profile.pads[Profile.LEFT][x].execute(self.lpe[x])
		
		
		# Generate events
		if len(self.keypress_list):
			self.keyboard.pressEvent(self.keypress_list)
			self.keypress_list = []
		if len(self.keyrelease_list):
			self.keyboard.releaseEvent(self.keyrelease_list)
			self.keyrelease_list = []
		self.sync()
