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

import logging
log = logging.getLogger("Gestures")


class GestureDetector(Action):
	"""
	Derived from Action, but not callable in profile.
	
	When daemon decides it's good time to start gesture, be it thanks to
	GestureAction special action or "Start Gesture" message from client,
	it constructs instance of this class and leaves everything to it.
	"""
	
	
	def __init__(self, resolution, on_finished):
		Action.__init__(self)
		self._resolution = clamp(2, resolution, 6)
		self._on_finished = on_finished
		self._enabled = False
	
	
	def enable(self):
		""" GestureDetector doesn't starts do detect anything until this is called """
		self._enabled = True
		self._string = "%s:" % (self._resolution,)
		self._last = None
	
	
	def whole(self, mapper, x, y, what):
		if self._enabled:
			if (x, y) == (0, 0):
				# Released
				self._enabled = False
				self._on_finished(self, self._string)
			else:
				## Project to rectangle
				# x, y = circle_to_square(x, y)
				# Project from ~(-32k, 32) to ~(0, 64k)
				x = max(0.0, x + STICK_PAD_MAX)
				y = max(0.0, y + STICK_PAD_MAX)
				# Convert to small, nice integers
				x = int(float(x) / STICK_PAD_MAX * 0.5 * self._resolution)
				y = int(float(y) / STICK_PAD_MAX * 0.5 * self._resolution)
				if self._last != (x, y):
					self._last = x, y
					self._string = "%s%s%s" % (
						self._string,
						int(x),
						chr(65 + y)	# 'A' + y
					)
