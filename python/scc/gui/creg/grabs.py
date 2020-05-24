#!/usr/bin/env python2
"""
SC-Controller - Controller Registration - Grabs

Helper classes for grabbing buttons and axes from physical gamepads.

"""
from __future__ import unicode_literals
from scc.tools import _

from scc.constants import STICK_PAD_MAX, STICK_PAD_MIN
from scc.gui.creg.constants import AXIS_MASK
from scc.gui.creg.data import AxisData, DPadEmuData
from scc.gui.creg.constants import X, Y
from scc.tools import nameof

import logging
log = logging.getLogger("CReg.grabs")


class InputGrabber(object):
	"""
	Base class for input grabbing. Waits for physical button being pressed
	by default.
	"""
	
	def __init__(self, parent, what, text=_("Press a button...")):
		self.parent = parent
		self.what = what
		self.set_message(text)
		self.dlgPressButton = parent.builder.get_object("dlgPressButton")
		self.dlgPressButton.show()
	
	
	def set_message(self, text):
		self.parent.builder.get_object("lblPressButton").set_text(text)
	
	
	def cancel(self):
		self.dlgPressButton.hide()
		self.parent._grabber = None
	
	
	def on_button(self, keycode, pressed):
		if not pressed:
			self.set_mapping(keycode, self.what)
	
	
	def set_mapping(self, keycode, what):
		parent = self.parent
		
		if isinstance(what, AxisData) and what in parent._mappings.values():
			for c in parent._mappings.keys():
				if parent._mappings[c] == what:
					del parent._mappings[c]
		
		parent._mappings[keycode] = what
		log.debug("Reassigned %s to %s", keycode, what)
		
		if nameof(what) in parent._unassigned:
			parent._unassigned.remove(nameof(what))
			parent.unhilight(nameof(what))
		
		self.parent.generate_unassigned()
		self.parent.generate_raw_data()
		self.cancel()
	
	
	def on_axis(self, number, value):
		pass


class TriggerGrabber(InputGrabber):
	"""
	InputGrabber modified to grab trigger bindings.
	That may be button or axis with at least 0-250 range is accepted.
	"""
	def __init__(self, parent, what, text=_("Pull a trigger...")):
		InputGrabber.__init__(self, parent, what, text)
		self.orig_pos = { k: parent._input_axes[k] for k in parent._input_axes }
		self.new_pos  = { k: parent._input_axes[k] for k in parent._input_axes }
	
	
	def on_button(self, keycode, pressed):
		if not pressed:
			self.set_mapping(keycode, self.what)
			self.what.min = STICK_PAD_MIN
			self.what.max = STICK_PAD_MAX
	
	
	def on_axis(self, number, value):
		if number > 50:
			# TODO: Remove this condition
			return
		self.new_pos[number] = value
		if number not in self.orig_pos:
			self.orig_pos[number] = 0
		
		# Get avgerage absolute change for all axes
		avg = float(sum([
				abs( self.orig_pos[k] - self.new_pos[k] )
				for k in self.new_pos
			])) / float(len(self.new_pos))
		
		# Get absolute change for _this_ axis
		change = abs( self.orig_pos[number] - self.new_pos[number] )
		if change > 2 and change > avg * 0.5:
			# TODO: change > 2 may be too strict
			# if there is pad going from -1 to 1 somewhere around
			self.axis_change(number, value, change)
	
	
	def axis_change(self, number, value, change):
		if value > 250:
			self.what.reset()
			self.set_mapping(AXIS_MASK | number, self.what)
			self.parent.generate_unassigned()
			self.parent.generate_raw_data()
			self.cancel()


class StickGrabber(TriggerGrabber):
	"""
	InputGrabber modified to grab stick or pad bindings, in two phases for
	both X and Y axis.
	"""
	
	def __init__(self, parent, what):
		TriggerGrabber.__init__(self, parent, what,
				text=_("Move stick left or right..."))
		self.xy = X
		self.grabbed = [ None, None ]
	
	
	def on_button(self, keycode, pressed):
		#if len(self.grabbed) == 2 and self.grabbed[X] != None:
		#	# Already grabbed one axis, don't grab buttons
		#	return
		if keycode in self.grabbed:
			# Don't allow same button to be used twice
			return
		if not pressed:
			if len(self.grabbed) < 4:
				self.grabbed = [ None ] * 4
			if self.grabbed[0] is None:
				self.grabbed[0] = keycode
				self.set_message(_("Move DPAD to right"))
			elif self.grabbed[1] is None:
				self.grabbed[1] = keycode
				self.set_message(_("Move DPAD up"))
			elif self.grabbed[2] is None:
				self.grabbed[2] = keycode
				self.set_message(_("Move DPAD down"))
			elif self.grabbed[3] is None:
				self.grabbed[3] = keycode
				self.set_message(str(self.grabbed))
				grabbed = [] + self.grabbed
				for w in self.what:
					for negative in (False, True):
						keycode, grabbed = grabbed[0], grabbed[1:]
						w.reset()
						self.set_mapping(keycode, DPadEmuData(w, negative))
				self.parent.generate_unassigned()
				self.parent.generate_raw_data()
				self.cancel()
	
	
	def on_axis(self, number, value):
		if len(self.grabbed) > 2:
			# Already started grabbing 4 buttons, don't grab axes now
			return
		if self.xy == X:
			self.grabbed[X] = number
			self.xy = Y
			self.set_message(_("Move stick up or down..."))
		else:
			if number != self.grabbed[X]:
				self.grabbed[Y] = number
				for i in xrange(len(self.grabbed)):
					self.what[i].reset()
					self.set_mapping(AXIS_MASK | self.grabbed[i], self.what[i])
				self.parent.generate_unassigned()
				self.parent.generate_raw_data()
				self.cancel()

