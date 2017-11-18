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
from scc.constants import STICK_PAD_MAX, DEFAULT
from scc.actions import Action, NoAction, SpecialAction, ButtonAction
from scc.actions import HapticEnabledAction, OSDEnabledAction
from scc.actions import MOUSE_BUTTONS
from scc.tools import strip_gesture, nameof, clamp
from scc.modifiers import Modifier, NameModifier
from math import sqrt

import sys, time, logging
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
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_OSD
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s('%s')" % (self.COMMAND,
				self.profile.encode('utf-8').encode('string_escape'))
	
	
	def button_release(self, mapper):
		# Execute only when button is released (executing this when button
		# is pressed would send following button_release event to another
		# action from loaded profile)
		self.execute(mapper)
	
	
	def whole(self, mapper, *a):
		self.execute(mapper)


class ShellCommandAction(Action, SpecialAction):
	SA = COMMAND = "shell"
	
	def __init__(self, command):
		Action.__init__(self, command)
		self.command = command
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Execute Command")
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_OSD
	
	
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
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_OSD
	
	
	def button_release(self, mapper):
		# Execute only when button is released (executing this when button
		# is pressed would hold stuck any other action bound to same button,
		# as button_release is not sent after controller turns off)
		self.execute(mapper)
	
	
	def whole(self, mapper, *a):
		self.execute(mapper)


class RestartDaemonAction(Action, SpecialAction):
	SA = COMMAND = "restart"
	
	def __init__(self):
		Action.__init__(self)
	
	def describe(self, context):
		if self.name: return self.name
		return _("Restart SCC-Daemon")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)
	
	
	def button_release(self, mapper):
		# Execute only when button is released (for same reason as
		# TurnOffAction does)
		self.execute(mapper)


class LedAction(Action, SpecialAction):
	SA = COMMAND = "led"
	
	def __init__(self, brightness):
		Action.__init__(self, brightness)
		self.brightness = clamp(0, int(brightness), 100)
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Set LED brightness")
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_OSD
	
	
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
	
	
	def get_compatible_modifiers(self):
		if self.action:
			return self.action.get_compatible_modifiers()
		return 0
	
	
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
			p0str = self.parameters[0].to_string(multiline=multiline, pad=pad)
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


class MenuAction(Action, SpecialAction, HapticEnabledAction):
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
					confirm_with=DEFAULT, cancel_with=DEFAULT,
					show_with_release=False, size = 0):
		if control_with == SAME:
			# Little touch of backwards compatibility
			control_with, confirm_with = self.DEFAULT_CONTROL, SAME
		if type(control_with) == int:
			# Allow short form in case when menu is assigned to pad
			# eg.: menu("some-id", 3) sets size to 3
			control_with, size = MenuAction.DEFAULT_CONTROL, control_with
		Action.__init__(self, menu_id, control_with, confirm_with, cancel_with, show_with_release, size)
		HapticEnabledAction.__init__(self)
		self.menu_id = menu_id
		self.control_with = control_with
		self.confirm_with = confirm_with
		self.cancel_with = cancel_with
		self.size = size
		self.x, self.y = MenuAction.DEFAULT_POSITION
		self.show_with_release = bool(show_with_release)
		self._stick_distance = 0
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Menu")
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_FEEDBACK
	
	
	def to_string(self, multiline=False, pad=0):
		if self.control_with in (self.DEFAULT_CONTROL, DEFAULT):
			dflt = (DEFAULT, DEFAULT, False)
			vals = (self.confirm_with, self.cancel_with, self.show_with_release)
			if dflt == vals:
				# Special case when menu is assigned to pad 
				if self.size == 0:
					return "%s%s('%s')" % (" " * pad, self.COMMAND, self.menu_id)
				else:
					return "%s%s('%s', %s)" % (" " * pad, self.COMMAND, self.menu_id, self.size)
		
		return "%s%s(%s)" % (
			" " * pad,
			self.COMMAND,
			",".join(Action.encode_parameters(self.strip_defaults()))
		)
	
	
	def get_previewable(self):
		return True
	
	
	def button_press(self, mapper):
		if not self.show_with_release:
			confirm_with = self.confirm_with
			cancel_with = self.cancel_with
			args = [ mapper ]
			if confirm_with == SAME:
				confirm_with = mapper.get_pressed_button() or self.DEFAULT_CONFIRM
			elif confirm_with == DEFAULT:
				confirm_with = MenuAction.DEFAULT_CONFIRM
			if cancel_with == DEFAULT:
				cancel_with = MenuAction.DEFAULT_CANCEL
			if nameof(self.control_with) in (LEFT, RIGHT):
				args += [ '--use-cursor' ]
			args += [
				'--control-with', nameof(self.control_with),
				'-x', str(self.x), '-y', str(self.y),
				'--size', str(self.size),
				'--confirm-with', nameof(confirm_with),
				'--cancel-with', nameof(cancel_with)
			]
			self.execute(*args)
	
	
	def button_release(self, mapper):
		if self.show_with_release:
			self.execute(mapper, '-x', str(self.x), '-y', str(self.y))
	
	
	def whole(self, mapper, x, y, what, *params):
		if x == 0 and y == 0:
			# Sent when pad is released - don't display menu then
			return
		if self.haptic:
			params = list(params) + [
				"--feedback-amplitude",
				str(self.haptic.get_amplitude())
			]
		if what in (LEFT, RIGHT):
			confirm_with = self.confirm_with
			cancel_with = self.cancel_with
			if what == LEFT:
				if confirm_with == DEFAULT: confirm_with = SCButtons.LPAD
				if cancel_with == DEFAULT:  cancel_with  = SCButtons.LPADTOUCH
			elif what == RIGHT:
				if confirm_with == DEFAULT: confirm_with = SCButtons.RPAD
				if cancel_with == DEFAULT:  cancel_with  = SCButtons.RPADTOUCH
			else:
				# Stick
				if confirm_with == DEFAULT: confirm_with = SCButtons.STICKPRESS
				if cancel_with == DEFAULT:  cancel_with  = SCButtons.B
			if not mapper.was_pressed(cancel_with):
				self.execute(mapper,
					'--control-with', what,
					'-x', str(self.x), '-y', str(self.y),
					'--use-cursor',
					'--size', str(self.size),
					'--confirm-with', nameof(confirm_with),
					'--cancel-with', nameof(cancel_with),
					*params
				)
		if what == STICK:
			# Special case, menu is displayed only if is moved enought
			distance = sqrt(x*x + y*y)
			if self._stick_distance < MenuAction.MIN_STICK_DISTANCE and distance > MenuAction.MIN_STICK_DISTANCE:
				self.execute(mapper,
					'--control-with', STICK,
					'-x', str(self.x), '-y', str(self.y),
					'--use-cursor',
					'--size', str(self.size),
					'--confirm-with', "STICKPRESS",
					'--cancel-with', STICK,
					*params
				)
			self._stick_distance = distance


class HorizontalMenuAction(MenuAction):
	"""
	Same as menu, but packed as row
	"""
	COMMAND = "hmenu"
	MENU_TYPE = "hmenu"


class GridMenuAction(MenuAction):
	"""
	Same as menu, but displayed in grid
	"""
	COMMAND = "gridmenu"
	MENU_TYPE = "gridmenu"


class QuickMenuAction(MenuAction):
	"""
	Quickmenu. Max.6 items, controller by buttons
	"""
	COMMAND = "quickmenu"
	MENU_TYPE = "quickmenu"
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("QuickMenu")
	
	
	def button_press(self, mapper):
		# QuickMenu is always shown with release
		pass
	
	
	def button_release(self, mapper):
		self.execute(mapper, '-x', str(self.x), '-y', str(self.y))



class RadialMenuAction(MenuAction):
	"""
	Same as grid menu, which is same as menu but displayed in grid,
	but displayed as circle.
	"""
	COMMAND = "radialmenu"
	MENU_TYPE = "radialmenu"
	DEFAULT_CONFIRM = SCButtons.A
	DEFAULT_CANCEL = SCButtons.B
	DEFAULT_CONTROL = STICK
	
	def __init__(self, menu_id, control_with=DEFAULT_CONTROL,
					confirm_with=DEFAULT, cancel_with=DEFAULT,
					show_with_release=False, size = 0):
		MenuAction.__init__(self, menu_id, control_with, confirm_with,
						cancel_with, show_with_release, size)
		self.rotation = 0
	
	
	def whole(self, mapper, x, y, what):
		if self.rotation:
			MenuAction.whole(self, mapper, x, y, what, "--rotation", self.rotation)
		else:
			MenuAction.whole(self, mapper, x, y, what)
	
	
	def set_rotation(self, angle):
		self.rotation = angle
	
	
	def get_compatible_modifiers(self):
		return MenuAction.get_compatible_modifiers(self) or Action.MOD_ROTATE


class DialogAction(Action, SpecialAction):
	"""
	Dialog is actually kind of menu, but options for it are different.
	"""
	SA = COMMAND = "dialog"
	DEFAULT_CONFIRM = SCButtons.A
	DEFAULT_CANCEL = SCButtons.B
	DEFAULT_POSITION = 10, -10
	
	def __init__(self, *pars):
		Action.__init__(self, pars)
		
		self.options = []
		self.confirm_with = DialogAction.DEFAULT_CONFIRM
		self.cancel_with  = DialogAction.DEFAULT_CANCEL
		self.text = _("Dialog")
		self.x, self.y = MenuAction.DEFAULT_POSITION
		# First and 2nd parameter may be confirm and cancel button
		if len(pars) > 0 and pars[0] in SCButtons:
			self.confirm_with, pars = pars[0], pars[1:]
			if len(pars) > 0 and pars[0] in SCButtons:
				self.cancel_with, pars = pars[0], pars[1:]
		# 1st always present argument is title
		if len(pars) > 0:
			self.text, pars = pars[0], pars[1:]
		# ... everything else are actions
		self.options = pars
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Dialog")
	
	
	def to_string(self, multiline=False, pad=0):
		rv = "%s%s(" % (" " * pad, self.COMMAND)
		if self.confirm_with not in (DialogAction.DEFAULT_CONFIRM, DEFAULT):
			rv += "%s, " % (nameof(self.confirm_with),)
			if self.cancel_with not in (DialogAction.DEFAULT_CANCEL, DEFAULT):
				rv += "%s, " % (nameof(self.cancel_with),)
		rv += "'%s', " % (self.text.encode('string_escape'),)
		if multiline:
			rv += "\n%s" % (" " * (pad + 2))
		for option in self.options:
			rv += "%s, " % (option.to_string(False),)
			if multiline:
				rv += "\n%s" % (" " * (pad + 2))
		
		rv = rv.strip("\n ,")
		if multiline:
			rv += "\n)"
		else:
			rv += ")"
		return rv
	
	
	def get_previewable(self):
		return False
	
	
	def button_release(self, mapper):
		confirm_with = self.confirm_with
		cancel_with = self.cancel_with
		args = [ mapper ]
		if confirm_with == DEFAULT:
			confirm_with = MenuAction.DEFAULT_CONFIRM
		if cancel_with == DEFAULT:
			cancel_with = MenuAction.DEFAULT_CANCEL
		args += [
			'-x', str(self.x), '-y', str(self.y),
			'--confirm-with', nameof(confirm_with),
			'--cancel-with', nameof(cancel_with),
			'--text', self.text,
		]
		for x in self.options:
			args.append(x)
		self.execute(*args)


class KeyboardAction(Action, SpecialAction):
	"""
	Shows OSD keyboard.
	"""
	SA = COMMAND = "keyboard"
	
	def __init__(self):
		Action.__init__(self)
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_POSITION
	
	
	def describe(self, context):
		if self.name: return self.name
		if context == Action.AC_OSD:
			return _("Display Keyboard")
		return _("OSD Keyboard")
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s()" % (self.COMMAND,)
	
	
	def button_press(self, mapper):
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


class GesturesAction(Action, OSDEnabledAction, SpecialAction):
	"""
	Stars gesture detection on pad. Recognition is handled by whatever
	is special_actions_handler and results are then sent back to this action
	as parameter of gesture() method.
	"""
	SA = COMMAND = "gestures"
	PROFILE_KEYS = ("gestures",)
	PROFILE_KEY_PRIORITY = 2
	
	def __init__(self, *stuff):
		OSDEnabledAction.__init__(self)
		Action.__init__(self, *stuff)
		self.gestures = {}
		gstr = None
		for i in stuff:
			if gstr is None and type(i) in (str, unicode):
				gstr = i
			elif gstr is not None and isinstance(i, Action):
				self.gestures[gstr] = i
				gstr = None
			else:
				raise ValueError("Invalid parameter for '%s': unexpected %s" % (
						self.COMMAND, i))
	
	
	def get_compatible_modifiers(self):
		return Action.MOD_OSD
	
	
	def describe(self, context):
		if self.name: return self.name
		return _("Gestures")
	
	
	def to_string(self, multiline=False, pad=0):
		if multiline:
			rv = [ (" " * pad) + self.COMMAND + "(" ]
			for gstr in self.gestures:
				a_str = self.gestures[gstr].to_string(True).split("\n")
				a_str[0] = (" " * pad) + "  '" + (gstr + "',").ljust(11) + a_str[0]	# Key has to be one of SCButtons
				for i in xrange(1, len(a_str)):
					a_str[i] = (" " * pad) + "  " + a_str[i]
				a_str[-1] = a_str[-1] + ","
				rv += a_str
			if rv[-1][-1] == ",":
				rv[-1] = rv[-1][0:-1]
			rv += [ (" " * pad) + ")" ]
			return "\n".join(rv)
		else:
			rv = [ ]
			for gstr in self.gestures:
				rv += [ "'%s'" % (gstr,), self.gestures[gstr].to_string(False) ]
			return self.COMMAND + "(" + ", ".join(rv) + ")"	
	
	
	def encode(self):
		rv = { self.COMMAND : {
			gstr : self.gestures[gstr].encode()
			for gstr in self.gestures
		}}
		if self.name:
			rv[NameModifier.COMMAND] = self.name
		return rv	
	
	
	def compress(self):
		for gstr in self.gestures:
			a = self.gestures[gstr].compress()
			if "i" in gstr:
				del self.gestures[gstr]
				gstr = strip_gesture(gstr)
			self.gestures[gstr] = a
		return self
	
	
	@staticmethod
	def decode(data, a, parser, *b):
		args = []
		ga = GesturesAction()
		ga.gestures = {
			gstr : parser.from_json_data(data[GesturesAction.PROFILE_KEYS[0]][gstr])
			for gstr in data[GesturesAction.PROFILE_KEYS[0]]
		}
		if "name" in data:
			ga.name = data["name"]
		if "osd" in data:
			ga = OSDAction(ga)
		return ga
	
	
	def gesture(self, mapper, gesture_string):
		action = None
		if gesture_string in self.gestures:
			action = self.gestures[gesture_string]
		else:
			sgstr = strip_gesture(gesture_string)
			if sgstr in self.gestures:
				action = self.gestures[sgstr]
		if action:
			action.button_press(mapper)
			mapper.schedule(0, action.button_release)
	
	
	def whole(self, mapper, x, y, what):
		if (x, y) != (0, 0):
			# (0, 0) singlanizes released touchpad
			self.execute(mapper, x, y, what)


# Register actions from current module
Action.register_all(sys.modules[__name__])
