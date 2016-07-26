#!/usr/bin/env python2
"""
Imports VDF profile and converts it to Profile object.
"""
from scc.uinput import Keys, Axes, Rels
from scc.modifiers import SensitivityModifier, ClickModifier, DoubleclickModifier, HoldModifier
from scc.actions import NoAction, ButtonAction, DPadAction, XYAction
from scc.actions import CircularAction, MouseAction, AxisAction
from scc.parser import ActionParser, ParseError
from scc.constants import SCButtons
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
		'button_back_right'	: SCButtons.BACK,
		'button_back_left'	: SCButtons.BACK,	# what?
		'button_menu'		: SCButtons.START,
		'button_escape'		: SCButtons.BACK,	# what what what
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
	
	
	def __init__(self):
		Profile.__init__(self, ActionParser())
	
	
	@staticmethod
	def parse_vdf_action(string):
		"""
		Parses action from vdf file.
		Returns Action instance or ParseError if action is not recognized.
		"""
		# Split string into binding type, name and parameters
		binding, params = string.split(" ", 1)
		if "," in params:
			params, name = params.split(",", 1)
		else:
			params, name = params, None
		params = params.split(" ")
		# Return apropriate Action for binding type
		if binding in ("key_press", "mouse_button"):
			if binding == "mouse_button":
				b = VDFProfile.convert_button_name(params[0])
			else:
				b = VDFProfile.convert_key_name(params[0])
			return ButtonAction(b).set_name(name)
		if binding in ("mode_shift", "controller_action"):
			# TODO: This gonna be fun
			log.warning("Ignoring '%s' binding" % (binding,))
			return NoAction()
		else:
			raise ParseError("Unknown binding: '%s'" % (binding,))
	
	
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
		key = "BTN_%s" % (name,)
		if hasattr(Keys, key):
			return getattr(Keys, key)
		raise ParseError("Unknown button: '%s'" % (name,))	
	
	
	@staticmethod
	def parse_vdf_button(dct_or_str):
		"""
		Parses button definition from vdf file.
		Parameter can be either string, as used in v2, or dict used in v3
		of vcf profiles.
		"""
		if type(dct_or_str) == str:
			# V2
			return VDFProfile.parse_vdf_action(dct_or_str)
		elif "activators" in dct_or_str:
			# V3
			act_actions = []
			for k in ("Full_Press", "Double_Press", "Long_Press"):
				a = NoAction()
				if k in dct_or_str["activators"]:
					# TODO: Handle multiple bindings
					bindings = ensure_list(dct_or_str["activators"][k])[0]
					a = VDFProfile.parse_vdf_action(bindings["bindings"]["binding"])
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
	def get_inputs(grp):
		"""
		Returns 'inputs' or 'bindings', whichever exists in passed group.
		If neither exists, return None.
		"""
		if "inputs" in grp:
			return grp["inputs"]
		if "bindings" in grp:
			return grp["bindings"]
		return None
	
	
	def load(self, filename):
		"""
		Loads profile from vdf file. Returns self.
		May raise ValueError.
		"""
		data = parse_vdf(open(filename, "r"))
		if 'controller_mappings' not in data:
			raise ValueError("Invalid profile file")
		data = data['controller_mappings']
		groups = ensure_list(data['group'])
		for grp in groups:
			action = NoAction()
			# Parse action
			mode = grp["mode"]
			if mode in ("switches", "four_buttons"):
				# ABXY and other buttons
				inputs = VDFProfile.get_inputs(grp)
				if not inputs: continue
				for b in inputs:
					if b.lower() in VDFProfile.BUTTON_TO_BUTTON:
						scc_b = VDFProfile.BUTTON_TO_BUTTON[b.lower()]
						action = VDFProfile.parse_vdf_button(inputs[b])
						self.buttons[scc_b] = action
					else:
						raise ValueError("Unknown button: '%s'" % (b,))
				# Don't parse rest, it bears no meaning here
				continue
			elif mode == "absolute_mouse":
				action = MouseAction()
			elif mode == "joystick_move":
				action = XYAction(AxisAction(Axes.ABS_X), AxisAction(Axes.ABS_Y))
			elif mode == "dpad":
				# Left or right pad
				inputs = VDFProfile.get_inputs(grp)
				if not inputs: continue
				keys = []
				for k in ("dpad_north", "dpad_south", "dpad_east", "dpad_west"):
					if k in inputs:
						keys.append(VDFProfile.parse_vdf_button(inputs[k]))
					else:
						keys.append(NoAction())
				action = DPadAction(*keys)
			elif mode == "trigger":
				half, full = NoAction(), NoAction()
				inputs = VDFProfile.get_inputs(grp)
				if not inputs: continue
				if "click" in inputs:
					full_action = VDFProfile.parse_vdf_button(inputs["click"])
				# TODO: Half-pressed trigger here
				action = full
			elif mode == "scrollwheel":
				# TODO: Here I'm just assuming that nothing else can be set,
				# mainly because SCC can't handle much more
				log.warning("Ignoring settings for scrollwheel, CircularAction assumed")
				action = CircularAction(Rels.REL_WHEEL)
			elif mode in ("mouse_region", "touch_menu"):
				# TODO: This. Don't have example yet
				log.warning("Ignoring mode '%s'", mode)
			else:
				raise ParseError("Unknown mode: '%s'" % (mode,))
			
			# Parse modifiers
			if "settings" in grp:
				settings = grp["settings"]
				if "sensitivity" in settings:
					sens = float(settings["sensitivity"]) / 100.0
					action = SensitivityModifier(sens, sens, sens, action)
				if "requires_click" in settings and settings["requires_click"] == "1":
					action = ClickModifier(action)
			
			# Parse target
			if "preset" in data:
				targets = ensure_list(data["preset"])[0]["group_source_bindings"]
			else:
				targets = data['group_source_bindings']
			if grp['id'] not in targets:
				# TODO: Handle multiple presets
				continue
			target = targets[grp['id']]
			# TODO: WTF is'joystick active' & co?
			if target.startswith("joystick"):
				self.stick = action
			elif target.startswith("left_trackpad"):
				self.pads[Profile.LEFT] = action
			elif target.startswith("right_trackpad"):
				self.pads[Profile.RIGHT] = action
			elif target.startswith("left_trigger"):
				self.triggers[Profile.LEFT] = action
			elif target.startswith("right_trigger"):
				self.triggers[Profile.RIGHT] = action
			else:
				raise ParseError("Unknown target: '%s'" % (target,))
		
		print self.stick
		print self.pads[Profile.LEFT]
		print self.pads[Profile.RIGHT]



if __name__ == "__main__":
	import sys
	from scc.tools import init_logging
	init_logging()
	f = VDFProfile().load(sys.argv[1])
