from scc.constants import SCButtons, STICK, HapticPos, STICK_PAD_MAX
from scc.uinput import Keys, Axes, Rels
from scc.actions import *
from . import _parses_as_itself, _parse_compressed, parser
import inspect
import pytest


class TestModifiers(object):
	
	def test_name(self):
		"""
		Tests if NameModifier is parsed
		"""
		a = parser.restart("name('Not A Button', button(KEY_A))").parse()
		assert a.name == "Not A Button"
		a = a.compress()
		assert isinstance(a, ButtonAction)
	
	def test_click(self):
		"""
		Tests if ClickedModifier is parsed
		"""
		a = _parse_compressed("clicked(button(KEY_A))")
		assert isinstance(a, ClickedModifier)
		# Old name
		a = _parse_compressed("click(button(KEY_A))")
		assert isinstance(a, ClickedModifier)
	
	@pytest.mark.skip
	def test_pressed(self):
		"""
		Tests if ReleasedModifier is parsed
		"""
		a = _parse_compressed("released(button(KEY_A))")
		assert isinstance(a, ReleasedModifier)
	
	@pytest.mark.skip
	def test_released(self):
		"""
		Tests if PressedModifier is parsed
		"""
		a = _parse_compressed("pressed(axis(KEY_A))")
		assert isinstance(a, PressedModifier)	
	
	@pytest.mark.skip
	def test_touched(self):
		"""
		Tests if TouchedModifier is parsed
		"""
		a = _parse_compressed("touched(button(KEY_A))")
		assert isinstance(a, TouchedModifier)
	
	@pytest.mark.skip
	def test_untouched(self):
		"""
		Tests if UntouchedModifier is parsed
		"""
		a = _parse_compressed("untouched(button(KEY_A))")
		assert isinstance(a, UntouchedModifier)
	
	@pytest.mark.skip
	def test_circular(self):
		"""
		Tests if CircularModifier is parsed
		"""
		assert isinstance(_parse_compressed("circular(axis(ABS_X))"), CircularModifier)
		assert isinstance(_parse_compressed("circular(axis(REL_WHEEL))"), CircularModifier)
	
	@pytest.mark.skip
	def test_circularabs(self):
		"""
		Tests if CircularAbsModifier is parsed
		"""
		assert isinstance(_parse_compressed("circularabs(axis(ABS_X))"), CircularAbsModifier)
		assert isinstance(_parse_compressed("circularabs(axis(REL_WHEEL))"), CircularAbsModifier)
	
	def test_ball(self):
		"""
		Tests if BallModifier is parsed
		"""
		a = _parse_compressed("ball(axis(ABS_X))")
		assert isinstance(a, BallModifier)
		assert isinstance(a.action, AxisAction)
		assert a.action.axis == Axes.ABS_X
		a = _parse_compressed("ball(mouse())")
		assert isinstance(a, BallModifier)
		assert isinstance(a.action, MouseAction)
	
	def test_smooth(self):
		"""
		Tests if SmoothModifier is parsed
		"""
		a = _parse_compressed("smooth(5, 0.3, axis(ABS_X))")
		assert isinstance(a, SmoothModifier)
		assert isinstance(a.action, AxisAction)
		assert a.action.axis == Axes.ABS_X
		assert a.level == 5
		assert a.multiplier == 0.3
	
	def test_deadzone(self):
		"""
		Tests if DeadzoneModifier is parsed
		"""
		# Lower only
		a = _parse_compressed("deadzone(100, axis(ABS_X))")
		assert isinstance(a, DeadzoneModifier)
		assert a.lower == 100 and a.upper == STICK_PAD_MAX
		assert isinstance(a.action, AxisAction)
		assert a.action.axis == Axes.ABS_X
		# Lower and upper
		a = _parse_compressed("deadzone(100, 2000, axis(ABS_X))")
		assert isinstance(a, DeadzoneModifier)
		assert a.lower == 100 and a.upper == 2000
		assert isinstance(a.action, AxisAction)
		assert a.action.axis == Axes.ABS_X
	
	def test_mode(self):
		"""
		Tests if ModeModifier is parsed
		"""
		# Without default
		a = _parse_compressed("""mode(
			A, axis(ABS_X),
			B, axis(ABS_Y)
		)""")
		assert isinstance(a, ModeModifier)
		assert isinstance(a.mods[SCButtons.A], AxisAction)
		assert a.mods[SCButtons.A].axis == Axes.ABS_X
		
		# With default
		a = _parse_compressed("""mode(
			A, axis(ABS_X),
			B, axis(ABS_Y),
			button(KEY_A)
		)""")
		assert isinstance(a, ModeModifier)
		assert isinstance(a.mods[SCButtons.A], AxisAction)
		assert isinstance(a.default, ButtonAction)
		assert a.default.button == Keys.KEY_A
	
	def test_doubleclick(self):
		"""
		Tests if DoubleclickModifier is parsed
		"""
		# With doubleclick action only
		a = _parse_compressed("doubleclick(axis(ABS_X))")
		assert isinstance(a.action, AxisAction) and a.action.axis == Axes.ABS_X
		assert not a.holdaction and not a.normalaction
		# With doubleclick and normal action
		a = _parse_compressed("doubleclick(axis(ABS_X), axis(ABS_Y))")
		assert isinstance(a.action, AxisAction) and a.action.axis == Axes.ABS_X
		assert isinstance(a.normalaction, AxisAction) and a.normalaction.axis == Axes.ABS_Y
		assert not a.holdaction
		# With all parameters
		a = _parse_compressed("doubleclick(axis(ABS_X), axis(ABS_Y), 1.5)")
		assert isinstance(a.action, AxisAction) and a.action.axis == Axes.ABS_X
		assert isinstance(a.normalaction, AxisAction) and a.normalaction.axis == Axes.ABS_Y
		assert not a.holdaction
		assert a.timeout == 1.5
	
	def test_hold(self):
		"""
		Tests if HoldModifier is parsed
		"""
		# With hold action only
		a = _parse_compressed("hold(axis(ABS_X))")
		assert isinstance(a.holdaction, AxisAction) and a.holdaction.axis == Axes.ABS_X
		assert not a.action and not a.normalaction
		# With hold and normal action
		a = _parse_compressed("hold(axis(ABS_X), axis(ABS_Y))")
		assert isinstance(a.holdaction, AxisAction) and a.holdaction.axis == Axes.ABS_X
		assert isinstance(a.normalaction, AxisAction) and a.normalaction.axis == Axes.ABS_Y
		assert not a.action
		# With all parameters
		a = _parse_compressed("hold(axis(ABS_X), axis(ABS_Y), 1.5)")
		assert isinstance(a.holdaction, AxisAction) and a.holdaction.axis == Axes.ABS_X
		assert isinstance(a.normalaction, AxisAction) and a.normalaction.axis == Axes.ABS_Y
		assert not a.action
		assert a.timeout == 1.5	
	
	def test_hold_doubleclick_combinations(self):
		"""
		Tests if combinations of DoubleclickModifier and HoldModifier
		are parsed as expected
		"""
		a = _parse_compressed("doubleclick(axis(ABS_X), hold(axis(ABS_Y), axis(ABS_Z)))")
		assert isinstance(a.action, AxisAction) and a.action.axis == Axes.ABS_X
		assert isinstance(a.holdaction, AxisAction) and a.holdaction.axis == Axes.ABS_Y
		assert isinstance(a.normalaction, AxisAction) and a.normalaction.axis == Axes.ABS_Z
		a = _parse_compressed("hold(axis(ABS_X), doubleclick(axis(ABS_Y), axis(ABS_Z)))")
		assert isinstance(a.holdaction, AxisAction) and a.holdaction.axis == Axes.ABS_X
		assert isinstance(a.action, AxisAction) and a.action.axis == Axes.ABS_Y
		assert isinstance(a.normalaction, AxisAction) and a.normalaction.axis == Axes.ABS_Z
		a = _parse_compressed("doubleclick(hold(axis(ABS_RX), axis(ABS_RY)), axis(ABS_Z))")
		assert isinstance(a.action, AxisAction) and a.action.axis == Axes.ABS_RY
		assert isinstance(a.holdaction, AxisAction) and a.holdaction.axis == Axes.ABS_RX
		assert isinstance(a.normalaction, AxisAction) and a.normalaction.axis == Axes.ABS_Z
		a = _parse_compressed("hold(doubleclick(axis(ABS_Z), axis(ABS_RZ)), axis(ABS_X))")
		assert isinstance(a.action, AxisAction) and a.action.axis == Axes.ABS_Z
		assert isinstance(a.holdaction, AxisAction) and a.holdaction.axis == Axes.ABS_RZ
		assert isinstance(a.normalaction, AxisAction) and a.normalaction.axis == Axes.ABS_X
	
	def test_sens(self):
		"""
		Tests if SensitivityModifier can be converted to string and parsed
		back to same.
		"""
		# Simple stuff
		assert _parse_compressed("sens(2, axis(ABS_X))").strip().get_speed() == (2.0,)
		assert _parse_compressed("sens(2, 3, mouse())").strip().get_speed() == (2.0, 3.0)
		
		# Basic modifiers, sensitivity should always end applied to mouse() action
		a = _parse_compressed("sens(2, 3, click(mouse()))")
		print "###", a
		assert isinstance(a, ClickedModifier)
		assert isinstance(a.action, MouseAction) and a.action.get_speed() == (2.0, 3.0)
		a = _parse_compressed("sens(2, 3, deadzone(2.0, mouse()))")
		assert isinstance(a.action, MouseAction) and a.action.get_speed() == (2.0, 3.0)
		
		# Special case, sensitivity should be applied to ball(), not mouse()
		a = _parse_compressed("sens(2, 3, ball(mouse()))")
		assert isinstance(a.action, MouseAction) and a.action.get_speed() == (1.0, 1.0)
		assert isinstance(a, BallModifier) and a.get_speed() == (2.0, 3.0)
	
	@pytest.mark.skip
	def test_sens_skipped(self):
		""" Part of test_sens that can't work for now """
		assert _parse_compressed("sens(2, 3, 4, gyro(ABS_RZ, ABS_RX, ABS_Z))").strip().get_speed() == (2.0, 3.0, 4.0)
	
	def test_feedback(self):
		"""
		Tests if FeedbackModifier can be converted to string and parsed
		back to same.
		"""
		# TODO: Here, with actual tests
		assert _parses_as_itself(FeedbackModifier(HapticPos.BOTH, MouseAction()))
		assert _parses_as_itself(FeedbackModifier(HapticPos.BOTH, 10, MouseAction()))
		assert _parses_as_itself(FeedbackModifier(HapticPos.BOTH, 10, 8, MouseAction()))
		assert _parses_as_itself(FeedbackModifier(HapticPos.BOTH, 10, 8, 512, MouseAction()))
		# Bellow was failing in past
		assert _parses_as_itself(FeedbackModifier(HapticPos.LEFT, MouseAction()))
		assert _parses_as_itself(FeedbackModifier(HapticPos.RIGHT, MouseAction()))
	
	@pytest.mark.skip
	def test_rotate(self):
		"""
		Tests if RotateInputModifier can be converted to string and parsed
		back to same.
		"""
		a = _parse_compressed("rotate(61, mouse())")
		assert isinstance(a, RotateInputModifier)

