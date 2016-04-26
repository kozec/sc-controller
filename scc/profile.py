#!/usr/bin/env python2
"""
SC-Controller - Profile

Handles mapping profile stored in json file
"""
from __future__ import unicode_literals

from scc.constants import SCButtons
from scc.parser import TalkingActionParser
from scc.constants import LEFT, RIGHT, WHOLE, STICK

import json

class Profile(object):
	LEFT  = LEFT
	RIGHT = RIGHT
	WHOLE = WHOLE
	STICK = STICK
	X, Y = "X", "Y"
	STICK_AXES = { X : "lpad_x", Y : "lpad_y" }
	LPAD_AXES  = STICK_AXES
	RPAD_AXES  = { X : "rpad_x", Y : "rpad_y" }
	TRIGGERS   = [ LEFT, RIGHT ]
	
	def __init__(self, parser):
		self.parser = parser
		self.buttons = {}
		self.stick = {}
		self.triggers = {}
		self.pads = { Profile.LEFT : {}, Profile.RIGHT : {} }
	
	
	def save(self, filename):
		""" Saves profile into file. Returns self """
		data = {
			'buttons' : {},
			'stick' : {},
			'triggers' : {},
			"left_pad" : {},
			"right_pad" : {}
		}
		# Buttons
		for x in SCButtons:
			if x in self.buttons:
				data['buttons'][x.name] = { 'action' : self.buttons[x].to_string() }
		
		# Stick
		if Profile.WHOLE in self.stick:
			data["stick"]['action'] = self.stick[Profile.WHOLE].to_string()
		else:
			for x in Profile.STICK_AXES:
				data["stick"][x] = {}
				if x in self.stick:
					data["stick"][x]['action'] = self.stick[x].to_string()
		
		# Triggers
		for x in Profile.TRIGGERS:
			data["triggers"][x] = {}
			if x in self.triggers:
				data["triggers"][x]['action'] = self.triggers[x].to_string()
		
		# Pads
		for (y, key) in ( (Profile.LEFT, "left_pad"), (Profile.RIGHT, "right_pad") ):
			data[key] = {}
			if Profile.WHOLE in self.pads[y]:
				data[key]['action'] = self.pads[y][Profile.WHOLE].to_string()
			else:
				for x in Profile.RPAD_AXES:
					data[key][x] = {}
					if x in self.pads[y]:
						data[key][x]['action'] = self.pads[y][x].to_string()
		
		# Generate json
		jstr = json.dumps(data, sort_keys=True, indent=4)
		# Convert spaces to tabs
		# jstr = jstr.replace("    ", "\t")
		# Compact it a little
		# for x in (2, 3):
		#	jstr = jstr.replace('{\n' + (b"\t" * x) + '"action', '\t{ "action')
		#	jstr = jstr.replace('"\n' + (b"\t" * x) + '}', ' }')
		
		# Save it
		open(filename, "w").write(jstr)
		return self


	def load(self, filename):
		""" Loads profile from file. Returns self """
		data = json.loads(open(filename, "r").read())
		# Buttons
		self.buttons = {}
		for x in SCButtons:
			if x.name in data["buttons"] and "action" in data["buttons"][x.name]:
				a = self.parser.restart(data["buttons"][x.name]["action"]).parse()
				if a is not None:
					self.buttons[x] = a
		
		# Stick
		self.stick = {}
		for x in Profile.STICK_AXES:
			if x in data["stick"] and "action" in data["stick"][x]:
				a = self.parser.restart(data["stick"][x]["action"]).parse()
				if a is not None:
					self.stick[x] = a
		if "action" in data["stick"]:
			a = self.parser.restart(data["stick"]["action"]).parse()
			if a is not None:
				self.stick[Profile.WHOLE] = a
		
		# Triggers
		self.triggers = {}
		for x in Profile.TRIGGERS:
			if x in data["triggers"] and "action" in data["triggers"][x]:
				a = self.parser.restart(data["triggers"][x]["action"]).parse()
				if a is not None:
					self.triggers[x] = a
		
		# Pads
		self.pads = {}
		for (y, key) in ( (Profile.LEFT, "left_pad"), (Profile.RIGHT, "right_pad") ):
			self.pads[y] = {}
			for x in Profile.RPAD_AXES:
				if x in data[key] and "action" in data[key][x]:
					a = self.parser.restart(data[key][x]["action"]).parse()
					if a is not None:
						self.pads[y][x] = a
			
			if "action" in data[key]:
				a = self.parser.restart(data[key]["action"]).parse()
				if a is not None:
					self.pads[y][Profile.WHOLE] = a
		
		return self