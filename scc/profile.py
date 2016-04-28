#!/usr/bin/env python2
"""
SC-Controller - Profile

Handles mapping profile stored in json file
"""
from __future__ import unicode_literals

from scc.constants import SCButtons
from scc.parser import TalkingActionParser
from scc.actions import NoAction, XYAction
from scc.modifiers import ClickModifier, ModeModifier
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
		self.buttons = { x : NoAction() for x in SCButtons }
		self.stick = NoAction()
		self.triggers = { Profile.LEFT : NoAction(), Profile.RIGHT : NoAction() }
		self.pads = { Profile.LEFT : NoAction(), Profile.RIGHT : NoAction() }
	
	
	def save(self, filename):
		""" Saves profile into file. Returns self """
		data = {
			'buttons'	: {},
			'stick'		: self.stick,
			'triggers'	: self.triggers,
			"left_pad"	: self.pads[Profile.LEFT],
			"right_pad"	: self.pads[Profile.RIGHT],
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
		if "click" in data:
			a = ClickModifier(a)
		if "modes" in data:
			args = []
			for button in data['modes']:
				if hasattr(SCButtons, button):
					args += [ getattr(SCButtons, button), self._load_action(data['modes'][button]) ]
			if a:
				args += [ a ]
			a = ModeModifier(*args)
		if "name" in data:
			a.name = data["name"]
		return a
		
	
	def load(self, filename):
		""" Loads profile from file. Returns self """
		data = json.loads(open(filename, "r").read())
		# Buttons
		self.buttons = {}
		for x in SCButtons:
			self.buttons[x] = self._load_action(data["buttons"], x.name)
		
		# Stick
		self.stick = self._load_action(data, "stick")
		
		# Triggers
		self.triggers = {}
		for x in Profile.TRIGGERS:
			self.triggers[x] = self._load_action(data["triggers"], x)
		
		# Pads
		self.pads = {}
		for (y, key) in ( (Profile.LEFT, "left_pad"), (Profile.RIGHT, "right_pad") ):
			self.pads[y] = self._load_action(data, key)
		
		return self

class Encoder(json.JSONEncoder):
	def default(self, obj):
		if hasattr(obj, "encode"):
			return obj.encode()
		return json.JSONEncoder.default(self, obj)
