#!/usr/bin/env python2
"""
SC Controller - Macros

Frontier is my favorite.
"""


from scc.actions import Action, NoAction, ButtonAction, MOUSE_BUTTONS
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import LEFT, RIGHT, STICK, SCButtons
from scc.uinput import Keys


import time, logging
log = logging.getLogger("Macros")
_ = lambda x : x


class Macro(Action):
	"""
	Two or more actions executed in sequence.
	Generated when parsing ';'
	"""

	COMMAND = None
	HOLD_TIME = 0.01
	
	def __init__(self, *parameters):
		Action.__init__(self, *parameters)
		self.actions = []
		self.repeat = False
		self.hold_time = Macro.HOLD_TIME
		self._active = False
		self._current = None
		self._release = None
		for p in parameters:
			if type(p) == float and len(self.actions):
				self.actions[-1].delay_after = p
			elif isinstance(p, Macro):
				self.actions += p.actions
			elif isinstance(p, Action):
				self.actions.append(p)
			else:
				self.actions.append(ButtonAction(p))
	
	
	def button_press(self, mapper):
		# Macro can be executed only by pressing button
		if len(self.actions) < 1:
			# Empty macro
			return False
		self._active = True
		if self._current is not None:
			# Already executing macro
			return False
		self._current = [] + self.actions
		self.timer(mapper)
	
	
	def timer(self, mapper):
		if self._release is None:
			# Execute next action
			self._release, self._current = self._current[0], self._current[1:]
			self._release.button_press(mapper)
			mapper.schedule(self.hold_time, self.timer)
		else:
			# Finish execited action
			self._release.button_release(mapper)
			if len(self._current) == 0 and self.repeat and self._active:
				# Repeating
				self._current = [] + self.actions
				mapper.schedule(self._release.delay_after, self.timer)
				self._release = None
			elif len(self._current) == 0:
				# Finished
				self._current = None
				self._release = None
			else:
				# Schedule for next action
				mapper.schedule(self._release.delay_after, self.timer)
				self._release = None
	
	
	def cancel(self, mapper):
		for a in self.actions:
			a.cancel(mapper)
	
	
	def set_haptic(self, hapticdata):
		for a in self.actions:
			if a and hasattr(a, "set_haptic"):
				a.set_haptic(hapticdata)
	
	
	def get_haptic(self):
		for a in self.actions:
			if a and hasattr(a, "set_haptic"):
				return a.get_haptic()
		return None
	
	
	def set_speed(self, x, y, z):
		for a in self.actions:
			if hasattr(a, "set_speed"):
				a.set_speed(x, y, z)
	
	
	def get_speed(self):
		for a in self.actions:
			if hasattr(a, "set_speed"):
				return a.get_speed()
		return (1.0,)
	
	
	def button_release(self, mapper):
		self._active = False
	
	
	def describe(self, context):
		if self.name: return self.name
		if self.repeat:
			return "repeat " + "; ".join([ x.describe(context) for x in self.actions ])
		return "; ".join([ x.describe(context) for x in self.actions ])
	
	
	def to_string(self, multiline=False, pad=0):
		lst = "; ".join([ x.to_string() for x in self.actions ])
		if self.repeat:
			return (" " * pad) + ("repeat(%s)" % (lst,))
		return (" " * pad) + lst
	
	
	def __str__(self):
		if self.repeat:
			return "<[repeat %s ]>" % ("; ".join([ str(x) for x in self.actions ]), )
		return "<[ %s ]>" % ("; ".join([ str(x) for x in self.actions ]), )
	
	__repr__ = __str__


class Type(Macro):
	"""
	Special type of Macro where keys to press are specified as string.
	Basically, writing type("iddqd") is same thing as
	button(KEY_I) ; button(KEY_D) ; button(KEY_D); button(KEY_Q); button(KEY_D)
	
	Recognizes only lowercase letters, uppercase letters, numbers and space.
	Adding anything else will make action unparseable.
	"""
	COMMAND = "type"
	HOLD_TIME = 0.001

	def __init__(self, string):
		params = []
		shift = False
		for letter in string:
			if (letter >= 'a' and letter <= 'z') or (letter >= '0' and letter <= '9'):
				if hasattr(Keys, ("KEY_" + letter).upper()):
					if shift:
						params.append(ReleaseAction(Keys.KEY_LEFTSHIFT))
						shift = False
					params.append(ButtonAction(getattr(Keys, ("KEY_" + letter).upper())))
					continue
			if letter == ' ':
				params.append(ButtonAction(Keys.KEY_SPACE))
				continue
			if letter >= 'A' and letter <= 'Z':
				if hasattr(Keys, "KEY_" + letter):
					if not shift:
						params.append(PressAction(Keys.KEY_LEFTSHIFT))
						shift = True
					params.append(ButtonAction(getattr(Keys, "KEY_" + letter)))
					continue
			raise ValueError("Invalid character for type(): '%s'" % (letter,))
		Macro.__init__(self, *params)
		self.letters = string
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + self.COMMAND + "(" + repr(self.letters).strip("u") + ")"


class Cycle(Macro):
	"""
	Multiple actions cycling on same button.
	When button is pressed 1st time, 1st action is executed. 2nd action is
	executed for 2nd press et cetera et cetera.
	"""

	COMMAND = 'cycle'
	
	def __init__(self, *parameters):
		Action.__init__(self, *parameters)
		self.actions = parameters
		self._current = 0
	
	
	def button_press(self, mapper):
		if len(self.actions) > 0:
			self.actions[self._current].button_press(mapper)
	
	
	def button_release(self, mapper):
		if len(self.actions) > 0:
			self.actions[self._current].button_release(mapper)
			self._current += 1
			if self._current >= len(self.actions):
				self._current = 0
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Cycle Actions")
	
	
	def to_string(self, multiline=False, pad=0):
		lst = ", ".join([ x.to_string() for x in self.actions ])
		return (" " * pad) + self.COMMAND + "(" + lst + ")"
	
	
	def __str__(self):
		return "<cycle %s >" % ("; ".join([ str(x) for x in self.actions ]), )
	
	__repr__ = __str__


class Repeat(Macro):
	"""
	Repeats specified action as long as physical button is pressed.
	This is actually just Macro with 'repeat' set to True
	"""
	COMMAND = "repeat"
	def __new__(cls, action):
		if not isinstance(action, Macro):
			action = Macro(action)
		action.repeat = True
		return action


class SleepAction(Action):
	"""
	Does nothing.
	If used in macro, overrides delay after itself.
	"""
	COMMAND = "sleep"
	def __init__(self, delay):
		Action.__init__(self, delay)
		self.delay = float(delay)
		self.delay_after = self.delay - Macro.HOLD_TIME
	
	def describe(self, context):
		if self.name: return self.name
		if self.delay < 1.0:
			return _("Wait %sms") % (int(self.delay*1000),)
		else:
			s = ("%0.2f" % (self.delay,)).strip(".0")
			return _("Wait %ss") % (s,)
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s(%0.3f)" % (self.COMMAND, self.delay)

	
	def button_press(self, mapper): pass
	def button_release(self, mapper): pass


class PressAction(Action):
	"""
	Presses button and leaves it pressed.
	Can be used anywhere, but makes sense only with macro.
	"""
	COMMAND = "press"
	PR = _("Press")

	def __init__(self, action):
		Action.__init__(self, action)
		self.action = action
	
	
	def describe_short(self):
		""" Used in macro editor """
		if isinstance(self.action, ButtonAction):
			return self.action.describe_short()
		if isinstance(self.action, Keys):
			return ButtonAction.describe_button(self.action)
		return self.action.describe(Action.AC_BUTTON)
	
	
	def describe(self, context):
		if self.name: return self.name
		return self.PR + " " + self.describe_short()
	
	
	def button_press(self, mapper):
		self.action.button_press(mapper)
	
	
	def button_release(self, mapper):
		# This is activated only when button is pressed
		pass


class ReleaseAction(PressAction):
	"""
	Releases button.
	Can be used anywhere, but makes sense only with macro.
	"""
	COMMAND = "release"
	PR = _("Release")
	
	def button_press(self, mapper):
		self.action.button_release(mapper)


class TapAction(PressAction):
	"""
	Presses button for short time.
	If button is already pressed, generates release-press-release-press
	events in quick sequence.
	"""
	COMMAND = "tap"
	PR = _("Tap")
	PAUSE = 0.1
	COUNTER_VAL = 100
	
	def __init__(self, button, count=1):
		PressAction.__init__(self, button)
		self._lst = []
		self._keep_pressed = False
		self.button = button
		self.count = count

	
	def button_press(self, mapper):
		if len(self._lst):
			# Still executing from scheduler
			return
		
		# ---
		# This thing abuses internal "button press" counter a little; First,
		# if button is supposedly pressed more than 1 times (because two or more
		# actions are holding it down at same time), tap is aborted. That is not
		# ideal, but shouldn't be a problem in most cases.
		#
		# 2nd, counter is manipulated before every call to _button_press / release,
		# so it always fires emulated button. Then, while scheduler is active,
		# counter is bumped to 'COUNTER_VAL', so it can be detected that other
		# action touched same button.
		# ---
		if self.button in mapper.pressed and mapper.pressed[self.button] > 1:
			log.warning("Failed to tap, two or more actions are holding button")
			return
			
		# Generate as many clicks as requested
		# True is for press, False for release
		self._lst = [ True, False ] * self.count
		
		if self.button in mapper.pressed and mapper.pressed[self.button] > 0:
			# Surround by release - ... - press if button is currently pressed
			self._lst = [ False ] + self._lst + [ True ]
		elif self.count > 1:
			# Keep button pressed if double-or-more tap was requested
			self._lst = self._lst[0:-1]
			self._keep_pressed = True
		
		mapper.pressed[self.button] = self.COUNTER_VAL
		self._rel_tap_press(mapper)
	
	
	def _bailout(self):
		self._lst, self._keep_pressed = [], None
		return None
	
	
	def _rel_tap_press(self, mapper):
		if not self.button in mapper.pressed or mapper.pressed[self.button] < self.COUNTER_VAL:
			# Something else tried to _release_ button in meanwhile, bail out
			mapper.pressed[self.button] = 1
			ButtonAction._button_release(mapper, self.button)
			return self._bailout()
		elif mapper.pressed[self.button] > self.COUNTER_VAL:
			# Something else pressed button in meanwhile, bail out
			mapper.pressed[self.button] = 1
			return self._bailout()
		
		a, self._lst = self._lst[0], self._lst[1:]
		if a:
			mapper.pressed[self.button] = 0
			ButtonAction._button_press(mapper, self.button)
		else:
			mapper.pressed[self.button] = 1
			ButtonAction._button_release(mapper, self.button)
		if len(self._lst):
			mapper.pressed[self.button] = self.COUNTER_VAL
			mapper.schedule(self.PAUSE, self._rel_tap_press)
	
	
	def button_release(self, mapper):
		if self._keep_pressed:
			self._keep_pressed = False
			if len(self._lst) > 0:
				# _rel_tap_press is still scheduled
				self._lst += [ False ]
			else:
				ButtonAction._button_release(mapper, self.button)
	
	
	def describe_short(self):
		""" Used in macro editor """
		if self.count <= 1:
			return "%s %s" % (_("Tap"), ButtonAction.describe_button(self.button))
		if self.count == 2:
			return "%s %s" % (_("DblTap"), ButtonAction.describe_button(self.button))
		return "%s%s %s" % (self.count, _("-tap"), ButtonAction.describe_button(self.button))
	
	
	def describe(self, context):
		if self.name: return self.name
		return self.describe_short()
	
	
	def to_string(self, multiline=False, pad=0):
		if self.count <= 1:
			return "%s(%s)" % (self.COMMAND, self.button)
		return "%s(%s, %s)" % (self.COMMAND, self.button, self.count)
