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
from scc.menu_data import MenuData
from scc.actions import NoAction

import json

class Profile(object):
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
			"menus"			: { id : self.menus[id].encode() for id in self.menus }
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
		
		# Menus
		self.menus = {}
		if "menus" in data:
			for id in data["menus"]:
				for invalid_char in ".:/":
					if invalid_char in id:
						raise ValueError("Invalid character '%s' in menu id '%s'" % (invalid_char, id))
				self.menus[id] = MenuData.from_json_data(data["menus"][id], self.parser)
		
		return self
	
	
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
	

class Encoder(JSONEncoder):
	def default(self, obj):
		#if type(obj) in (list, tuple):
		#	return basestring("[" + ", ".join(self.encode(x) for x in obj) + " ]")
		if hasattr(obj, "encode"):
			return obj.encode()
		return JSONEncoder.default(self, obj)
