from scc.uinput import Keys, Axes, Rels
from scc.constants import SCButtons, HapticPos
from scc.modifiers import DoubleclickModifier
from scc.actions import Action, AxisAction
from scc.macros import Macro
from scc.special_actions import MenuAction
from scc.parser import ActionParser

parser = ActionParser()

CASES = {
	# Contains all test cases that are tested by
	# test_sensitivity and test_feedback
	# This should contain key for every Action that supports setting feedback
	# or sensitivity. test_tests method tests whether it realy does.
	'axis': {
		'action': 'sens(2.0, axis(ABS_RX))',
		'sensitivity': (2.0,),
	},
	'raxis': {
		'action': 'sens(2.0, axis(ABS_RX))',
		'sensitivity': (2.0,),
	},
	'mouse': {
		'action': 'feedback(BOTH, sens(2.0, 3.0, mouse()))',
		'feedback': (HapticPos.BOTH, ),
		'sensitivity': (2.0, 3.0),
	},
	'mouseabs': {
		'action': 'sens(2.0, 3.0, mouseabs(REL_X))',
		'sensitivity': (2.0, 3.0),
	},
	'gyro': {
		'action': 'sens(2.0, 3.0, 4.0, gyro(ABS_X, ABS_Y, ABS_Z))',
		'sensitivity': (2.0, 3.0, 4.0),
	},
	'tilt': {
		'action': """sens(2.0, 3.0, 4.0, tilt(
			button(KEY_D), button(KEY_U), button(KEY_L), button(KEY_R) ))""",
		'sensitivity': (2.0, 3.0, 4.0),
	},
	'gyroabs': {
		'action': 'feedback(BOTH, sens(2.0, 3.0, 4.0, gyroabs(ABS_X, ABS_Y, ABS_Z)))',
		'feedback': (HapticPos.BOTH, ),
		'sensitivity': (2.0, 3.0, 4.0),
	},
	'hatup':    { 'action': 'sens(2.0, hatup(ABS_X))', 'sensitivity': (2.0,) },
	'hatdown':  { 'action': 'sens(2.0, hatdown(ABS_X))', 'sensitivity': (2.0,) },
	'hatleft':  { 'action': 'sens(2.0, hatleft(ABS_X))', 'sensitivity': (2.0,) },
	'hatright': { 'action': 'sens(2.0, hatright(ABS_X))', 'sensitivity': (2.0,) },
	'button': {
		'action': 'feedback(BOTH, button(KEY_X))',
		'feedback': (HapticPos.BOTH, ),
	},
	'circular': {
		'action': 'feedback(BOTH, sens(2.0, circular(mouse(REL_HWHEEL))))',
		'feedback': (HapticPos.BOTH, ),
		'sensitivity': (2.0, ),
	},
	'circularabs': {
		'action': 'feedback(BOTH, sens(2.0, circularabs(mouse(REL_HWHEEL))))',
		'feedback': (HapticPos.BOTH, ),
		'sensitivity': (2.0, ),
	},
	'XY': {
		'action': """feedback(BOTH, sens(2.0, 3.0, XY(
			axis(ABS_X),
			axis(ABS_Y))))""",
		'feedback': (HapticPos.BOTH, ),
		'sensitivity': (2.0, 3.0),
	},
	'trigger': {
		'action': 'feedback(BOTH, trigger(10, 80, button(KEY_X)))',
		'feedback': (HapticPos.BOTH, ),
	},
	'ball': {
		'action': """feedback(BOTH, sens(2.0, 3.0,
			ball(XY(axis(Axes.ABS_RX), axis(Axes.ABS_RY)))))""",
		'feedback': (HapticPos.BOTH, ),
		'sensitivity': (2.0, 3.0),
	},
	"dpad": {
		'action': """feedback(LEFT, 32640, dpad(
			button(Keys.KEY_W),
			button(Keys.KEY_S),
			button(Keys.KEY_A),
			button(Keys.KEY_D)
		))""",
		'feedback': (HapticPos.LEFT, 32640, ),
	},
	"dpad8": {
		'action': """feedback(LEFT, 32640, dpad(
			button(Keys.KEY_1),
			button(Keys.KEY_2),
			button(Keys.KEY_3),
			button(Keys.KEY_4),
			button(Keys.KEY_5),
			button(Keys.KEY_6),
			button(Keys.KEY_7),
			button(Keys.KEY_8)
		))""",
		'feedback': (HapticPos.LEFT, 32640, ),
	},
	"menu": {
		"action": "feedback(LEFT, 32640, menu('Default.menu'))",
		'feedback': (HapticPos.LEFT, 32640, ),
	},
	"hold": {
		"action": """feedback(LEFT, 32640,
				hold( menu('Default.menu'), button(Keys.KEY_W) )
			)""",
		'feedback': (HapticPos.LEFT, 32640, ),
	}
}


class TestCompress(object):
	"""
	Tests Aciton.compress method.
	Basically, tests how various combinations of modifiers interacts together.
	"""
	
	def test_tests(self):
		# Test if there is key in CASES for every action that suppports
		# setting feedback or sensitivity.
		for cls in Action.ALL.values():
			if Macro in cls.__bases__:
				# Skip macros, they are handled separately
				continue
			if MenuAction in cls.__bases__ and cls != MenuAction:
				# Skip alternate menu types, they all behave in same way
				continue
			if cls == DoubleclickModifier:
				# Tested along with hold
				continue
			if hasattr(cls, "set_speed"):
				assert cls.COMMAND in CASES, (
					"%s supports setting sensitivity, but "
					"there is no test case it" % (cls.COMMAND,))
			if hasattr(cls, "set_haptic"):
				assert cls.COMMAND in CASES, (
					"%s supports feedback, but there is "
					"no test case it" % (cls.COMMAND,))
	
	
	def test_hold_doubleclick(self):
		"""
		Tests parsing of hold & doubleclick combination.
		"""
		a = parser.from_json_data({
			'action': """doubleclick(
				axis(ABS_Z), hold(axis(ABS_X), axis(ABS_RX)))"""
		}).compress()
		
		assert isinstance(a, DoubleclickModifier)
		assert isinstance(a.normalaction, AxisAction)
		assert isinstance(a.action, AxisAction)
		assert isinstance(a.holdaction, AxisAction)
		assert a.normalaction.id == Axes.ABS_RX
		assert a.action.id == Axes.ABS_Z
		assert a.holdaction.id == Axes.ABS_X
	
	
	def test_sensitivity(self):
		"""
		Tests if all sensitivity setting are parsed and applied
		after .compress() is called.
		"""
		for case in CASES:
			if hasattr(Action.ALL[case], 'set_speed'):
				print "Testing 'sensitivity' on %s" % (case,)
				try:
					a = parser.from_json_data(CASES[case]).compress()
				except Exception:
					print "Failed to parse", CASES[case]['action']
					raise
				assert (
					a.get_speed() == CASES[case]['sensitivity']
					or
					a.strip().get_speed() == CASES[case]['sensitivity']
				)
	
	
	def test_feedback(self):
		"""
		Tests if all feedback setting are parsed and applied
		after .compress() is called.
		"""
		for case in CASES:
			if hasattr(Action.ALL[case], 'set_haptic'):
				print "Testing 'feedback' on %s" % (case,)
				try:
					a = parser.from_json_data(CASES[case]).compress()
					print case, a
				except Exception:
					print "Failed to parse", CASES[case]['action']
					raise
				assert a.get_haptic().get_position() == CASES[case]['feedback'][0]
	
	
	def test_multi(self):
		"""
		Tests if feedback and sensitivity setting are parsed and applied
		to actions in multiaciton.
		"""
		a = parser.from_json_data({
			'action': """feedback(BOTH,
				sens(2.0, 3.0, 4.0,
					circular(REL_HWHEEL) and gyroabs(None, ABS_Y, ABS_Z)
				))"""
		}).compress()
		assert a.actions[0].get_haptic().get_position().name == "BOTH"
		for action in a.actions:
			assert action.get_speed()[0] == 2.0
	
	
	def test_macro(self):
		"""
		Tests if feedback and sensitivity setting are parsed and applied
		to actions in basic macro.
		"""
		a = parser.from_json_data({
			'action': """feedback(BOTH,
				sens(2.0, 3.0, 4.0,
					circular(REL_HWHEEL) ; gyroabs(None, ABS_Y, ABS_Z)
				))"""
		}).compress()
		for action in a.actions:
			assert action.get_haptic().get_position().name == "BOTH"
			assert action.get_speed()[0] == 2.0
