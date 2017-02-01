from scc.uinput import Keys, Axes, Rels
from scc.constants import SCButtons, HapticPos
from scc.modifiers import DoubleclickModifier
from scc.actions import Action, AxisAction
from scc.macros import Macro
from scc.parser import ActionParser

parser = ActionParser()

CASES = {
	# Contains all test cases that are tested by
	# test_sensitivity and test_feedback
	# This should contain key for every Action that supports setting feedback
	# or sensitivity. test_tests method tests whether it realy does.
	'axis'  : {
		'action' : 'axis(ABS_RX)',
		'sensitivity' : (2.0,)
	},
	'raxis'  : {
		'action' : 'axis(ABS_RX)',
		'sensitivity' : (2.0,)
	},
	'mouse' : {
		'action' : 'mouse',
		'sensitivity' : (2.0, 3.0,),
		'feedback' : ('BOTH',)
	},
	'mouseabs' : {
		'action' : 'mouseabs(REL_X)',
		'sensitivity' : (2.0, 3.0,)
	},
	'gyro' : {
		'action' : 'gyro(ABS_X, ABS_Y, ABS_Z)',
		'sensitivity' : (2.0, 3.0, 4.0,)
	},
	'tilt' : {
		'action' : 'tilt( button(KEY_D), button(KEY_U), button(KEY_L), button(KEY_R) )',
		'sensitivity' : (2.0, 3.0, 4.0,)
	},
	'gyroabs' : {
		'action' : 'gyroabs(ABS_X, ABS_Y, ABS_Z)',
		'sensitivity' : (2.0, 3.0, 4.0),
		'feedback' : ('BOTH',)
	},
	'hatup' :    { 'action' : 'hatup(ABS_X)',    'sensitivity' : (2.0,) },
	'hatdown' :  { 'action' : 'hatdown(ABS_X)',  'sensitivity' : (2.0,) },
	'hatleft' :  { 'action' : 'hatleft(ABS_X)',  'sensitivity' : (2.0,) },
	'hatright' : { 'action' : 'hatright(ABS_X)', 'sensitivity' : (2.0,) },
	'button' : {
		'action' : 'button(KEY_X)',
		'feedback' : ('BOTH',)
	},
	'circular' : {
		'action' : 'circular(REL_HWHEEL)',
		'sensitivity' : (2.0,),
		'feedback' : ('BOTH',)
	},
	'XY' : {
		'X' : { 'action' : 'axis(ABS_X)' },
		'Y' : { 'action' : 'axis(ABS_Y)' },
		'sensitivity' : (2.0, 3.0,),
		'feedback' : ('BOTH',)
	},
	'trigger' : {
		'action' : 'button(KEY_X)',
		'levels' : [ 10, 80 ],
		'feedback' : ('BOTH',)
	},
	'tilt' : {
		'action' : 'tilt( button(KEY_D), button(KEY_U), button(KEY_L), button(KEY_R) )',
		'sensitivity' : (2.0, 3.0, 4.0,)
	},
	'ball' : {
		'action' : 'ball(XY(axis(Axes.ABS_RX), axis(Axes.ABS_RY)))',
		'sensitivity' : (2.0, 3.0),
		'feedback' : ('BOTH',)
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
			if hasattr(cls, "set_speed"):
				assert cls.COMMAND in CASES, (
					"%s supports setting sensitivity, but "
					"there is no test case it" % (cls.COMMAND,))
				assert 'sensitivity' in CASES[cls.COMMAND], (
					"%s supports setting sensitivity, but "
					"case for it has no 'sensitivity' key it" % (
					cls.COMMAND,))
			if hasattr(cls, "set_haptic"):
				assert cls.COMMAND in CASES, (
					"%s supports feedback, but there is "
					"no test case it" % (cls.COMMAND,))
				assert 'feedback' in CASES[cls.COMMAND], (
					"%s supports feedback, but case for it has "
					"no 'feedback' key it" % (
					cls.COMMAND,))			
	
	
	def test_hold_doubleclick(self):
		"""
		Tests parsing of hold & doubleclick combination.
		"""
		a = parser.from_json_data({
			'action' : 'axis(ABS_RX)',
			'hold' : { 'action' : "axis(ABS_X)" },
			'doubleclick' : { 'action' : "axis(ABS_Z)" }
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
			if 'sensitivity' in CASES[case]:
				print "Testing 'sensitivity' on %s" % (case,)
				a = parser.from_json_data(CASES[case]).compress()
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
			if 'feedback' in CASES[case]:
				print "Testing 'feedback' on %s" % (case,)
				a = parser.from_json_data(CASES[case]).compress()
				assert a.get_haptic().get_position().name == CASES[case]['feedback'][0]
	
	
	def test_multi(self):
		"""
		Tests if feedback and sensitivity setting are parsed and applied
		to actions in multiaciton.
		"""
		a = parser.from_json_data({
			'action' : 'circular(REL_HWHEEL) and gyroabs(None, ABS_Y, ABS_Z)',
			'sensitivity' : (2.0, 3.0, 4.0),
			'feedback' : ('BOTH',)
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
			'action' : 'circular(REL_HWHEEL) ; gyroabs(None, ABS_Y, ABS_Z)',
			'sensitivity' : (2.0, 3.0, 4.0),
			'feedback' : ('BOTH',)
		}).compress()
		for action in a.actions:
			assert action.get_haptic().get_position().name == "BOTH"
			assert action.get_speed()[0] == 2.0
