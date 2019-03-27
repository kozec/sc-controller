from scc.constants import SCButtons, HapticPos
from scc.actions import DoubleclickModifier, SensitivityModifier, FeedbackModifier
from scc.actions import Action, AxisAction, Macro
from scc.parser import ActionParser
import pytest

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
	'hatup' :    { 'action' : 'hatup(ABS_X)',    'sensitivity' : (2.0,) },
	'hatdown' :  { 'action' : 'hatdown(ABS_X)',  'sensitivity' : (2.0,) },
	'hatleft' :  { 'action' : 'hatleft(ABS_X)',  'sensitivity' : (2.0,) },
	'hatright' : { 'action' : 'hatright(ABS_X)', 'sensitivity' : (2.0,) },
	'button' : {
		'action' : 'button(KEY_X)',
		'feedback' : ('BOTH',)
	},
	'XY' : {
		'action': 'XY(axis(ABS_X), axis(ABS_Y))',
		'sensitivity' : (2.0, 3.0,),
		'feedback' : ('BOTH',)
	},
	'relXY' : {
		'action': 'relXY(axis(ABS_RX), axis(ABS_RY))',
		'sensitivity' : (2.0, 3.0,),
		'feedback' : ('BOTH',)
	},
	'trigger' : {
		'action' : 'button(KEY_X)',
		'levels' : [ 10, 80 ],
		'feedback' : ('BOTH',)
	},
	'ball' : {
		'action' : 'ball(XY(axis(Axes.ABS_RX), axis(Axes.ABS_RY)))',
		'sensitivity' : (2.0, 3.0),
		'feedback' : ('BOTH',)
	},
}

_DISABLED = {
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
	'circular' : {
		'action' : 'mouse(REL_HWHEEL)',
		'circular' : True,
		'sensitivity' : (2.0,),
		'feedback' : ('BOTH',)
	},
	'circularabs' : {
		'action' : 'mouse(REL_HWHEEL)',
		'circularabs' : True,
		'sensitivity' : (2.0,),
		'feedback' : ('BOTH',)
	},
	"dpad" : {
		'action': '''dpad(
			button(Keys.KEY_W),
			button(Keys.KEY_S),
			button(Keys.KEY_A),
			button(Keys.KEY_D)
		)''',
		"feedback": ["LEFT", 32640]
	},
	"dpad8" : {
		"action": '''dpad(
			button(Keys.KEY_1),
			button(Keys.KEY_2),
			button(Keys.KEY_3),
			button(Keys.KEY_4),
			button(Keys.KEY_5),
			button(Keys.KEY_6),
			button(Keys.KEY_7),
			button(Keys.KEY_8)
		)''',
		"feedback": ["LEFT", 32640]
	},
	"hold": {
		"action": "hold(menu('Default.menu'), button(Keys.KEY_W))",
		"feedback": ["LEFT", 32640]
	},
	"menu" : {
		"action": "menu('Default.menu')",
		"feedback": ["LEFT", 32640]
	},
}

class TestCompress(object):
	"""
	Tests Aciton.compress method.
	Basically, tests how various combinations of modifiers interacts together.
	"""
	
	@pytest.mark.skip
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
		assert a.normalaction.axis == Axes.ABS_RX
		assert a.action.axis == Axes.ABS_Z
		assert a.holdaction.axis == Axes.ABS_X
	
	def test_sensitivity(self):
		"""
		Tests if all sensitivity setting are parsed and applied
		after .compress() is called.
		"""
		for case in CASES:
			if 'sensitivity' in CASES[case]:
				print "Testing 'sensitivity' on %s" % (case,)
				a = parser.restart(CASES[case]["action"]).parse()
				params = list(CASES[case]['sensitivity'])
				params += [ a ]
				a = SensitivityModifier(*params).compress()
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
				a = parser.restart(CASES[case]["action"]).parse()
				params = list(CASES[case]['feedback'])
				params += [ a ]
				a = FeedbackModifier(*params).compress()
				assert a.get_haptic().get_position().name == CASES[case]['feedback'][0]
	
	@pytest.mark.skip
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
	
	@pytest.mark.skip
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


if __name__ == "__main__":
	t = TestCompress()
	t.test_sensitivity()

