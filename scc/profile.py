#!/usr/bin/env python2
"""
SC-Controller - Profile

Handles mapping profile stored in json file
"""
from __future__ import unicode_literals

from scc.constants import LEFT, RIGHT, WHOLE, STICK, GYRO
from scc.constants import SCButtons, HapticPos
from scc.modifiers import SensitivityModifier, ModeModifier
from scc.modifiers import ClickModifier, FeedbackModifier
from scc.parser import TalkingActionParser
from scc.actions import NoAction, XYAction
from scc.lib.jsonencoder import JSONEncoder

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
		}
		
		for i in self.buttons:
			if self.buttons[i]:
				data['buttons'][i.name] = self.buttons[i]
		
		# Generate & save json
		jstr = Encoder(sort_keys=True, indent=4).encode(data)
		open(filename, "w").write(jstr)
		return self
	
	
	def _load_action(self, data, key=None):
		"""
		Converts dict returned by json.loads into action.
		Returns NoAction when parser returns None.
		"""
		if key is not None:
			# Allow calling _load_action(data["buttons"], button), it's shorter
			# than 'if button in data["buttons"]: ...'
			if key in data:
				return self._load_action(data[key], None)
			else:
				return NoAction()
		
		a = NoAction()
		if "action" in data:
			a = self.parser.restart(data["action"]).parse() or NoAction()
		if "X" in data or "Y" in data:
			# "action" is ignored if either "X" or "Y" is there
			x = self._load_action(data["X"]) if "X" in data else NoAction()
			y = self._load_action(data["Y"]) if "Y" in data else NoAction()
			a = XYAction(x, y)
		if "sensitivity" in data:
			args = data["sensitivity"]
			args.append(a)
			a = SensitivityModifier(*args)
		if "feedback" in data:
			args = data["feedback"]
			if hasattr(HapticPos, args[0]):
				args[0] = getattr(HapticPos, args[0])
			args.append(a)
			a = FeedbackModifier(*args)
		if "click" in data:
			a = ClickModifier(a)
		if "name" in data:
			a.name = data["name"]
		if "modes" in data:
			args = []
			for button in data['modes']:
				if hasattr(SCButtons, button):
					args += [ getattr(SCButtons, button), self._load_action(data['modes'][button]) ]
			if a:
				args += [ a ]
			a = ModeModifier(*args)
		return a
		
	
	def load(self, filename):
		""" Loads profile from file. Returns self """
		data = json.loads(open(filename, "r").read())
		# Buttons
		self.buttons = {}
		for x in SCButtons:
			self.buttons[x] = self._load_action(data["buttons"], x.name)
		
		# Stick & gyro
		self.stick = self._load_action(data, "stick")
		self.gyro = self._load_action(data, "gyro")
		
		if "triggers" in data:
			# Old format
			# Triggers
			self.triggers = ({
				x : self._load_action(data["triggers"], x) for x in Profile.TRIGGERS
			})
			
			# Pads
			self.pads = {
				Profile.LEFT	: self._load_action(data, "left_pad"),
				Profile.RIGHT	: self._load_action(data, "right_pad"),
			}
		else:
			# New format
			# Triggers
			self.triggers = {
				Profile.LEFT	: self._load_action(data, "trigger_left"),
				Profile.RIGHT	: self._load_action(data, "trigger_right"),
			}
		
			# Pads
			self.pads = {
				Profile.LEFT	: self._load_action(data, "pad_left"),
				Profile.RIGHT	: self._load_action(data, "pad_right"),
			}
		
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
		return json.JSONEncoder.default(self, obj)
