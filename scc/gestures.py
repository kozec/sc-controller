#!/usr/bin/env python2
"""
SC-Controller - Gestures

Everything related to non-GUI part of gesture detection lies here.
It's technically part of SCC-Daemon, separater into special module just to keep
it clean.
"""
from scc.actions import Action
from scc.tools import circle_to_square, clamp
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX
from math import pi as PI, atan2, sqrt
from itertools import groupby

import logging
log = logging.getLogger("Gestures")


class GestureDetector(Action):
	"""
	Derived from Action, but not callable in profile.
	
	When daemon decides it's good time to start gesture, be it because of
	GestureAction special action or "Gesture:" message from client,
	it constructs instance of this class and leaves everything to it.
	"""
	UP			= "U"
	DOWN		= "D"
	LEFT		= "L" 
	RIGHT		= "R"
	
	
	def __init__(self, up_direction, on_finished):
		Action.__init__(self)
		# TODO: Configurable resolution
		self._resolution = 3
		self._deadzone = 1.0 / self._resolution / self._resolution
		self._up_direction = up_direction
		self._on_finished = on_finished
		self._enabled = False
		self._positions = []
		self._result = []
	
	
	def enable(self):
		""" GestureDetector doesn't starts do detect anything until this is called """
		self._enabled = True
		self._result = [ ]
	
	
	def get_string(self):
		""" Returns string representation of (probably unfinished) gesture """
		return "".join(self._result)
	
	
	def get_positions(self):
		""" Returns list of positions used to generate gesture """
		return self._positions
	
	
	def get_resolution(self):
		""" Returns gesture resolution """
		return self._resolution
	
	
	def whole(self, mapper, x, y, what):
		if self._enabled:
			if (x, y) == (0, 0):
				# Pad was released
				self._enabled = False
				self._on_finished(self, "".join(self._result))
				return
			else:
				# Convert positions on pad to position on grid
				x -= STICK_PAD_MIN
				y = STICK_PAD_MAX - y
				x = float(x) / (float(STICK_PAD_MAX - STICK_PAD_MIN) / self._resolution)
				y = float(y) / (float(STICK_PAD_MAX - STICK_PAD_MIN) / self._resolution)
				# Check for deadzones around grid lines
				for i in xrange(1, self._resolution):
					if x > i - self._deadzone and x < i + self._deadzone: return
					if y > i - self._deadzone and y < i + self._deadzone: return
				# Round
				x = clamp(0, int(x), self._resolution - 1)
				y = clamp(0, int(y), self._resolution - 1)
				if self._positions:
					ox, oy = self._positions[-1]
					if (x, y) != (ox, oy):
						self._positions.append( (x, y) )
						while (x, y) != (ox, oy):
							if x < ox:
								self._result.append(self.LEFT)
								x += 1
							elif x > ox:
								self._result.append(self.RIGHT)
								x -= 1
							elif y < oy:
								self._result.append(self.UP)
								y += 1
							elif y > oy:
								self._result.append(self.DOWN)
								y -= 1
				else:
					self._positions.append( (x, y) )
