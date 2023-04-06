from scc.uinput import Keys, Axes, Rels
from scc.actions import ButtonAction, AxisAction, GyroAction
from scc.constants import SCButtons, HapticPos
from scc.modifiers import *
from . import parser
import inspect

def _is_axis_with_value(a, value=Axes.ABS_X):
	"""
	Common part of all tests; Check if parsed action
	is AxisAction with given value as parameter.
	"""
	assert isinstance(a, AxisAction)
	assert a.id == value
	return True


class TestModifiers(object):
	
	def test_tests(self):
		"""
		Tests if this class has test for each known modifier defined.
		"""
		for cls in list(Action.ALL.values()):
			if "/modifiers.py" in inspect.getfile(cls):
				method_name = "test_%s" % (cls.COMMAND,)
				assert hasattr(self, method_name), \
					"There is no test for %s modifier" % (cls.COMMAND)
	
	
	def test_name(self):
		"""
		Tests if NameModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'name' : 'hithere'
		})
		
		# NameModifier is lost in parsing
		assert not isinstance(a, NameModifier)
		assert a.name == 'hithere'
		assert _is_axis_with_value(a)
	
	
	def test_click(self):
		"""
		Tests if ClickModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'click' : True
		})
		
		assert isinstance(a, ClickModifier)
		assert _is_axis_with_value(a.action)
	
	
	def test_pressed(self):
		"""
		Tests if PressedModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : "pressed(axis(ABS_X))" })
		assert isinstance(a, PressedModifier)
		assert _is_axis_with_value(a.action)
	
	
	def test_released(self):
		"""
		Tests if ReleasedModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : "released(axis(ABS_X))" })
		assert isinstance(a, ReleasedModifier)
		assert _is_axis_with_value(a.action)
	
	
	def test_touched(self):
		"""
		Tests if TouchedModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : "touched(button(KEY_A))" })
		assert isinstance(a, TouchedModifier)
	
	
	def test_untouched(self):
		"""
		Tests if UntouchedModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : "untouched(button(KEY_A))" })
		assert isinstance(a, UntouchedModifier)
	
	
	def test_circular(self):
		"""
		Tests if CircularModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'circular' : True
		})
		assert isinstance(a, CircularModifier)
	
	
	def test_circularabs(self):
		"""
		Tests if CircularModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'circularabs' : True
		})
		assert isinstance(a, CircularAbsModifier)
	
	
	def test_ball(self):
		"""
		Tests if BallModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'ball' : True
		})
		
		assert isinstance(a, BallModifier)
		assert _is_axis_with_value(a.action)
	
	
	def test_smooth(self):
		"""
		Tests if SmoothModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'smooth' : [ 5, 0.3 ]
		})
		
		assert isinstance(a, SmoothModifier)
		assert a.level == 5
		assert a.multiplier == 0.3
		assert _is_axis_with_value(a.action)
	
	
	def test_deadzone(self):
		"""
		Tests if DeadzoneModifier is parsed correctly from json.
		"""
		# One parameter
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'deadzone' : { 'upper' : 300 }
		})
		
		assert isinstance(a, DeadzoneModifier)
		assert a.upper == 300
		assert _is_axis_with_value(a.action)
		
		# Two parameters
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'deadzone' : { 'upper' : 300, 'lower' : 50 }
		})
		
		assert isinstance(a, DeadzoneModifier)
		assert a.lower == 50
		assert _is_axis_with_value(a.action)
	
	
	def test_sens(self):
		"""
		Tests if SensitivityModifier is parsed correctly from json.
		"""
		# Simple
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'sensitivity' : [ 2.0, 3.0, 4.0 ]
		})
		assert isinstance(a, SensitivityModifier)
		assert a.speeds == [ 2.0, 3.0, 4.0 ]
		assert _is_axis_with_value(a.action)
		
		# Hold and doubleclick
		a = parser.from_json_data({
			'hold' : {
				"action" : "mouse(ROLL)",
				'sensitivity' : [ 3.0, 4.0 ]
			},
			"doubleclick" : {
				"action" : "gyro(ABS_RZ, ABS_RX, ABS_Z)",
				'sensitivity' : [ 7.0, 8.0, 9.0 ]
			},
			"action" : "axis(ABS_Z)",
			'sensitivity' : [ 10.0, ]
		}).compress()
		assert isinstance(a.holdaction, MouseAction) and a.holdaction.get_speed() == ( 3.0, 4.0 )
		assert isinstance(a.action, GyroAction) and a.action.get_speed() == ( 7.0, 8.0, 9.0 )
		assert isinstance(a.normalaction, AxisAction) and a.normalaction.get_speed() == ( 10.0, )
		
		# Modeshift
		a = parser.from_json_data({
			'modes' : {
				"A" : {
					"action" : "mouse(ROLL)",
					'sensitivity' : [ 3.0, 4.0 ]
				},
				"B" : {
					"action" : "axis(ABS_X)",
					'sensitivity' : [ 7.0, ]
				},
				"X" : {
					"action" : "gyro(ABS_RZ, ABS_RX, ABS_Z)",
					'sensitivity' : [ 8.0, 9.0, 10.0 ]
				},
			},
			"action" : "axis(ABS_Z)",
			'sensitivity' : [ 12.0, ]
		}).compress()
		assert isinstance(a.mods[SCButtons.A], MouseAction) and a.mods[SCButtons.A].get_speed() == ( 3.0, 4.0 )
		assert isinstance(a.mods[SCButtons.B], AxisAction) and a.mods[SCButtons.B].get_speed() == ( 7.0, )
		assert isinstance(a.mods[SCButtons.X], GyroAction) and a.mods[SCButtons.X].get_speed() == ( 8.0, 9.0, 10.0 )
		assert isinstance(a.default, AxisAction) and a.default.get_speed() == ( 12.0, )
	
	
	def test_feedback(self):
		"""
		Tests if FeedbackModifier is parsed correctly from json.
		"""
		# One parameter
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'feedback' : [ "BOTH" ]
		})
		
		assert isinstance(a, FeedbackModifier)
		assert a.haptic.get_position() == HapticPos.BOTH
		assert _is_axis_with_value(a.action)
		
		# All parameters
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'feedback' : [ "RIGHT", 1024, 8, 2048 ]
		})
		
		assert isinstance(a, FeedbackModifier)
		assert a.haptic.get_position() == HapticPos.RIGHT
		assert a.haptic.get_amplitude() == 1024
		assert a.haptic.get_frequency() == 8
		assert a.haptic.get_period() == 2048
		assert _is_axis_with_value(a.action)
	
	
	def test_rotate(self):
		"""
		Tests if RotateInputModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : "axis(ABS_X)",
			'rotate' : 33.14
		})
		
		assert isinstance(a, RotateInputModifier)
		assert a.angle == 33.14
		assert _is_axis_with_value(a.action)
	
	
	def test_mode(self):
		"""
		Tests if ModeModifier is parsed correctly from json.
		"""
		# Without default
		a = parser.from_json_data({
			'modes' : {
				'A'  : { 'action' : "axis(ABS_X)" },
				'B'  : { 'action' : "axis(ABS_Y)" },
				'LT' : { 'action' : "axis(ABS_Z)" },
			}
		})
		
		assert isinstance(a, ModeModifier)
		assert _is_axis_with_value(a.mods[SCButtons.A],  Axes.ABS_X)
		assert _is_axis_with_value(a.mods[SCButtons.B],  Axes.ABS_Y)
		assert _is_axis_with_value(a.mods[SCButtons.LT], Axes.ABS_Z)
		
		# With default
		a = parser.from_json_data({
			'action' : 'axis(ABS_RX)',
			'modes' : {
				'X'  : { 'action' : "axis(ABS_X)" },
				'RT' : { 'action' : "axis(ABS_Z)" },
			}
		})
		
		assert isinstance(a, ModeModifier)
		assert _is_axis_with_value(a.default,  Axes.ABS_RX)
		assert _is_axis_with_value(a.mods[SCButtons.X], Axes.ABS_X)
		assert _is_axis_with_value(a.mods[SCButtons.RT], Axes.ABS_Z)
	
	
	def test_doubleclick(self):
		"""
		Tests if DoubleclickModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : 'axis(ABS_RX)',
			'doubleclick' : {
				'action' : "axis(ABS_X)"
			}
		})
		
		assert isinstance(a, DoubleclickModifier)
		assert _is_axis_with_value(a.normalaction,  Axes.ABS_RX)
		assert _is_axis_with_value(a.action, Axes.ABS_X)
		assert not a.holdaction
	
	
	def test_hold(self):
		"""
		Tests if HoldModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : 'axis(ABS_RX)',
			'hold' : {
				'action' : "axis(ABS_X)"
			}
		})
		
		assert isinstance(a, HoldModifier)
		assert _is_axis_with_value(a.normalaction,  Axes.ABS_RX)
		assert _is_axis_with_value(a.holdaction, Axes.ABS_X)
		assert not a.action
