#!/usr/bin/env python2
"""
SC-Controller - Profile

Handles mapping profile stored in json file
"""
from __future__ import unicode_literals

from scc.constants import LEFT, RIGHT, WHOLE, STICK, GYRO
from scc.constants import SCButtons, HapticPos
from scc.lib.jsonencoder import JSONEncoder
from scc.parser import TalkingActionParser
from scc.actions import Action, NoAction
from scc.menu_data import MenuData

import json, logging
log = logging.getLogger("profile")


class Profile(object):
	VERSION = 2		# Current profile version. When loading profile file
					# with version lower than this, auto-conversion may happen
	
	LEFT  = LEFT
	RIGHT = RIGHT
	WHOLE = WHOLE
	STICK = STICK
	GYRO  = GYRO
	X, Y, Z = "X", "Y", "Z"
	STICK_AXES = { X : "lpad_x", Y : "lpad_y" }
	LPAD_AXES  = STICK_AXES
	RPAD_AXES  = { X : "rpad_x", Y : "rpad_y" }
	TRIGGERS   = [ LEFT, RIGHT ]
	
	def __init__(self, parser):
		self.parser = parser
		self.buttons = { x : NoAction() for x in SCButtons }
		self.menus = {}
		self.stick = NoAction()
		self.triggers = { Profile.LEFT : NoAction(), Profile.RIGHT : NoAction() }
		self.pads = { Profile.LEFT : NoAction(), Profile.RIGHT : NoAction() }
		self.gyro = NoAction()
	
	
	def save(self, filename):
		""" Saves profile into file. Returns self """
		data = {
			'buttons'		: {},
			'stick'			: self.stick,
			'gyro'			: self.gyro,
			'trigger_left'	: self.triggers[Profile.LEFT],
			'trigger_right'	: self.triggers[Profile.RIGHT],
			"pad_left"		: self.pads[Profile.LEFT],
			"pad_right"		: self.pads[Profile.RIGHT],
			"menus"			: { id : self.menus[id].encode() for id in self.menus },
			"version"		: Profile.VERSION
		}
		
		for i in self.buttons:
			if self.buttons[i]:
				data['buttons'][i.name] = self.buttons[i]
		
		# Generate & save json
		jstr = Encoder(sort_keys=True, indent=4).encode(data)
		open(filename, "w").write(jstr)
		return self
	
	
	def load(self, filename):
		""" Loads profile from file. Returns self """
		data = json.loads(open(filename, "r").read())
		# Version
		try:
			version = int(data["version"])
		except:
			version = 0
		
		if version < 2:
			self._load_v1(data)
			self._convert(version)
		else:
			# Buttons
			self.buttons = {}
			for x in SCButtons:
				self.buttons[x] = self.parser.from_json(data["buttons"], x.name)
			
			# Stick & gyro
			self.stick = self.parser.from_json(data, "stick")
			self.gyro = self.parser.from_json(data, "gyro")
			
			# Triggers
			self.triggers = {
				Profile.LEFT	: self.parser.from_json(data, "trigger_left"),
				Profile.RIGHT	: self.parser.from_json(data, "trigger_right"),
			}
		
			# Pads
			self.pads = {
				Profile.LEFT	: self.parser.from_json(data, "pad_left"),
				Profile.RIGHT	: self.parser.from_json(data, "pad_right"),
			}
		
		# Menus
		self.menus = {}
		if "menus" in data:
			for id in data["menus"]:
				for invalid_char in ".:/":
					if invalid_char in id:
						raise ValueError("Invalid character '%s' in menu id '%s'" % (invalid_char, id))
				self.menus[id] = MenuData.from_json_data(data["menus"][id], self.parser)
		
		return self
	
	
	def _load_v1(self, data):
		""" Old, complicated method used to load old profile files """
		# Buttons
		self.buttons = {}
		for x in SCButtons:
			self.buttons[x] = self.parser.from_json_data(data["buttons"], x.name)

		# Stick & gyro
		self.stick = self.parser.from_json_data(data, "stick")
		self.gyro = self.parser.from_json_data(data, "gyro")

		if "triggers" in data:
			# Old format
			# Triggers
			self.triggers = ({
				x : self.parser.from_json_data(data["triggers"], x) for x in Profile.TRIGGERS
			})
			
			# Pads
			self.pads = {
				Profile.LEFT	: self.parser.from_json_data(data, "left_pad"),
				Profile.RIGHT	: self.parser.from_json_data(data, "right_pad"),
			}
		else:
			# New format
			# Triggers
			self.triggers = {
				Profile.LEFT	: self.parser.from_json_data(data, "trigger_left"),
				Profile.RIGHT	: self.parser.from_json_data(data, "trigger_right"),
			}

			# Pads
			self.pads = {
				Profile.LEFT	: self.parser.from_json_data(data, "pad_left"),
				Profile.RIGHT	: self.parser.from_json_data(data, "pad_right"),
			}

	
	
	def compress(self):
		"""
		Calls compress on every action to throw out some redundant stuff.
		Note that calling save() after compress() will break stuff.
		"""
		for dct in (self.buttons, self.triggers, self.pads):
			for x in dct:
				dct[x] = dct[x].compress()
		self.stick = self.stick.compress()
		self.gyro = self.gyro.compress()
	
	
	def _convert(self, from_version):
		""" Performs conversion from older profile version """
		if from_version < 1:
			from scc.modifiers import ModeModifier, HoldModifier
			from scc.special_actions import MenuAction
			# Add 'display Default.menu if center button is held' for old profiles
			c = self.buttons[SCButtons.C]
			if not c:
				# Nothing set to C button
				self.buttons[SCButtons.C] = HoldModifier(
					MenuAction("Default.menu"),
					normalaction = MenuAction("Default.menu")
				)
			elif hasattr(c, "holdaction") and c.holdaction:
				# Already set to something, don't overwrite it
				pass
			elif c.to_string().startswith("OSK."):
				# Special case, don't touch this either
				pass
			else:
				self.buttons[SCButtons.C] = HoldModifier(
					MenuAction("Default.menu"),
					normalaction = self.buttons[SCButtons.C]
				)
		
		if from_version < 1.1:
			# Convert old scrolling wheel to new representation
			from scc.modifiers import FeedbackModifier, BallModifier
			from scc.actions import MouseAction, XYAction
			from scc.uinput import Rels
			iswheelaction = ( lambda x : isinstance(x, MouseAction) and
					x.parameters[0] in (Rels.REL_HWHEEL, Rels.REL_WHEEL) )
			for p in (Profile.LEFT, Profile.RIGHT):
				a, feedback = self.pads[p], None
				if isinstance(a, FeedbackModifier):
					feedback = a.haptic.get_position()
					a = a.action
				if isinstance(a, XYAction):
					if iswheelaction(a.x) or iswheelaction(a.y):
						n = BallModifier(XYAction(a.x, a.y))
						if feedback:
							n = FeedbackModifier(feedback, 4096, 16, n)
						self.pads[p] = n
						log.info("Converted %s to %s", a.to_string(), n.to_string())


class Encoder(JSONEncoder):
	def default(self, obj):
		if hasattr(obj, "encode"):
			return obj.encode()
		return JSONEncoder.default(self, obj)
