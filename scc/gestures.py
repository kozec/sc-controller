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
	
	When daemon decides it's good time to start gesture, be it thanks to
	GestureAction special action or "Gesture:" message from client,
	it constructs instance of this class and leaves everything to it.
	"""
	# Minimal difference in positions over both axes
	MIN_MOVEMENT_SIZE = 500.0
	
	# Constants used in GestureDetector.cleanup
	DIRTY_ELS = ("412", "236", "698", "874", "214", "478", "896", "632",
				 "284", "468", "826", "642", "286", "648", "824", "462")
	SHORT = 0.3
	
	
	def __init__(self, up_direction, vh_preference, on_finished):
		Action.__init__(self)
		self._up_direction = up_direction
		self.vh_preference = clamp(0, vh_preference, 45)
		self._on_finished = on_finished
		self._enabled = False
		self._old_pos = None
	
	
	def enable(self):
		""" GestureDetector doesn't starts do detect anything until this is called """
		self._enabled = True
		self._string = ""
	
	
	def whole(self, mapper, x, y, what):
		if self._enabled:
			if (x, y) == (0, 0):
				# Released
				self._enabled = False
				self._on_finished(self, 
					(self._string + "::" +
					GestureDetector.cleanup(self._string)
					))
				return
			else:
				if self._old_pos is None:
					self._old_pos = x, y
				else:
					dx, dy = self._old_pos[0] - x, self._old_pos[1] - y
					if sqrt(dx * dx + dy * dy) > GestureDetector.MIN_MOVEMENT_SIZE:
						angle = atan2(dy, dx) * 180.0 / PI
						if angle < 0: angle += 360
						self._string = "%s%s" % (
							self._string, GestureDetector.angle_to_direction(angle))
						self._old_pos = x, y
	
	
	@staticmethod
	def cleanup(dirty):
		"""
		This does magic.
		
		1st, it breaks gesture into consecutive strings of same characters.
		2nd, it find longest such string and removes every other string that is
		     shorter than rougly 1/3 of longest size
		3rd, it reassemles string back, removing all repeating characters
		4rd, as special treatement, removes all cases when there is diagonal
		     motion detected between two straight movements, to make detection
		     of "L-like" movements better.
		
		Doing this had best results in making sure that I can get same gesture
		string for eveyr time when I attempt to do same gesture.
		"""
		cur, split = [], []
		last, longest = None, 0
		for ch in dirty:
			if ch != last:
				if len(cur) > 0:
					longest = max(longest, len(cur))
					split.append("".join(cur))
					cur = []
					last = ch
			cur.append(ch)
		
		req_len = max(1, int(longest * GestureDetector.SHORT))
		split = ( x[0] for x in split if len(x) > req_len )
		almost_clean = "".join(( x[0] for x in groupby(split) ))
		for dl in GestureDetector.DIRTY_ELS:
			while dl in almost_clean:
				almost_clean = almost_clean.replace(dl, "")
		
		return "[%s]%s" % (longest, almost_clean)
	
	
	@staticmethod
	def angle_to_direction(angle):
		"""
		Translates direction expressed in degrees (where 0.0 goes left and 90.0 up)
		to direction expressed using numbers of numpad (because that's as good as
		anything else for my purposes)
		"""
		B = 45
		if angle > 360 - B or angle < B:
			return 4	# Left
		elif angle > B and angle < 90 - B:
			return 1	# Left-Down
		elif angle > 90 - B and angle < 90 + B:
			return 2	# Down
		elif angle > 90 + B and angle < 180 - B:
			return 3	# Right-Down
		elif angle > 180 - B and angle < 180 + B:
			return 6	# Rigth
		elif angle > 180 + B and angle < 270 - B:
			return 9	# Rigth-Up
		elif angle > 270 - B and angle < 270 + B:
			return 8	# Up
		else:
			return 7	# Left-Up
