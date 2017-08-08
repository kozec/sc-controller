#!/usr/bin/env python2
"""
Imports VDF profile and converts it to Profile object.
"""
from scc.profile import Profile
from scc.actions import TriggerAction, XYAction, DPadAction, DPad8Action
from scc.actions import NoAction, TiltAction, RingAction, MultiAction
from scc.modifiers import CircularModifier, CircularAbsModifier, SmoothModifier
from scc.modifiers import ClickModifier, FeedbackModifier, DeadzoneModifier
from scc.modifiers import SensitivityModifier, ModeModifier, BallModifier
from scc.modifiers import HoldModifier, DoubleclickModifier
from scc.modifiers import RotateInputModifier
from scc.constants import CUT, STICK_PAD_MIN, STICK_PAD_MAX
from scc.constants import SCButtons, HapticPos
from scc.special_actions import OSDAction, PositionModifier
from scc.special_actions import GesturesAction
from scc.parser import ActionParser

import logging
log = logging.getLogger("import.oldscc")


class OldSCCProfile(Profile):
	
	def load_fileobj(self, fileobj):
		if not isinstance(self.parser, OldSCCParser):
			self.parser = OldSCCParser(self.parser)
		
		Profile.load_fileobj(self, fileobj)


class OldSCCParser(ActionParser):
	"""
	Wraps around another parser and overrides from_json_data method so it can
	parse old (<v1.3) profiles profiles.
	"""
	
	def __init__(self, parent):
		self._parent = parent
		# priorities is build from contains moved from various
		# places when old profile format was abandonded
		self.priorities = {
			self._decode_and: -20,
			self._decode_dpad: -10,
			self._decode_ring: -10,
			self._decode_XY: -10,
			self._decode_ball: -6,
			self._decode_circular: -6,
			self._decode_circularabs: -6,
			self._decode_levels: -5,
			self._decode_osd: -5,
			self._decode_sensitivity: -5,
			self._decode_feedback: -4,
			self._decode_gestures: 2,
			self._decode_modes: 2,
			self._decode_doubleclick: 3,
			self._decode_hold: 4,
			self._decode_smooth: 11,
		}
	
	
	def from_json_data(self, data, key=None):
		if data is None:
			return NoAction()
		elif key is not None:
			return self.from_json_data(data.get(key))
		
		a = ActionParser.from_json_data(self, data)
		decoders = set()
		for key in data:
			m_name = "_decode_%s" % (key, )
			if hasattr(self, m_name):
				decoders.add(getattr(self, m_name))
		if "X" in data or "Y" in data:
			decoders.add(self._decode_XY)
		
		if decoders:
			for decoder in sorted(decoders, key=lambda x: self.priorities.get(x, 0)):
				a = decoder(data, a, 0)
		return a
	
	
	def restart(self, string):
		return self._parent.restart(string)
	
	
	def parse(self):
		return self._parent.parse()
	
	
	###
	# Following methods were moved from various places
	# when old profile format was abandonded
	def _decode_tilt(self, data, a, *b):
		args = [ self.from_json_data(x) for x in data['tilt'] ]
		return TiltAction(*args)
	
	def _decode_and(self, data, a, *b):
		return MultiAction.make(*[
			self.from_json_data(x) for x in data['actions']
		])
	
	def _decode_dpad(self, data, a, *b):
		args = [ self.from_json_data(x) for x in data['dpad'] ]
		if len(args) > 4:
			a = DPad8Action(*args)
		else:
			a = DPadAction(*args)
		return a
	
	def _decode_ring(self, data, a, *b):
		args, data = [], data['ring']
		if 'radius' in data: args.append(float(data['radius']))
		args.append(self.from_json_data(data['inner']) if 'inner' in data else NoAction())
		args.append(self.from_json_data(data['outer']) if 'outer' in data else NoAction())
		return RingAction(*args)
	
	def _decode_XY(self, data, action, *a):
		x = self.from_json_data(data["X"]) if "X" in data else NoAction()
		y = self.from_json_data(data["Y"]) if "Y" in data else NoAction()
		return XYAction(x, y)
	
	def _decode_levels(self, data, a, *b):
		# Triggers
		press_level, release_level = data['levels']
		return TriggerAction(press_level, release_level, a)
	
	def _decode_name(self, data, a, *b):
		return a.set_name(data['name'])
	
	def _decode_click(self, data, a, *b):
		return ClickModifier(a)
	
	def _decode_ball(self, data, a, *b):
		if data['ball'] is True:
			# backwards compatibility
			return BallModifier(a)
		else:
			args = list(data['ball'])
			args.append(a)
			return BallModifier(*args)
	
	def _decode_deadzone(self, data, a, *b):
		return DeadzoneModifier(
			data["deadzone"]["mode"] if "mode" in data["deadzone"] else CUT,
			data["deadzone"]["lower"] if "lower" in data["deadzone"] else STICK_PAD_MIN,
			data["deadzone"]["upper"] if "upper" in data["deadzone"] else STICK_PAD_MAX,
			a
		)
	
	def _decode_modes(self, data, a, *b):
		args = []
		for button in data['modes']:
			if hasattr(SCButtons, button):
				args += [ getattr(SCButtons, button), self.from_json_data(data['modes'][button]) ]
		if a:
			args += [ a ]
		mm = ModeModifier(*args)
		if "name" in data:
			mm.name = data["name"]
		return mm
	
	def _decode_doubleclick(self, data, a, *b):
		args = [ self.from_json_data(data['doubleclick']), a ]
		a = DoubleclickModifier(*args)
		if 'time' in data:
			a.timeout = data['time']
		return a
	
	def _decode_hold(self, data, a, *b):
		if isinstance(a, DoubleclickModifier):
			a.holdaction = self.from_json_data(data['hold'])
		else:
			args = [ self.from_json_data(data['hold']), a ]
			a = HoldModifier(*args)
		if 'time' in data:
			a.timeout = data['time']
		if isinstance(a.normalaction, FeedbackModifier):
			# Ugly hack until profile file is redone
			mod = a.normalaction
			a.normalaction = mod.action
			if hasattr(a.normalaction, "set_haptic"):
				a.normalaction.set_haptic(None)
			mod.action = a
			mod.action.set_haptic(mod.haptic)
			a = mod
		return a
	
	def _decode_sensitivity(self, data, a, *b):
		if a:
			args = list(data["sensitivity"])
			args.append(a)
			return SensitivityModifier(*args)
		# Adding sensitivity to NoAction makes no sense
		return a
	
	def _decode_feedback(self, data, a, *b):
		args = list(data['feedback'])
		if hasattr(HapticPos, args[0]):
			args[0] = getattr(HapticPos, args[0])
		args.append(a)
		return FeedbackModifier(*args)
	
	def _decode_rotate(self, data, a, *b):
		return RotateInputModifier(float(data['rotate']), a)
	
	def _decode_smooth(self, data, a, *b):
		pars = data['smooth'] + [ a ]
		return SmoothModifier(*pars)
	
	def _decode_circular(self, data, a, *b):
		return CircularModifier(a)
	
	def _decode_circularabs(self, data, a, *b):
		return CircularAbsModifier(a)
	
	def _decode_osd(self, data, a, *b):
		a = OSDAction(a)
		if data["osd"] is not True:
			a.timeout = float(data["osd"])
		return a
	
	def _decode_position(self, data, a, *b):
		x, y = data['position']
		return PositionModifier(x, y, a)
	
	def _decode_gestures(self, data, a, *b):
		ga = GesturesAction()
		ga.gestures = {
			gstr: self.from_json_data(data['gestures'][gstr])
			for gstr in data['gestures']
		}
		if "name" in data:
			ga.name = data["name"]
		if "osd" in data:
			ga = OSDAction(ga)
		return ga
