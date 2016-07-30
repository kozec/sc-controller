#!/usr/bin/env python2
"""
Imports VDF profile and converts it to Profile object.
"""
from scc.uinput import Keys, Axes, Rels
from scc.modifiers import SensitivityModifier, ClickModifier, FeedbackModifier
from scc.modifiers import BallModifier, DoubleclickModifier, HoldModifier
from scc.actions import NoAction, ButtonAction, DPadAction, XYAction, TriggerAction
from scc.actions import HatUpAction, HatDownAction, HatLeftAction, HatRightAction
from scc.actions import CircularAction, MouseAction, AxisAction, MultiAction
from scc.constants import SCButtons, HapticPos, TRIGGER_CLICK, YAW, ROLL
from scc.parser import ActionParser, ParseError
from scc.profile import Profile
from scc.lib.vdf import parse_vdf, ensure_list

import logging
log = logging.getLogger("import.vdf")

class VDFProfile(Profile):
	BUTTON_TO_BUTTON = {
		# maps button keys from vdf file to SCButtons constants
		'button_a'			: SCButtons.A,
		'button_b'			: SCButtons.B,
		'button_x'			: SCButtons.X,
		'button_y'			: SCButtons.Y,
		'button_back_left'	: SCButtons.LGRIP,
		'button_back_right'	: SCButtons.RGRIP,
		'button_menu'		: SCButtons.BACK,
		'button_escape'		: SCButtons.START,	# what what what
		'left_bumper'		: SCButtons.LB,
		'right_bumper'		: SCButtons.RB,
		'left_click'		: SCButtons.LPAD,
		'right_click'		: SCButtons.RPAD,
	}
	
	SPECIAL_KEYS = {
		# Maps some key names from vdf file to Keys.* constants.
		# Rest of key names are converted in convert_key_name.
		'FORWARD_SLASH' : Keys.KEY_SLASH,
		'VOLUME_DOWN' : Keys.KEY_VOLUMEDOWN,
		'VOLUME_UP' : Keys.KEY_VOLUMEUP,
		'NEXT_TRACK' : Keys.KEY_NEXTSONG,
		'PREV_TRACK' : Keys.KEY_PREVIOUSSONG,
		'PAGE_UP' : Keys.KEY_PAGEUP,
		'PAGE_DOWN' : Keys.KEY_PAGEDOWN,
		'SINGLE_QUOTE' : Keys.KEY_APOSTROPHE,
		'RETURN' : Keys.KEY_ENTER,
		'ESCAPE' : Keys.KEY_ESC,
		'PERIOD' : Keys.KEY_DOT,
	}
	
	SPECIAL_BUTTONS = {
		# As SPECIAL_KEYS, but for buttons.
		'shoulder_left' : Keys.BTN_TL,
		'shoulder_right' : Keys.BTN_TR,
		'joystick_left' : Keys.BTN_THUMBL,
		'joystick_right' : Keys.BTN_THUMBR,
		'trigger_left' : Keys.BTN_TL2,
		'trigger_right' : Keys.BTN_TR2,
	}
	
	
	def __init__(self):
		Profile.__init__(self, ActionParser())
		self.name = "Unnamed"
	
	
	@staticmethod
	def parse_action(lst_or_str):
		"""
		Parses action from vdf file. a_string can be either string or list of
		strings, in which case MultiAction is returned.
		
		Returns Action instance or ParseError if action is not recognized.
		"""
		if type(lst_or_str) == list:
			return MultiAction.make(*[ VDFProfile.parse_action(x) for x in lst_or_str ])
		# Split string into binding type, name and parameters
		binding, params = lst_or_str.split(" ", 1)
		if "," in params:
			params, name = params.split(",", 1)
		else:
			params, name = params, None
		params = params.split(" ")
		if name:
			name = name.strip()
		# Return apropriate Action for binding type
		if binding in ("key_press", "mouse_button"):
			if binding == "mouse_button":
				b = VDFProfile.convert_button_name(params[0])
			else:
				b = VDFProfile.convert_key_name(params[0])
			return ButtonAction(b).set_name(name)
		elif binding == "xinput_button":
			# Special cases, as dpad is apparently button on Windows
			b = params[0].strip().lower()
			if b == "dpad_up":
				return HatUpAction(Axes.ABS_HAT0Y)
			elif b == "dpad_down":
				return HatDownAction(Axes.ABS_HAT0Y)
			elif b == "dpad_left":
				return HatLeftAction(Axes.ABS_HAT0X)
			elif b == "dpad_right":
				return HatRightAction(Axes.ABS_HAT0X)
			else:
				b = VDFProfile.convert_button_name(b)
				return ButtonAction(b).set_name(name)
		elif binding in ("mode_shift", "controller_action"):
			# TODO: This gonna be fun
			log.warning("Ignoring '%s' binding" % (binding,))
			return NoAction()
		elif binding == "mouse_wheel":
			if params[0].lower() == "scroll_down":
				return MouseAction(Rels.REL_WHEEL, -1)
			else:
				return MouseAction(Rels.REL_WHEEL, 1)
		else:
			raise ParseError("Unknown binding: '%s'" % (binding,))
	
	
	@staticmethod
	def parse_modifiers(group, action, side):
		"""
		If passed group or activator has 'settings' key, converts known
		settings to one or more Modifier.
		
		Returns resulting Action
		"""
		if "settings" in group:
			settings = group["settings"]
			sens = 1.0, 1.0, 1.0
			if "sensitivity" in settings:
				s = float(settings["sensitivity"]) / 100.0
				sens = s, s, s
			if "haptic_intensity" in settings:
				action = FeedbackModifier(
					HapticPos.LEFT if side == Profile.LEFT else HapticPos.RIGHT,
					1024 * int(settings["haptic_intensity"]), action)
			if "invert_x" in settings and int(settings["invert_x"]):
				sens = -1.0 * sens[0], sens[1], sens[2]
			if "invert_y" in settings and int(settings["invert_y"]):
				sens = sens[0], -1.0 * sens[1], sens[2]
			if "invert_z" in settings and int(settings["invert_z"]):
				sens = sens[0], sens[1], -1.0 * sens[2]
			
			if sens != (1.0, 1.0, 1.0):
				action = SensitivityModifier(sens[0], sens[1], sens[2], action)
			
		
		return action
	
	
	@staticmethod
	def convert_key_name(name):
		"""
		Converts keys names used in vdf profiles to Keys.KEY_* constants.
		"""
		if name in VDFProfile.SPECIAL_KEYS:
			return VDFProfile.SPECIAL_KEYS[name]
		elif name.endswith("_ARROW"):
			key = "KEY_%s" % (name[:-6],)
		elif "KEYPAD_" in name:
			key = "KEY_%s" % (name.replace("KEYPAD_", "KP"),)
		elif "LEFT_" in name:
			key = "KEY_%s" % (name.replace("LEFT_", "LEFT"),)
		elif "RIGHT_" in name:
			key = "KEY_%s" % (name.replace("LEFT_", "RIGHT"),)
		else:
			key = "KEY_%s" % (name,)
		if hasattr(Keys, key):
			return getattr(Keys, key)
		raise ParseError("Unknown key: '%s'" % (name,))
	
	
	@staticmethod
	def convert_button_name(name):
		"""
		Converts button names used in vdf profiles to Keys.BTN_* constants.
		"""
		if name.lower() in VDFProfile.SPECIAL_BUTTONS:
			return VDFProfile.SPECIAL_BUTTONS[name.lower()]
		key = "BTN_%s" % (name.upper(),)
		if hasattr(Keys, key):
			return getattr(Keys, key)
		raise ParseError("Unknown button: '%s'" % (name,))	
	
	
	@staticmethod
	def parse_button(dct_or_str):
		"""
		Parses button definition from vdf file.
		Parameter can be either string, as used in v2, or dict used in v3.
		"""
		if type(dct_or_str) == str:
			# V2
			return VDFProfile.parse_action(dct_or_str)
		elif "activators" in dct_or_str:
			# V3
			act_actions = []
			for k in ("full_press", "double_press", "long_press"):
				a = NoAction()
				if k in dct_or_str["activators"]:
					# TODO: Handle multiple bindings
					bindings = ensure_list(dct_or_str["activators"][k])[0]
					a = VDFProfile.parse_action(bindings["bindings"]["binding"])
					a = VDFProfile.parse_modifiers(bindings, a, Profile.RIGHT)
					# holly...
				act_actions.append(a)
			normal, double, hold = act_actions
			if not double and not hold:
				return normal
			elif hold and not double:
				return HoldModifier(hold, normal)
			else:
				action = DoubleclickModifier(double, normal)
				action.holdaction = hold
				return action
		else:
			raise ParseError("WTF")
	
	
	@staticmethod
	def get_inputs(group):
		"""
		Returns 'inputs' or 'bindings', whichever exists in passed group.
		If neither exists, return None.
		"""
		if "inputs" in group:
			return group["inputs"]
		if "bindings" in group:
			return group["bindings"]
		return {}
	
	
	@staticmethod
	def find_group(data, id):
		""" Returns group with specified ID or None """
		for g in ensure_list(data["group"]):
			if "id" in g and g["id"] == id:
				return g
		return None
	
	
	def parse_group(self, group, side):
		"""
		Parses output (group) from vdf profile.
		Returns Action.
		"""
		if not "mode" in group:
			raise ParseError("Group without mode")
		mode = group["mode"]
		inputs = VDFProfile.get_inputs(group)
		
		settings = group["settings"] if "settings" in group else {}
		for o in ("output_trigger", "output_joystick"):
			if o in settings:
				if int(settings[o]) <= 1:
					side = Profile.LEFT
				else:
					side = Profile.RIGHT
		
		if mode == "dpad":
			keys = []
			for k in ("dpad_north", "dpad_south", "dpad_east", "dpad_west"):
				if k in inputs:
					keys.append(VDFProfile.parse_button(inputs[k]))
				else:
					keys.append(NoAction())
			action = DPadAction(*keys)
		elif mode == "joystick_move":
			if side == Profile.LEFT:
				# Left
				action = XYAction(AxisAction(Axes.ABS_X), AxisAction(Axes.ABS_Y))
			else:
				# Right
				action = XYAction(AxisAction(Axes.ABS_RX), AxisAction(Axes.ABS_RY))
		elif mode == "absolute_mouse":
			if "click" in inputs:
				if side == Profile.LEFT:
					self.buttons[SCButtons.LPAD] = VDFProfile.parse_button(inputs["click"])
				else:
					self.buttons[SCButtons.RPAD] = VDFProfile.parse_button(inputs["click"])
			if "gyro_axis" in settings:
				if int(settings["gyro_axis"]) == 1:
					action = MouseAction(ROLL)
				else:
					action = MouseAction(YAW)
			else:
				action = MouseAction()
		elif mode == "mouse_wheel":
			action = BallModifier(XYAction(MouseAction(Rels.REL_HWHEEL),
			 	ouseAction(Rels.REL_WHEEL)))
		elif mode == "trigger":
			actions = []
			if "click" in inputs:
				actions.append(TriggerAction(TRIGGER_CLICK,
					VDFProfile.parse_button(inputs["click"])))
			
			if side == Profile.LEFT:
				actions.append(AxisAction(Axes.ABS_Z))
			else:
				actions.append(AxisAction(Axes.ABS_RZ))
			
			action = MultiAction.make(*actions)
		else:
			raise ParseError("Unknown mode: '%s'" % (group["mode"],))
		
		action = VDFProfile.parse_modifiers(group, action, side)
		return action
	
	
	def parse_switches(self, group):
		""" Used for special cases of input groups that contains buttons """
		inputs = VDFProfile.get_inputs(group)
		for button in inputs:
			if button not in VDFProfile.BUTTON_TO_BUTTON:
				raise ParseError("Unknown button: '%s'" % (button,))
			b = VDFProfile.BUTTON_TO_BUTTON[button]
			self.buttons[b] = VDFProfile.parse_button(inputs[button])
	
	
	def parse_input_binding(self, data, group_id, binding):
		group = VDFProfile.find_group(data, group_id)
		if group and "mode" in group:
			if binding.startswith("switch"):
				self.parse_switches(group)
			elif binding.startswith("button_diamond"):
				self.parse_switches(group)
			elif binding.startswith("left_trackpad"):
				self.pads[Profile.LEFT] = self.parse_group(group, Profile.LEFT)
			elif binding.startswith("right_trackpad"):
				self.pads[Profile.RIGHT] = self.parse_group(group, Profile.RIGHT)
			elif binding.startswith("left_trigger"):
				self.triggers[Profile.LEFT] = self.parse_group(group, Profile.LEFT)
			elif binding.startswith("right_trigger"):
				self.triggers[Profile.RIGHT] = self.parse_group(group, Profile.RIGHT)
			elif binding.startswith("joystick"):
				self.stick = self.parse_group(group, Profile.LEFT)
			elif binding.startswith("gyro"):
				self.gyro = self.parse_group(group, Profile.LEFT)
			else:
				raise ParseError("Unknown source: '%s'" % (binding,))
	
	
	def load(self, filename):
		"""
		Loads profile from vdf file. Returns self.
		May raise ValueError.
		"""
		data = parse_vdf(open(filename, "r"))
		if 'controller_mappings' not in data:
			raise ValueError("Invalid profile file")
		data = data['controller_mappings']
		if 'title' in data:
			name = data['title'].strip()
			if name:
				self.name = name
		presets = ensure_list(data['preset'])
		for p in presets:
			if not 'group_source_bindings' in p:
				continue
			gsb = p['group_source_bindings']
			for group_id in gsb:
				if not gsb[group_id].endswith("inactive"):
					self.parse_input_binding(data, group_id, gsb[group_id])
			
			if "switch_bindings" in p:
				self.parse_switches(p['switch_bindings'])
			
			break	# TODO: Support for multiple presets
		
		return self


if __name__ == "__main__":
	import sys
	from scc.tools import init_logging
	init_logging()
	f = VDFProfile().load(sys.argv[1])
	f.save("output.sccprofile")

