#!/usr/bin/python2
from __future__ import unicode_literals

from collections import deque
from scc.uinput import Gamepad, Keyboard, Mouse
from scc.profile import Profile
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import SCStatus, SCButtons, SCI_NULL
from scc.constants import CI_NAMES, ControllerInput
from scc.constants import LEFT, RIGHT, STICK

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
		self.shell_command_callback = None
		
		# Setup emulation
		self.keypress_list = []
		self.keyrelease_list = []
		self.mouse_dq = [ deque(maxlen=8), deque(maxlen=8), deque(maxlen=8), deque(maxlen=8) ] # x, y, wheel, hwheel
		self.mouse_tb = [ False, False ]	# trackball mode for mouse / wheel
		self.syn_list = set()
		self.buttons, self.old_buttons = 0, 0
		self.state, self.old_state = SCI_NULL, SCI_NULL
		self.mouse_movements = [ None, None, None, None ]
		self.force_event = set()
	
	
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
	
	
	def is_touched(self, what):
		"""
		Returns True if specified pad is being touched.
		May randomly return False for aphephobic pads.
		
		'what' should be LEFT or RIGHT (from scc.constants)
		"""
		if what == LEFT:
			return self.buttons & SCButtons.LPADTOUCH
		else: # what == RIGHT
			return self.buttons & SCButtons.RPADTOUCH
	
	
	def was_touched(self, what):
		"""
		As is_touched, but returns True if pad *was* touched
		in previous known state.
		
		This is used as:
		is_touched() and not was_touched() -> pad was just pressed
		not is_touched() and was_touched() -> pad was just released
		"""
		if what == LEFT:
			return self.old_buttons & SCButtons.LPADTOUCH
		else: # what == RIGHT
			return self.old_buttons & SCButtons.RPADTOUCH
	
	
	def is_pressed(self, button):
		"""
		Returns True if button is pressed
		"""
		return self.buttons & button
	
	
	def was_pressed(self, button):
		"""
		Returns True if button was pressed in previous known state
		"""
		return self.old_buttons & button
	
	
	def callback(self, controller, time, sci):
		# Store state
		if sci.status != SCStatus.INPUT:
			return
		self.old_state = self.state
		self.old_buttons = self.buttons

		self.state = sci
		self.buttons = sci.buttons
		
		if self.buttons & SCButtons.LPAD and not self.buttons & SCButtons.LPADTOUCH:
			self.buttons = (self.buttons & ~SCButtons.LPAD) | SCButtons.STICK
		
		fe = self.force_event
		self.force_event = set()
		
		# Check buttons
		xor = self.old_buttons ^ self.buttons
		btn_rem = xor & self.old_buttons
		btn_add = xor & self.buttons
		
		try:
			if btn_add or btn_rem:
				# At least one button was pressed
				for x in self.profile.buttons:
					if x & btn_add:
						self.profile.buttons[x].button_press(self)
					elif x & btn_rem:
						self.profile.buttons[x].button_release(self)
			
			
			# Check stick
			if not self.buttons & SCButtons.LPADTOUCH:
				if FE_STICK in fe or self.old_state.lpad_x != sci.lpad_x or self.old_state.lpad_y != sci.lpad_y:
					self.profile.stick.whole(self, sci.lpad_x, sci.lpad_y, STICK)
			
			# Check triggers
			if FE_TRIGGER in fe or sci.ltrig != self.old_state.ltrig:
				if LEFT in self.profile.triggers:
					self.profile.triggers[LEFT].trigger(self, sci.ltrig, self.old_state.ltrig)
			if FE_TRIGGER in fe or sci.rtrig != self.old_state.rtrig:
				if RIGHT in self.profile.triggers:
					self.profile.triggers[RIGHT].trigger(self, sci.rtrig, self.old_state.rtrig)
			
			# Check pads
			if FE_PAD in fe or self.buttons & SCButtons.RPADTOUCH or SCButtons.RPADTOUCH & btn_rem:
				# RPAD
				self.profile.pads[RIGHT].whole(self, sci.rpad_x, sci.rpad_y, RIGHT)
			
			if (FE_PAD in fe and self.buttons & SCButtons.LPADTOUCH) or self.buttons & SCButtons.LPADTOUCH or SCButtons.LPADTOUCH & btn_rem:
				# LPAD
				self.profile.pads[LEFT].whole(self, sci.lpad_x, sci.lpad_y, LEFT)
		except Exception, e:
			# Log error but don't crash here, it breaks too many things at once
			log.error("Error while processing controller event")
			log.error(traceback.format_exc())
		
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
