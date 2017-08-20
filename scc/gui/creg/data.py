#!/usr/bin/env python2
"""
SC-Controller - Controller Registration data

Dummy container classes
"""
from __future__ import unicode_literals

from scc.constants import STICK_PAD_MAX, STICK_PAD_MIN
from scc.gui.creg.constants import AXIS_TO_BUTTON

import logging
log = logging.getLogger("CRegistration.data")


class AxisData(object):
	"""
	(Almost) dumb container.
	Stores position, center and limits for single axis.
	"""
	
	def __init__(self, name, xy, min=STICK_PAD_MAX, max=STICK_PAD_MIN):
		self.name = name
		self.area = name.split("_")[0].upper()
		if self.area.endswith("TRIG"): self.area = self.area[0:-3]
		self.xy = xy
		self.pos = 0
		self.center = 0
		self.min = min
		self.max = max
		self.invert = False
		self.cursor = None
	
	
	def reset(self):
		"""
		Resets min and max value so axis can (has to be) recalibrated again
		"""
		self.min = STICK_PAD_MAX
		self.max = STICK_PAD_MIN
	
	
	def __repr__(self):
		return "<Axis data '%s'>" % (self.name, )
	
	
	def set_position(self, value):
		"""
		Returns current position
		translated to range of (STICK_PAD_MIN, STICK_PAD_MAX)
		"""
		self.min = min(self.min, value)
		self.max = max(self.max, value)
		self.pos = value
		try:
			r = (STICK_PAD_MAX - STICK_PAD_MIN) / (self.max - self.min)
			v = (self.pos - self.min) * r
			if self.invert:
				return STICK_PAD_MAX - v
			else:
				return v + STICK_PAD_MIN
		except ZeroDivisionError:
			return 0


class DPadEmuData(object):
	"""
	Dumb container that stores dpad emulation data.
	DPAd emulation is used, for example, on PS3 controller, where dpad does not
	inputs as 2 axes, but as 4 buttons.
	
	This class stores mapping of one button to one half of axis.
	"""
	
	def __init__(self, axis_data, positive):
		self.axis_data = axis_data
		self.positive  = positive
		self.button = AXIS_TO_BUTTON[axis_data.name]
