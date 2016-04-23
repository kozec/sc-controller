#!/usr/bin/python2
from __future__ import unicode_literals

from collections import deque
from scc.uinput import Gamepad, Keyboard, Mouse
from scc.profile import Profile
from scc.events import ButtonPressEvent, ButtonReleaseEvent, StickEvent
from scc.events import PadEvent, TriggerEvent
from scc.events import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import SCStatus, SCButtons, SCI_NULL
from scc.constants import CI_NAMES, ControllerInput

import traceback, logging
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
			friction=0.1, # Mouse.DEFAULT_SCR_FRICTION
			xscale=Mouse.DEFAULT_SCR_XSCALE,
			yscale=Mouse.DEFAULT_SCR_XSCALE
		)
		
		# Set some stuff to None just to have it overriden
		# by SCCDaemon class
		self.change_profile_callback = None
		
		# Setup emulation
		self.keypress_list = []
		self.keyrelease_list = []
		self.mouse_dq = [ deque(maxlen=8), deque(maxlen=8), deque(maxlen=8), deque(maxlen=8) ] # x, y, wheel, hwheel
		self.mouse_tb = [ False, False ]	# trackball mode for mouse / wheel
		self.syn_list = set()
		self.old_state = SCI_NULL
		self.state = SCI_NULL
		self.mouse_movements = [ None, None, None, None ]
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
		""" Syncs generated events """
		if len(self.syn_list):
			for dev in self.syn_list:
				dev.synEvent()
			self.syn_list = set()
	
	
	def mouse_dq_clear(self, *axes):
		""" Used by trackpad, trackball and mouse wheel emulation """
		for axis in axes:
			self.mouse_dq[axis].clear()
	
	
	def mouse_dq_add(self, axis, position, speed):
		""" Used by trackpad, trackball and mouse wheel emulation """
		t = self.mouse_movements[axis]
		if t is None:
			try:
				prev = int(sum(self.mouse_dq[axis]) / len(self.mouse_dq[axis]))
			except ZeroDivisionError:
				prev = position
			t = self.mouse_movements[axis] = [ prev, 0, False ]
		self.mouse_dq[axis].append(position)
		
		try:
			t[1] = int(sum(self.mouse_dq[axis]) / len(self.mouse_dq[axis]))
		except ZeroDivisionError:
			t[1] = 0
	
	
	def do_trackball(self, move_or_wheel, stop=False):
		""" Used to continue mouse movement when user presses or releases pad """
		self.mouse_tb[move_or_wheel] = not stop
	
	
	def _get_mouse_movement(self, axis):
		if self.mouse_movements[axis] is None:
			return 0
		return self.mouse_movements[axis][1] - self.mouse_movements[axis][0]
	
	
	def callback(self, controller, sci):
		# Store state
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
		
		if (FE_PAD in fe and sci.buttons & SCButtons.LPADTOUCH) or sci.buttons & SCButtons.LPADTOUCH or SCButtons.LPADTOUCH & btn_rem:
			# LPAD
			if Profile.WHOLE in self.profile.pads[Profile.LEFT]:
				self.profile.pads[Profile.LEFT][Profile.WHOLE].execute(self.lpe[Profile.WHOLE])
			else:
				for x in Profile.LPAD_AXES:
					if x in self.profile.pads[Profile.LEFT]:
						self.profile.pads[Profile.LEFT][x].execute(self.lpe[x])
		
		
		# Generate events - keys
		if len(self.keypress_list):
			self.keyboard.pressEvent(self.keypress_list)
			self.keypress_list = []
		if len(self.keyrelease_list):
			self.keyboard.releaseEvent(self.keyrelease_list)
			self.keyrelease_list = []
		# Generate events - mouse
		mx, my = self._get_mouse_movement(0), self._get_mouse_movement(1)
		wx, wy = self._get_mouse_movement(2), self._get_mouse_movement(3)
		if mx != 0 or my != 0:
			self.mouse.moveEvent(mx, my * -1, False)
			self.syn_list.add(self.mouse)
			self.mouse_movements[0] = self.mouse_movements[1] = None
		if wx != 0 or wy != 0:
			self.mouse.scrollEvent(wx, wy, False)
			self.syn_list.add(self.mouse)
			self.mouse_movements[2] = self.mouse_movements[3] = None
		# Generate events - trackball
		if self.mouse_tb[0]:
			dist = self.mouse.moveEvent(0, 0, True)
			self.syn_list.add(self.mouse)
			if not dist:
				self.mouse_tb[0] = False
		if self.mouse_tb[1]:
			dist = self.mouse.scrollEvent(0, 0, True)
			self.syn_list.add(self.mouse)
			if not dist:
				self.mouse_tb[1] = False
		self.sync()
