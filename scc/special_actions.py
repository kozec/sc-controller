#!/usr/bin/env python2
"""
SC Controller - Special Actions

Special Action is "special" since it cannot be handled by mapper alone.
Instead, on_sa_<actionname> method on handler instance set by
mapper.set_special_actions_handler() is called to do whatever action is supposed
to do. If handler is not set, or doesn't have reqiuired method defined,
action only prints warning to console.
"""
from __future__ import unicode_literals

from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD, SCButtons
from scc.constants import LEFT, RIGHT, STICK, SCButtons, SAME
from scc.actions import Action, NoAction, SpecialAction, ButtonAction
from scc.actions import OSDEnabledAction, MOUSE_BUTTONS
from scc.tools import strip_none, nameof, clamp
from scc.constants import STICK_PAD_MAX
from scc.modifiers import Modifier
from math import sqrt

import time, logging
log = logging.getLogger("SActions")
_ = lambda x : x


class ChangeProfileAction(Action, SpecialAction):
	SA = COMMAND = "profile"
	
	def __init__(self, profile):
		Action.__init__(self, profile)
		self.profile = profile
	
	def describe(self, context):
		if self.name: return self.name
		if context == Action.AC_OSD:
			return _("Profile: %s") % (self.profile,)
		if context == Action.AC_SWITCHER:
			return _("Switch to %s") % (self.profile,)
		return _("Profile Change")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s('%s')" % (self.COMMAND, self.profile.encode('string_escape'))
	
	
	def button_release(self, mapper):
		# Execute only when button is released (executing this when button
		# is pressed would send following button_release event to another
		# action from loaded profile)
		self.execute(mapper)


class ShellCommandAction(Action, SpecialAction):
	SA = COMMAND = "shell"
	
	def __init__(self, command):
		Action.__init__(self, command)
		self.command = command
	
	def describe(self, context):
		if self.name: return self.name
		return _("Execute Command")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s('%s')" % (self.COMMAND, self.parameters[0].encode('string_escape'))
	
	
	def button_press(self, mapper):
		# Execute only when button is pressed
		self.execute(mapper)


class TurnOffAction(Action, SpecialAction):
	SA = COMMAND = "turnoff"
	
	def __init__(self):
		Action.__init__(self)
	
	def describe(self, context):
		if self.name: return self.name
		if context == Action.AC_OSD:
			return _("Turning controller OFF")
		return _("Turn Off the Controller")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)
	
	
	def button_release(self, mapper):
		# Execute only when button is released (executing this when button
		# is pressed would hold stuck any other action bound to same button,
		# as button_release is not sent after controller turns off)
		self.execute(mapper)


class LedAction(Action, SpecialAction):
	SA = COMMAND = "led"
	
	def __init__(self, brightness):
		Action.__init__(self, brightness)
		self.brightness = clamp(0, int(brightness), 100)
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Set LED brightness")
	
	
	def button_press(self, mapper):
		# Execute only when button is pressed
		self.execute(mapper)


class OSDAction(Action, SpecialAction):
	"""
	Displays text in OSD, or, if used as modifier, displays action description
	and executes that action.
	"""
	SA = COMMAND = "osd"
	DEFAULT_TIMEOUT = 5
	PROFILE_KEY_PRIORITY = -5	# After XYAction, but beforee everything else
	
	def __init__(self, *parameters):
		Action.__init__(self, *parameters)
		self.action = None
		self.timeout = self.DEFAULT_TIMEOUT
		if len(parameters) > 1:
			# timeout parameter included
			self.timeout = parameters[0]
		if isinstance(parameters[-1], Action):
			self.action = parameters[-1]
			self.text = self.action.describe(Action.AC_OSD)
		else:
			self.text = unicode(parameters[-1])
		if self.action and isinstance(self.action, OSDEnabledAction):
			self.action.enable_osd(self.timeout)
	
	
	def encode(self):
		if self.action:
			rv = self.action.encode()
			if self.timeout == self.DEFAULT_TIMEOUT:
				rv[OSDAction.COMMAND] = True
			else:
				rv[OSDAction.COMMAND] = self.timeout
			return rv
		else:
			return Action.encode(self)	
	
	
	@staticmethod
	def decode(data, a, *b):
		a = OSDAction(a)
		if data["osd"] is not True:
			a.timeout = float(data["osd"])
		return a
	
	
	def describe(self, context):
		if self.name: return self.name
		if self.action:
			return _("%s (with OSD)") % (self.action.describe(context), )
		elif context == Action.AC_OSD:
			return _("Display '%s'" % self.text)
		return _("OSD Message")
	
	
	def to_string(self, multiline=False, pad=0):
		if isinstance(self.parameters[0], Action):
			p0str = self.parameters[0].to_string()
		else:
			p0str = "'%s'" % (str(self.parameters[0]).encode('string_escape'),)
		if len(self.parameters) == 1:
			return (" " * pad) + "%s(%s)" % (self.COMMAND, p0str)
		else:
			return (" " * pad) + "%s(%s, %s)" % (self.COMMAND,
				p0str, self.parameters[1]
			)
	
	
	def strip(self):
		if self.action:
			return self.action.strip()
		return self
	
	
	def compress(self):
		if self.action:
			if isinstance(self.action, OSDEnabledAction):
				return self.action.compress()
			self.action = self.action.compress()
		return self
	
	
	def button_press(self, mapper):
		self.execute(mapper)
		if self.action:
			return self.action.button_press(mapper)
	
	
	def button_release(self, mapper):
		if self.action:
			return self.action.button_release(mapper)
	
	
	def trigger(self, mapper, position, old_position):
		if self.action:
			return self.action.trigger(mapper, position, old_position)
	
	def axis(self, mapper, position, what):
		if self.action:
			return self.action.axis(mapper, position, what)
	
	def pad(self, mapper, position, what):
		if self.action:
			return self.action.pad(mapper, position, what)
	
	def whole(self, mapper, x, y, what):
		if self.action:
			return self.action.whole(mapper, x, y, what)


class MenuAction(Action, SpecialAction):
	"""
	Displays menu defined in profile or globally.
	"""
	SA = COMMAND = "menu"
	MENU_TYPE = "menu"
	DEFAULT_CONFIRM = SCButtons.A
	DEFAULT_CANCEL = SCButtons.B
	DEFAULT_CONTROL = STICK
	MIN_STICK_DISTANCE = STICK_PAD_MAX / 3
	DEFAULT_POSITION = 10, -10
	
	def __init__(self, menu_id, control_with=DEFAULT_CONTROL,
					confirm_with=DEFAULT_CONFIRM, cancel_with=DEFAULT_CANCEL,
					show_with_release=False):
		if control_with == SAME:
			# Little touch of backwards compatibility
			control_with, confirm_with = self.DEFAULT_CONTROL, SAME
		Action.__init__(self, menu_id, control_with, confirm_with, cancel_with, show_with_release)
		self.menu_id = menu_id
		self.control_with = control_with
		self.confirm_with = confirm_with
		self.cancel_with = cancel_with
		self.x, self.y = MenuAction.DEFAULT_POSITION
		self.show_with_release = bool(show_with_release)
		self._stick_distance = 0
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Menu")
	
	
	def to_string(self, multiline=False, pad=0):
		return "%s%s(%s)" % (
			" " * pad,
			self.COMMAND,
			",".join(Action.encode_parameters(self.strip_defaults()))
		)
	
	
	def button_press(self, mapper):
		if not self.show_with_release:
			confirm_with = self.confirm_with
			args = [ mapper ]
			if confirm_with == SAME:
				confirm_with = mapper.get_pressed_button() or self.DEFAULT_CONFIRM
			if nameof(self.control_with) in (LEFT, RIGHT):
				args += [ '--use-cursor' ]
			args += [
				'--control-with', nameof(self.control_with),
				'-x', str(self.x), '-y', str(self.y),
				'--confirm-with', confirm_with.name,
				'--cancel-with', self.cancel_with.name
			]
			self.execute(*args)
	
	
	def button_release(self, mapper):
		if self.show_with_release:
			self.execute(mapper, '-x',
				'-x', str(self.x), '-y', str(self.y)
			)
	
	
	def whole(self, mapper, x, y, what):
		if x == 0 and y == 0:
			# Sent when pad is released - don't display menu then
			return
		if what in (LEFT, RIGHT):
			if what == LEFT:
				confirm, cancel = "LPAD", SCButtons.LPADTOUCH
			else:
				confirm, cancel = "RPAD", SCButtons.RPADTOUCH
			if not mapper.was_pressed(cancel):
				self.execute(mapper,
					'--control-with', what,
					'-x', str(self.x), '-y', str(self.y),
					'--use-cursor',
					'--confirm-with', confirm,
					'--cancel-with', cancel.name
				)
		if what == STICK:
			# Special case, menu is displayed only if is moved enought
			distance = sqrt(x*x + y*y)
			if self._stick_distance < MenuAction.MIN_STICK_DISTANCE and distance > MenuAction.MIN_STICK_DISTANCE:
				self.execute(mapper,
					'--control-with', STICK,
					'-x', str(self.x), '-y', str(self.y),
					'--use-cursor',
					'--confirm-with', "STICKPRESS",
					'--cancel-with', STICK
				)
			self._stick_distance = distance


class GridMenuAction(MenuAction):
	"""
	Same as menu, but displayed in grid
	"""
	COMMAND = "gridmenu"
	MENU_TYPE = "gridmenu"


class RadialMenuAction(MenuAction):
	"""
	Same as grid menu, which is same as menu but displayed in grid,
	but displayed as circle.
	"""
	COMMAND = "radialmenu"
	MENU_TYPE = "radialmenu"


class KeyboardAction(Action, SpecialAction):
	"""
	Shows OSD keyboard.
	"""
	SA = COMMAND = "keyboard"
	
	def __init__(self):
		Action.__init__(self)
	
	
	def describe(self, context):
		if self.name: return self.name
		if context == Action.AC_OSD:
			return _("Display Keyboard")
		return _("OSD Keyboard")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)
	
	
	def button_release(self, mapper):
		self.execute(mapper)


class PositionModifier(Modifier):
	"""
	Sets position for OSD menu.
	"""
	COMMAND = "position"
	
	def _mod_init(self, x, y):
		self.position = (x, y)
	
	
	def compress(self):
		if isinstance(self.action, MenuAction):
			self.action.x, self.action.y = self.position
		return self.action
	
	
	def encode(self):
		rv = Modifier.encode(self)
		rv[PositionModifier.COMMAND] = self.position
		return rv
	
	
	@staticmethod
	def decode(data, a, *b):
		x, y = data[PositionModifier.COMMAND]
		return PositionModifier(x, y, a)
	
	
	def describe(self, context):
		return self.action.describe(context)
