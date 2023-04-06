#!/usr/bin/env python2
"""
SC-Controller - Config

Handles loading, storing and querying config file
"""


from scc.paths import get_config_path
from scc.profile import Encoder
from scc.special_actions import ChangeProfileAction

import os, json, logging
log = logging.getLogger("Config")


class Config(object):
	DEFAULTS = {
		"autoswitch_osd":	True,	# True to show OSD message when profile is autoswitched
		"autoswitch":		[],		# Empty list of conditions
		"recent_max":		10,		# Number of profiles to keep
		"recent_profiles":	[		# Hard-coded list of profiles from default_profiles/
			# This is actually updated by scc-osd-daemon, as that's
			# only thing actually knowing what to put here.
			"Desktop",
			"XBox Controller with High Precision Camera",
			"XBox Controller"
		],
		"drivers" : {				# Map of drivers with values of True, Flase
									# or additional driver config where needed.
									# Anything but False means enabled here.
			"sc_dongle": True,
			"sc_by_cable": True,
			"sc_by_bt": True,
			"steamdeck": True,
			"fake": False,			# Used for developement
			"hiddrv": True,
			"evdevdrv": True,
			"ds4drv": True,			# At least one of hiddrv or evdevdrv has to be enabled as well
		},
		"fix_xinput" : True,		# If True, attempt is done to deatach emulated controller 
									# from 'Virtual core pointer' core device.
		"gui": {
			# GUI-only settings
			"enable_status_icon" : False,
			"minimize_to_status_icon" : True,
			"minimize_on_start" : False,
			"autokill_daemon" : False,
			"news": {
				# Controls "new in this version" message
				"enabled": True,			# if disabled, no querying is done
				"last_version": "0.3.12",	# last version for which message was displayed
			}
		},
		"controllers": { },
		# output - modifies emulated controller
		# Changing this may be usefull, but can break a lot of things
		"output": {
			'vendor'	: '0x045e',
			'product'	: '0x028e',
			'version'	: '0x110',
			'name'		: "Microsoft X-Box 360 pad",
			'buttons'	: 11,
			'rumble'	: True,
			'axes'	: [
				(-32768, 32767),	# Axes.ABS_X
				(-32768, 32767),	# Axes.ABS_Y
				(-32768, 32767),	# Axes.ABS_RX
				(-32768, 32767),	# Axes.ABS_RY
				(0, 255),			# Axes.ABS_Z
				(0, 255),			# Axes.ABS_RZ
				(-1, 1),			# Axes.ABS_HAT0X
				(-1, 1)				# Axes.ABS_HAT0Y
			],
		},
		# enable_sniffing - If enabled, another program with write access to
		# ~/.config/scc can ask daemon to send notifications about all
		# (or only some) inputs.
		# This enables GUI to display which physical button was pressed to user.
		"enable_sniffing" : False,
		# Style and colors used by OSD
		"osd_style": "Classic.gtkstyle.css",
		"osd_colors": {
			"background": "101010",
			"border": "101010",
			"text": "16BF24",
			"menuitem_border": "101010",
			"menuitem_hilight": "202020",
			"menuitem_hilight_text": "16FF26",
			"menuitem_hilight_border": "16FF26",
			"menuseparator": "2e3436",
		},
		# Colors used by on-screen keyboard
		"osk_colors": {
			'hilight' : '7A7A7A',
			'pressed' : 'B0B0B0',
			"button1" : "101010",
			"button1_border" : "101010",
			"button2" : "2e3436",
			"button2_border" : "2e3436",
			"text" : "16BF24"
		},
		# Colors used by gesture display. Unlike OSD and OSK, these are RGBA
		"gesture_colors" : {
			"background": "160c00ff",
			"grid": "004000ff",
			"line": "ffffff1a",
		},
		# TODO: Config for opacity
		"windows_opacity": 0.95,
		# See drivers/sc_dongle.py, read_serial method
		"ignore_serials" : True,
	}
	
	CONTROLLER_DEFAULTS = {
		# Defaults for controller config
		"name":					None,	# Filled with controller ID on runtime
		"icon":					None,	# Determined by magic by UI
		"led_level":			80,		# range 0 to 100
		"idle_timeout":			600,	# in seconds, range from 1 to 32767
		"osd_alignment":		0,		# not used yet
		"input_rotation_l":		20,		# range -180 to 180
		"input_rotation_r":		-20,	# range -180 to 180
		"menu_control":			"STICK",
		"menu_confirm":			"A",
		"menu_cancel":			"B",
	}
	
	
	def __init__(self):
		self.filename = os.path.join(get_config_path(), "config.json")
		self.reload()
	
	
	def reload(self):
		""" (Re)loads configuration. Works as load(), but handles exceptions """
		try:
			self.load()
		except Exception as e:
			log.warning("Failed to load configuration; Creating new one.")
			log.warning("Reason: %s", (e,))
			self.create()
		if self.check_values():
			self.save()
	
	
	def _check_dict(self, values, defaults):
		"""
		Recursivelly checks if 'config' contains all keys in 'defaults'.
		Creates keys with default values where missing.
		
		Returns True if anything was changed.
		"""
		rv = False
		for d in defaults:
			if d not in values:
				values[d] = defaults[d]
				rv = True
			if type(values[d]) == dict:
				rv = self._check_dict(values[d], defaults[d]) or rv
		return rv
	
	
	def check_values(self):
		"""
		Check if all required values are in place and fill by default
		whatever is missing.
		
		Returns True if anything gets changed.
		"""
		rv = self._check_dict(self.values, self.DEFAULTS)
		# Special check for autoswitcher after v0.2.17
		if "autoswitch" in self.values:
			for a in self.values["autoswitch"]:
				if "profile" in a:
					a["action"] = ChangeProfileAction(str(a["profile"])).to_string()
					del a["profile"]
					rv = True
		return rv
	
	
	def get_controller_config(self, controller_id):
		"""
		Returns self['controllers'][controller_id], creating new node populated
		with defaults if there is none.
		"""
		if controller_id in self.values['controllers']:
			# Check values in existing config
			rv = self.values['controllers'][controller_id]
			for key in self.CONTROLLER_DEFAULTS:
				if key not in rv:
					if key in ("input_rotation_l", "input_rotation_r"):
						# Special case, just to not change behavior for existing users
						rv[key] = 0
					else:
						rv[key] = self.CONTROLLER_DEFAULTS[key]
			return rv
		# Create new config
		rv = self.values['controllers'][controller_id] = {
			key : self.CONTROLLER_DEFAULTS[key] for key in self.CONTROLLER_DEFAULTS
		}
		rv["name"] = controller_id
		return rv
	
	
	def load(self):
		self.values = json.loads(open(self.filename, "r").read())
	
	
	def create(self):
		""" Creates new, empty configuration """
		self.values = {}
		self.check_values()
		self.save()
	
	
	def save(self):
		""" Saves configuration file """
		# Check & create directory
		if not os.path.exists(get_config_path()):
			os.makedirs(get_config_path())
		# Save
		data = { k:self.values[k] for k in self.values }
		jstr = Encoder(sort_keys=True, indent=4).encode(data)
		file(self.filename, "w").write(jstr)
		log.debug("Configuration saved")
	
	
	def __iter__(self):
		for k in self.values:
			yield k
	
	def get(self, key, default=None):
		return self.values.get(key, default)
	
	def set(self, key, value):
		self.values[key] = value
	
	__getitem__ = get
	__setitem__ = set
	
	def __contains__(self, key):
		""" Returns true if there is such value """
		return key in self.values

