#!/usr/bin/python2
from __future__ import unicode_literals

from collections import deque
from scc.lib import xwrappers as X
from scc.uinput import UInput, Keyboard, Mouse, Dummy, Rels
from scc.constants import SCButtons, LEFT, RIGHT, STICK, STICK_TILT
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD, GYRO
from scc.constants import HapticPos, ALL_AXES, ALL_BUTTONS
from scc.controller import HapticData
from scc.actions import ButtonAction
from scc.config import Config
from scc.profile import Profile


import traceback, logging, time, os
log = logging.getLogger("Mapper")

class Mapper(object):
	DEBUG = False
	
	def __init__(self, profile, keyboard=b"SCController Keyboard",
				mouse=b"SCController Mouse",
				gamepad=True, poller=None):
		"""
		If any of keyboard, mouse or gamepad is set to None, that device
		will not be emulated.
		If poller is set to instance, emulated gamepad will have rumble enabled.
		"""
		self.profile = profile
		self.controller = None
		self.xdisplay = None
		
		# Create virtual devices
		log.debug("Creating virtual devices")
		self.keyboard = Keyboard(name=keyboard) if keyboard else Dummy()
		log.debug("Keyboard: %s" % (self.keyboard, ))
		self.mouse = Mouse(name=mouse) if mouse else Dummy()
		log.debug("Mouse:    %s" % (self.mouse, ))
		self.gamepad = self._create_gamepad(gamepad, poller)
		log.debug("Gamepad:  %s" % (self.gamepad, ))
		
		# Set by SCCDaemon instance; Used to handle actions
		# from scc.special_actions
		self._sa_handler = None
		
		# Setup emulation
		self.keypress_list = []
		self.keyrelease_list = []
		self.mouse_movements = [0, 0, 0, 0]		# mouse x, y, wheel vertical, horisontal
		self.feedbacks = [ None, None ]			# left, right
		self.pressed = {}						# for ButtonAction, holds number of times virtual button was pressed without releasing it first
		self.syn_list = set()
		self.scheduled_tasks = []
		self.buttons, self.old_buttons = 0, 0
		self.lpad_touched = False
		self.state, self.old_state = None, None
		self.force_event = set()
	
	
	def _create_gamepad(self, enabled, poller):
		""" Parses gamepad configuration and creates apropriate unput device """
		if not enabled or "SCC_NOGAMEPAD" in os.environ:
			# Completly undocumented and for debuging purposes only.
			# If set, no gamepad is emulated
			self.gamepad = Dummy()
			return
		cfg = Config()
		keys = ALL_BUTTONS[0:cfg["output"]["buttons"]]
		vendor = int(cfg["output"]["vendor"], 16)
		product = int(cfg["output"]["product"], 16)
		version = int(cfg["output"]["version"], 16)
		name = cfg["output"]["name"]
		axes = []
		i = 0
		for min, max in cfg["output"]["axes"]:
			fuzz, flat = 0, 0
			if abs(max - min) > 32768:
				fuzz, flat = 16, 128
			try:
				axes.append(( ALL_AXES[i], min, max, fuzz, flat ))
			except IndexError:
				# Out of axes
				break
			i += 1
		
		ui = UInput(vendor=vendor, product=product, version=version,
			name=name, keys=keys, axes=axes, rels=[], rumble=(poller != None))
		if poller:
			poller.register(ui.getDescriptor(), poller.POLLIN, self._rumble_ready)
		return ui
	
	
	def _rumble_ready(self, fd, event):
		ef = self.gamepad.ff_read()
		if ef:	# tale of...
			if not ef.playing and ef.repetitions > 0:
				ef.playing = True
				self.send_feedback(HapticData(
					HapticPos.BOTH,
					period = 32760,
					amplitude = 1024,
					count = ef.duration * ef.repetitions / 30
				))	
	
	
	def get_gamepad_name(self):
		"""
		Returns name of emulated gamepad (as displayed by jstest & co)
		or None if Dummy is assigned.
		"""
		if isinstance(self.gamepad, Dummy):
			return None
		return self.gamepad.name
	
	
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
	
	
	def set_special_actions_handler(self, sa):
		self._sa_handler = sa
	
	
	def get_special_actions_handler(self):
		return self._sa_handler
	
	
	def set_xdisplay(self, x):
		self.xdisplay = x
	
	
	def get_xdisplay(self):
		return self.xdisplay
	
	
	def get_current_window(self):
		"""
		Returns window id of current window or None if xdisplay is not set
		"""
		if self.xdisplay:
			return X.get_current_window(self.xdisplay)
		return None
	
	
	def schedule(self, delay, cb):
		"""
		Schedules callback to be ran no sooner than after delay.
		Delay is float number in seconds.
		Callback is called with mapper as only argument.
		"""
		when = time.time() + delay
		self.scheduled_tasks.append( (when, cb) )
		self.scheduled_tasks.sort(key=lambda a: a[0])
	
	
	def remove_scheduled(self, cb):
		""" Removes scheduled task by callback. """
		self.scheduled_tasks = [
			(w, c) for (w, c) in self.scheduled_tasks if cb != c
		]
	
	
	def mouse_move(self, dx, dy):
		"""
		Schedules mouse movement to be done at end of processing callback.
		Called from actions while callback is being processed.
		"""
		self.mouse_movements[0] += dx
		self.mouse_movements[1] += dy
	
	
	def mouse_wheel(self, wx, wy):
		"""
		Schedules mouse wheel movement to be done at end of processing callback.
		Called from actions while callback is being processed.
		"""
		self.mouse_movements[2] += wx
		self.mouse_movements[3] += wy
	
	
	def send_feedback(self, hapticdata):
		"""
		Schedules haptic feedback to be sent at end of processing callback.
		Called from actions while callback is being processed.
		"""
		if hapticdata.get_position() == HapticPos.BOTH:
			# HapticPos.BOTH is special case as controller doesn't
			# really support doing that by itself.
			self.feedbacks[0]  = hapticdata.with_position(HapticPos.LEFT)
			self.feedbacks[1]  = hapticdata.with_position(HapticPos.RIGHT)
		else:
			self.feedbacks[hapticdata.get_position()] = hapticdata
	
	
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
	
	
	def get_pressed_button(self):
		"""
		Gets button that was pressed by very last handled event or None,
		if last event doesn't involved button pressing.
		"""
		for x in SCButtons:
			if x & self.buttons & ~self.old_buttons:
				return x
		return None
	
	
	def release_virtual_buttons(self):
		"""
		Called when daemon is killed or USB dongle is disconnected.
		Sends button release event for every virtual button that is still being
		pressed.
		"""
		to_release, self.pressed = self.pressed, {}
		for x in to_release:
			ButtonAction._button_release(self, x, True)
	
	
	def input(self, controller, now, old_state, state):
		# Store states
		self.old_state = old_state
		self.old_buttons = self.buttons

		self.state = state
		self.buttons = state.buttons
		
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
				if FE_STICK in fe or self.old_state.lpad_x != state.lpad_x or self.old_state.lpad_y != state.lpad_y:
					self.profile.stick.whole(self, state.lpad_x, state.lpad_y, STICK)
			
			# Check gyro
			if controller.get_gyro_enabled():
				self.profile.gyro.gyro(self, state.gpitch, state.gyaw, state.groll, state.q1, state.q2, state.q3, state.q4)
			
			# Check triggers
			if FE_TRIGGER in fe or state.ltrig != self.old_state.ltrig:
				if LEFT in self.profile.triggers:
					self.profile.triggers[LEFT].trigger(self, state.ltrig, self.old_state.ltrig)
			if FE_TRIGGER in fe or state.rtrig != self.old_state.rtrig:
				if RIGHT in self.profile.triggers:
					self.profile.triggers[RIGHT].trigger(self, state.rtrig, self.old_state.rtrig)
			
			# Check pads
			# RPAD
			if FE_PAD in fe or self.buttons & SCButtons.RPADTOUCH or SCButtons.RPADTOUCH & btn_rem:
				self.profile.pads[RIGHT].whole(self, state.rpad_x, state.rpad_y, RIGHT)
			
			# LPAD
			if self.buttons & SCButtons.LPADTOUCH:
				# Pad is being touched now
				if not self.lpad_touched:
					self.lpad_touched = True
				self.profile.pads[LEFT].whole(self, state.lpad_x, state.lpad_y, LEFT)
			elif not self.buttons & STICK_TILT:
				# Pad is not being touched
				if self.lpad_touched:
					self.lpad_touched = False
					self.profile.pads[LEFT].whole(self, 0, 0, LEFT)
		except Exception, e:
			# Log error but don't crash here, it breaks too many things at once
			log.error("Error while processing controller event")
			log.error(traceback.format_exc())
		
		self.run_scheduled(now)
		self.generate_events()
		self.generate_feedback()
	
	
	def run_scheduled(self, now):
		if len(self.scheduled_tasks) > 0 and self.scheduled_tasks[0][0] <= now:
			cb = self.scheduled_tasks[0][1]
			self.scheduled_tasks = self.scheduled_tasks[1:]
			cb(self)
	
	
	def generate_events(self):
		# Generate events - keys
		if len(self.keypress_list):
			self.keyboard.pressEvent(self.keypress_list)
			self.keypress_list = []
		if len(self.keyrelease_list):
			self.keyboard.releaseEvent(self.keyrelease_list)
			self.keyrelease_list = []
		# Generate events - mouse
		mx, my, wx, wy = self.mouse_movements
		if mx != 0 or my != 0:
			self.mouse.moveEvent(mx, my * -1)
			self.syn_list.add(self.mouse)
		if wx != 0 or wy != 0:
			self.mouse.scrollEvent(wx, wy)
			self.syn_list.add(self.mouse)
		self.mouse_movements = [ 0, 0, 0, 0 ]
		self.sync()
	
	
	def generate_feedback(self):
		if self.controller:
			for x in (0, 1):
				if self.feedbacks[x]:
					self.controller.feedback(self.feedbacks[x])
					self.feedbacks[x] = None
