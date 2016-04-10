from __future__ import unicode_literals

from scc.constants import SCButtons
import json

class Profile(object):
	LEFT  = "LEFT"
	RIGHT = "RIGHT"
	WHOLE = "WHOLE"
	STICK_AXES = { "X" : "lpad_x", "Y" : "lpad_y" }
	LPAD_AXES  = STICK_AXES
	RPAD_AXES  = { "X" : "rpad_x", "Y" : "rpad_y" }
	TRIGGERS   = [ LEFT, RIGHT ]
	
	def __init__(self):
		self.buttons = {}
		self.stick = {}
		self.triggers = {}
		self.left_pad = {}
		self.right_pad = {}
	
	def load(self, filename):
		data = json.loads(open(filename, "r").read())
		# Buttons
		self.buttons = {
			x : data["buttons"][x.name]["action"]
			for x in SCButtons
			if x.name in data["buttons"] and "action" in data["buttons"][x.name]
		}
		
		# Stick
		self.stick = {
			x : data["stick"][x]["action"]
			for x in Profile.STICK_AXES
			if x in data["stick"] and "action" in data["stick"][x]
		}
		if "action" in data["stick"]: self.stick[Profile.WHOLE] = data["stick"]["action"]
		
		# Triggers
		self.triggers = {
			x : data["triggers"][x]["action"]
			for x in Profile.TRIGGERS
			if x in data["triggers"] and "action" in data["triggers"][x]
		}
		
		# Pads
		self.pads = {
			Profile.LEFT : {
				x : data["left_pad"][x]["action"]
				for x in Profile.LPAD_AXES
				if x in data["left_pad"] and "action" in data["left_pad"][x]
			},
			Profile.RIGHT : {
				x : data["right_pad"][x]["action"]
				for x in Profile.RPAD_AXES
				if x in data["right_pad"] and "action" in data["right_pad"][x]
			}
		}
		
		
		if "action" in data["left_pad"]: self.pads[Profile.LEFT][Profile.WHOLE] = data["left_pad"]["action"]
		if "action" in data["right_pad"]: self.pads[Profile.RIGHT][Profile.WHOLE] = data["right_pad"]["action"]
