#!/usr/bin/env python2
"""
Imports VDF profile and converts it to Profile object.
"""
from scc.uinput import Keys, Axes, Rels
from scc.actions import Action, NoAction, ButtonAction, DPadAction, XYAction
from scc.actions import HatRightAction, TriggerAction, MouseAction
from scc.actions import HatUpAction, HatDownAction, HatLeftAction
from scc.actions import AxisAction, RelAreaAction, MultiAction
from scc.special_actions import ChangeProfileAction, GridMenuAction, MenuAction
from scc.modifiers import SensitivityModifier, ClickModifier, FeedbackModifier
from scc.constants import SCButtons, HapticPos, TRIGGER_CLICK, YAW, ROLL
from scc.modifiers import BallModifier, DoubleclickModifier
from scc.modifiers import HoldModifier, ModeModifier
from scc.parser import ActionParser, ParseError
from scc.menu_data import MenuData, MenuItem
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
		'DASH' : Keys.KEY_MINUS,
		'RETURN' : Keys.KEY_ENTER,
		'ESCAPE' : Keys.KEY_ESC,
		'PERIOD' : Keys.KEY_DOT,
		"LEFT_BRACKET" : Keys.KEY_LEFTBRACE,
		"RIGHT_BRACKET" : Keys.KEY_RIGHTBRACE,
		'KEYPAD_DASH' : Keys.KEY_KPMINUS,
		'KEYPAD_FORWARD_SLASH' : Keys.KEY_KPSLASH,
		'LEFT_CONTROL' : Keys.KEY_LEFTCTRL,
		'RIGHT_CONTROL' : Keys.KEY_RIGHTCTRL,
	}
	
	SPECIAL_BUTTONS = {
		# As SPECIAL_KEYS, but for buttons.
		'shoulder_left' : Keys.BTN_TL,
		'shoulder_right' : Keys.BTN_TR,
		'joystick_left' : Keys.BTN_THUMBL,
		'joystick_right' : Keys.BTN_THUMBR,
	}
	
	REGION_IMPORT_FACTOR = 0.6		# Bulgarian const.
	
	
	def __init__(self, name = "Unnamed"):
		Profile.__init__(self, ActionParser())
		self.name = name
		self.next_menu_id = 1
		self.action_set_id = 0
		self.action_sets = { 'default' : self }
		self.action_set_switches = set()
	
	
	def parse_action(self, lst_or_str, button=None):
		"""
		Parses action from vdf file. a_string can be either string or list of
		strings, in which case MultiAction is returned.
		
		Returns Action instance or ParseError if action is not recognized.
		"""
		if type(lst_or_str) == list:
			return MultiAction.make(*[ self.parse_action(x) for x in lst_or_str ])
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
			elif b == "trigger_left":
				return AxisAction(Axes.ABS_Z)
			elif b == "trigger_right":
				return AxisAction(Axes.ABS_RZ)
			else:
				b = VDFProfile.convert_button_name(b)
				return ButtonAction(b).set_name(name)
		elif binding in ("mode_shift"):
			if button is None:
				log.warning("Ignoring modeshift assigned to no button: '%s'" % (lst_or_str,))
				return NoAction()
			if button not in VDFProfile.BUTTON_TO_BUTTON:
				log.warning("Ignoring modeshift assigned to unknown button: '%s'" % (button,))
				return NoAction()
			self.modeshift_buttons[VDFProfile.BUTTON_TO_BUTTON[button]] = (
				params[1], params[0]
			)
			return NoAction()
		elif binding in ("controller_action"):
			if params[0] == "CHANGE_PRESET":
				id = int(params[1]) - 1
				cpa = ChangeProfileAction("action_set:%s" % (id,))
				self.action_set_switches.add(cpa)
				return cpa
			
			log.warning("Ignoring controller_action '%s' binding" % (params[0],))
			return NoAction()
		elif binding == "mouse_wheel":
			if params[0].lower() == "scroll_down":
				return MouseAction(Rels.REL_WHEEL, -1)
			else:
				return MouseAction(Rels.REL_WHEEL, 1)
		elif binding == "game_action":
			log.warning("Ignoring game_action binding: '%s'" % (lst_or_str,))
			return NoAction()

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
					512 * int(settings["haptic_intensity"]), 8, action)
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
			key = "KEY_%s" % (name.replace("RIGHT_", "RIGHT"),)
		else:
			key = "KEY_%s" % (name,)
		if hasattr(Keys, key):
			return getattr(Keys, key)
		if hasattr(Keys, key.upper()):
			return getattr(Keys, key.upper())
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
	
	
	def parse_button(self, bdef, button=None):
		"""
		Parses button definition from vdf file.
		Parameter can be either string, as used in v2, or dict used in v3.
		"""
		if type(bdef) == str:
			# V2
			return self.parse_action(bdef, button)
		elif type(bdef) == list:
			# V2
			return MultiAction.make(*[ self.parse_action(x, button) for x in bdef ])
		elif "activators" in bdef:
			# V3
			act_actions = []
			for k in ("full_press", "double_press", "long_press"):
				a = NoAction()
				if k in bdef["activators"]:
					# TODO: Handle multiple bindings
					bindings = ensure_list(bdef["activators"][k])[0]
					a = self.parse_action(bindings["bindings"]["binding"], button)
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
			log.warning("Failed to parse button definition: %s" % (bdef,))
	
	
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
					keys.append(self.parse_button(inputs[k]))
				else:
					keys.append(NoAction())
			action = DPadAction(*keys)
		elif mode == "four_buttons":
			keys = []
			for k in ("button_y", "button_a", "button_x", "button_b"):
				if k in inputs:
					keys.append(self.parse_button(inputs[k]))
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
		elif mode == "joystick_camera":
			output_joystick = 0
			if 'output_joystick' in settings:
				output_joystick = int(settings['output_joystick'])
			if output_joystick == 0:
				action = BallModifier(XYAction(AxisAction(Axes.ABS_X), AxisAction(Axes.ABS_Y)))
			elif output_joystick == 1:
				action = BallModifier(XYAction(AxisAction(Axes.ABS_RX), AxisAction(Axes.ABS_RY)))
			else:
				# TODO: Absolute mouse? Doesn't seems to do anything in Steam
				action = BallModifier(SensitivityModifier(0.1, 0.1, MouseAction()))
		elif mode == "mouse_joystick":
			action = BallModifier(XYAction(AxisAction(Axes.ABS_RX), AxisAction(Axes.ABS_RY)))
		elif mode == "scrollwheel":
			action = BallModifier(XYAction(MouseAction(Rels.REL_HWHEEL), MouseAction(Rels.REL_WHEEL)))
		elif mode == "touch_menu":
			# Touch menu is converted to GridMenu
			items = []
			next_item_id = 1
			for k in inputs:
				action = self.parse_button(inputs[k])
				items.append(MenuItem(
					"item_%s" % (next_item_id,),
					action.describe(Action.AC_BUTTON),
					action
				))
				next_item_id += 1
			# Menu is stored in profile, with generated ID
			menu_id = "menu_%s" % (self.next_menu_id,)
			self.next_menu_id += 1
			self.menus[menu_id] = MenuData(*items)
			
			action = GridMenuAction(menu_id,
				'LEFT' if side == Profile.LEFT else 'RIGHT',
				SCButtons.LPAD if side == Profile.LEFT else SCButtons.RPAD
			)
		elif mode == "absolute_mouse":
			if "click" in inputs:
				if side == Profile.LEFT:
					self.add_by_binding(SCButtons.LPAD,
							self.parse_button(inputs["click"]))
				else:
					self.add_by_binding(SCButtons.RPAD,
							self.parse_button(inputs["click"]))
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
					self.parse_button(inputs["click"])))
			
			if side == Profile.LEFT:
				actions.append(AxisAction(Axes.ABS_Z))
			else:
				actions.append(AxisAction(Axes.ABS_RZ))
			
			action = MultiAction.make(*actions)
		elif mode == "mouse_region":
			# Read value and assume dafaults
			scale = float(settings["scale"]) if "scale" in settings else 100.0
			x = float(settings["position_x"]) if "position_x" in settings else 50.0
			y = float(settings["position_y"]) if "position_y" in settings else 50.0
			w = float(settings["sensitivity_horiz_scale"]) if "sensitivity_horiz_scale" in settings else 100.0
			h = float(settings["sensitivity_vert_scale"]) if "sensitivity_vert_scale" in settings else 100.0
			# Apply scale
			w = w * scale / 100.0
			h = h * scale / 100.0
			# Convert to (0, 1) range
			x, y = x / 100.0, 1.0 - (y / 100.0)
			w, h = w / 100.0, h / 100.0
			# Convert to rectangle
			x1 = max(0.0, x - (w * VDFProfile.REGION_IMPORT_FACTOR))
			x2 = min(1.0, x + (w * VDFProfile.REGION_IMPORT_FACTOR))
			y1 = max(0.0, y - (h * VDFProfile.REGION_IMPORT_FACTOR))
			y2 = min(1.0, y + (h * VDFProfile.REGION_IMPORT_FACTOR))
			
			action = RelAreaAction(x1, y1, x2, y2)
		else:
			raise ParseError("Unknown mode: '%s'" % (group["mode"],))
		
		action = VDFProfile.parse_modifiers(group, action, side)
		return action
	
	
	def parse_switches(self, group):
		""" Used for special cases of input groups that contains buttons """
		inputs = VDFProfile.get_inputs(group)
		for button in inputs:
			if button in ("trigger_left", "left_trigger"):
				self.add_by_binding(
					"left_trigger",
					AxisAction(Axes.ABS_Z)
				)
			elif button in ("trigger_right", "right_trigger"):
				self.add_by_binding(
					"right_trigger",
					AxisAction(Axes.ABS_RZ)
				)
			elif button in VDFProfile.BUTTON_TO_BUTTON:
				self.add_by_binding(
					VDFProfile.BUTTON_TO_BUTTON[button],
					self.parse_button(inputs[button], button)
				)
			else:
				raise ParseError("Unknown button: '%s'" % (button,))
	
	
	def parse_input_binding(self, data, group_id, binding):
		group = VDFProfile.find_group(data, group_id)
		if group and "mode" in group:
			if binding.startswith("switch"):
				self.parse_switches(group)
			elif binding.startswith("button_diamond"):
				self.parse_switches(group)
			else:
				if binding.startswith("right_"):
					action = self.parse_group(group, Profile.RIGHT)
				else:
					action = self.parse_group(group, Profile.LEFT)
				if binding.endswith("modeshift"):
					modeshift_id = (group_id, binding.split(" ")[0])
					self.modeshifts[modeshift_id] = action
				else:
					self.set_by_binding(binding, action)
	
	
	def set_by_binding(self, binding, action):
		"""
		Sets action specified by binding, one of group_source_bindings keys
		used in vdf profile. Also supports SCButtons constants for buttons.
		
		Throws ParseError if key is not supported.
		"""
		if binding in SCButtons:
			self.buttons[binding] = action
		elif binding.startswith("left_trackpad"):
			self.pads[Profile.LEFT] = action
		elif binding.startswith("right_trackpad"):
			self.pads[Profile.RIGHT] = action
		elif binding.startswith("left_trigger"):
			self.triggers[Profile.LEFT] = action
		elif binding.startswith("right_trigger"):
			self.triggers[Profile.RIGHT] = action
		elif binding.startswith("joystick"):
			self.stick = action
		elif binding.startswith("gyro"):
			self.gyro = action
		else:
			raise ParseError("Unknown group source binding: '%s'" % (binding,))
	
	
	def add_by_binding(self, binding, action):
		"""
		As set_by_binding, but if there is alrady action for specified binding
		set, creates MultiAction.
		"""
		old = self.get_by_binding(binding)
		new = MultiAction.make(old, action)
		if isinstance(new, MultiAction):
			new = new.deduplicate()
		self.set_by_binding(binding, new)
	
	
	def get_by_binding(self, binding):
		"""
		Returns action specified by binding, one of group_source_bindings keys
		used in vdf profile. Also supports SCButtons constants for buttons.
		
		Throws ParseError if key is not supported.
		"""
		if binding in SCButtons:
			return self.buttons[binding]
		elif binding.startswith("left_trackpad"):
			return self.pads[Profile.LEFT]
		elif binding.startswith("right_trackpad"):
			return self.pads[Profile.RIGHT]
		elif binding.startswith("left_trigger"):
			return self.triggers[Profile.LEFT]
		elif binding.startswith("right_trigger"):
			return self.triggers[Profile.RIGHT]
		elif binding.startswith("joystick"):
			return self.stick
		elif binding.startswith("gyro"):
			return self.gyro
		raise ParseError("Unknown group source binding: '%s'" % (binding,))
	
	
	@staticmethod
	def _load_preset(data, profile, preset):
		profile.modeshifts = {}
		profile.modeshift_buttons = {}
		if not 'group_source_bindings' in preset:
			# Empty preset
			return
			
		gsb = preset['group_source_bindings']
		for group_id in gsb:
			binding = gsb[group_id]
			if not binding.endswith("inactive"):
				profile.parse_input_binding(data, group_id, binding)
		
		if "switch_bindings" in preset:
			profile.parse_switches(preset['switch_bindings'])
		
		for b in profile.modeshift_buttons:
			if profile.modeshift_buttons[b] in profile.modeshifts:
				# Should be always
				modeshift = profile.modeshift_buttons[b]
			else:
				continue
			action = profile.modeshifts[modeshift]
			trash, binding = modeshift
			old = profile.get_by_binding(binding)
			profile.set_by_binding(binding, ModeModifier(
				b, action,
				old
			))	
	
	
	@staticmethod
	def _get_preset_name(data, preset):
		""" Returns name of specified preset """
		name = preset["name"].lower()
		if "actions" in data and name in data['actions']:
			name = data['actions'][name]['title']
		return name
	
	
	def action_set_by_id(self, id):
		""" Returns name of action set with specified id """
		for s in self.action_sets:
			if self.action_sets[s].action_set_id == id:
				return s
		return None
	
	
	def load(self, filename):
		"""
		Loads profile from vdf file. Returns self.
		May raise ValueError.
		"""
		data = parse_vdf(open(filename, "r"))
		self.load_data(data)
	
	
	def load_data(self, data):
		if 'controller_mappings' not in data:
			raise ValueError("Invalid profile file")
		data = data['controller_mappings']
		if 'title' in data:
			name = data['title'].strip()
			if name:
				self.name = name
		presets = ensure_list(data['preset'])
		for p in presets:
			id = int(p["id"])
			if id == 0:
				# Default profile
				VDFProfile._load_preset(data, self, p)
			else:
				aset = VDFProfile(VDFProfile._get_preset_name(data, p))
				aset.action_set_id = id
				aset.action_set_switches = self.action_set_switches
				self.action_sets[aset.name] = aset
				VDFProfile._load_preset(data, aset, p)
		
		for aset in list(self.action_sets.values()):
			aset.buttons[SCButtons.C] = HoldModifier(
				MenuAction("Default.menu"), MenuAction("Default.menu")
			)
		
		return self


if __name__ == "__main__":
	import sys
	from scc.tools import init_logging
	init_logging()
	f = VDFProfile().load(sys.argv[1])
	f.save("output.sccprofile")

