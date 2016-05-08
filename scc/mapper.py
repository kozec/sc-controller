#!/usr/bin/python2
from __future__ import unicode_literals

from collections import deque
from scc.uinput import Gamepad, Keyboard, Mouse, Rels
from scc.constants import SCStatus, SCButtons, SCI_NULL
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import CI_NAMES, ControllerInput
from scc.constants import LEFT, RIGHT, STICK, GYRO
from scc.profile import Profile


import traceback, logging, time
log = logging.getLogger("Mapper")

class Mapper(object):
	DEBUG = False
	
	def __init__(self, profile):
		self.profile = profile
		self.controller = None
		
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
		self.mouse_tb = [ False, False ]		# trackball mode for mouse / wheel
		self.mouse_feedback = [ None, None ]	# for mouse / wheel
		self.travelled = [ 0, 0 ]				# for mouse / wheel, used when generating "rolling ball" feedback
		self.syn_list = set()
		self.scheduled_tasks = []
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
	
	
	def set_controller(self, c):
		""" Sets controller device, used by some (one so far) actions """
		self.controller = c
	
	
	def get_controller(self):
		""" Returns assigned controller device or None if no controller is set """
		return self.controller
	
	
	def send_feedback(self, hapticdata):
		""" Sends haptic feedback to controller """
		if self.controller is None:
			log.warning("Trying to add feedback while controller instance is not set")
		else:
			self.controller.addFeedback(*hapticdata.data)
	
	
	def schedule(self, delay, cb):
		"""
		Schedules callback to be ran no sooner than after 'delay's.
		Callback is called with mapper as only argument.
		"""
		when = time.time() + delay
		self.scheduled_tasks.append( (when, cb) )
		self.scheduled_tasks.sort(key=lambda a: a[0])
	
	
	def mouse_dq_clear(self, *axes):
		""" Used by trackpad, trackball and mouse wheel emulation """
		for axis in axes:
			self.mouse_dq[axis].clear()
	
	
	def mouse_dq_add(self, axis, position, speed, hapticdata):
		""" Used by trackpad, trackball and mouse wheel emulation """
		t = self.mouse_movements[axis]
		if t is None:
			try:
				prev = int(sum(self.mouse_dq[axis]) / len(self.mouse_dq[axis]))
			except ZeroDivisionError:
				prev = position
			t = self.mouse_movements[axis] = [ prev, 0, False ]
		self.mouse_dq[axis].append(position)
		if axis >= 2:	# 2 - wheel, 3 - horisontal wheel
			self.mouse_feedback[1] = hapticdata
		else:
			self.mouse_feedback[0] = hapticdata
		
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
	
	
	def callback(self, controller, now, sci):
		# Store state
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
			
			# Check gyro
			if controller.getGyroEnabled():
				self.profile.gyro.gyro(self, sci.gpitch, sci.gyaw, sci.groll, sci.q1, sci.q2, sci.q3, sci.q4)
			
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
		
		if len(self.scheduled_tasks) > 0 and self.scheduled_tasks[0][0] <= now:
			cb = self.scheduled_tasks[0][1]
			self.scheduled_tasks = self.scheduled_tasks[1:]
			cb(self)
		
		
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
			self.travelled[0] += self.mouse.moveEvent(mx, my * -1, False)
			self.syn_list.add(self.mouse)
			self.mouse_movements[0] = self.mouse_movements[1] = None
		if wx != 0 or wy != 0:
			if self.mouse.scrollEvent(wx, wy, False):
				# Returns True
				self.travelled[1] += 500
			self.syn_list.add(self.mouse)
			self.mouse_movements[2] = self.mouse_movements[3] = None
		# Generate events - trackball
		if self.mouse_tb[0]:
			dist = self.mouse.moveEvent(0, 0, True)
			self.syn_list.add(self.mouse)
			if dist:
				self.travelled[0] += dist
			else:
				self.mouse_tb[0] = False
				self.mouse_feedback[0] = None
		
		if self.mouse_tb[1]:
			dist = self.mouse.scrollEvent(0, 0, True)
			self.syn_list.add(self.mouse)
			if dist:
				# scrollEvent returns True, not number
				self.travelled[1] += 500
			else:
				self.mouse_tb[1] = False
				self.mouse_feedback[1] = None
		
		for i in (0, 1):
			if self.mouse_feedback[i]:
				# print i, self.travelled[i], self.mouse_feedback[i].frequency
				if self.travelled[i] > self.mouse_feedback[i].frequency:
					self.travelled[i] -= self.mouse_feedback[i].frequency
					self.send_feedback(self.mouse_feedback[i])
		
		
		self.sync()
