from scc.actions import Action, ButtonAction, AxisAction, MouseAction
from scc.constants import SCButtons, STICK, HapticPos
from scc.uinput import Keys, Axes, Rels
from scc.modifiers import *
from . import _parses_as_itself, parser
import inspect

class TestModifiers(object):
	
	def test_tests(self):
		"""
		Tests if this class has test for each known modifier defined.
		"""
		for cls in Action.ALL.values():
			if "/modifiers.py" in inspect.getfile(cls):
				if cls in (HoldModifier, DoubleclickModifier,):
					# Skip over some hard-coded cases, these have
					# tests merged together under weird names
					continue
				method_name = "test_%s" % (cls.COMMAND,)
				assert hasattr(self, method_name), \
					"There is no test for %s modifier" % (cls.COMMAND)
	
	
	def test_name(self):
		"""
		Tests if NameModifier can be converted to string and parsed
		back to same.
		"""
		assert _parses_as_itself(NameModifier("Not A Button",
			ButtonAction(Keys.KEY_A)))
	
	
	def test_click(self):
		"""
		Tests if ClickModifier can be converted to string and parsed
		back to same.
		"""
		assert _parses_as_itself(ClickModifier(AxisAction(Axes.ABS_X)))
	
	
	def test_ball(self):
		"""
		Tests if BallModifier can be converted to string and parsed
		back to same.
		"""
		assert _parses_as_itself(BallModifier(AxisAction(Axes.ABS_X)))
		assert _parses_as_itself(BallModifier(MouseAction()))


	def test_deadzone(self):
		"""
		Tests if DeadzoneModifier can be converted to string and parsed
		back to same.
		"""
		# Lower only
		assert _parses_as_itself(DeadzoneModifier(100, AxisAction(Axes.ABS_X)))
		# Lower and upper
		assert _parses_as_itself(DeadzoneModifier(100, 20000, AxisAction(Axes.ABS_X)))
	
	
	def test_mode(self):
		"""
		Tests if ModeModifier can be converted to string and parsed
		back to same.
		"""
		# Without default
		assert _parses_as_itself(ModeModifier(
			SCButtons.A, AxisAction(Axes.ABS_X),
			SCButtons.B, AxisAction(Axes.ABS_Y),
		))
		# With default
		assert _parses_as_itself(ModeModifier(
			SCButtons.A, AxisAction(Axes.ABS_X),
			SCButtons.B, AxisAction(Axes.ABS_Y),
			AxisAction(Axes.ABS_Z)
		))
	
	
	def test_hold_doubleclick(self):
		"""
		Tests if DoubleclickModifier and HoldModifier
		can be converted to string and parsed back to same.
		"""
		for cls in (DoubleclickModifier, HoldModifier):
			# With doubleclick action only
			assert _parses_as_itself(cls(AxisAction(Axes.ABS_X)))
			# With doubleclick and normal action
			assert _parses_as_itself(cls(
				AxisAction(Axes.ABS_X),
				AxisAction(Axes.ABS_Y)
			))
			# With all parameters
			assert _parses_as_itself(cls(
				AxisAction(Axes.ABS_X),
				AxisAction(Axes.ABS_Y),
				1.5
			))
	
	
	def test_hold_doubleclick_combinations(self):
		"""
		Tests if combinations of DoubleclickModifier and HoldModifier
		are convertable to string and parsable back to same objects.
		"""
		# Test combinations
		assert _parses_as_itself(DoubleclickModifier(AxisAction(Axes.ABS_X),
			HoldModifier(AxisAction(Axes.ABS_Y)), AxisAction(Axes.ABS_Z)
		))
		assert _parses_as_itself(HoldModifier(AxisAction(Axes.ABS_X),
			DoubleclickModifier(AxisAction(Axes.ABS_Y)), AxisAction(Axes.ABS_Z)
		))
		assert _parses_as_itself(DoubleclickModifier(AxisAction(Axes.ABS_X),
			HoldModifier(AxisAction(Axes.ABS_Y), AxisAction(Axes.ABS_Z)
		)))
		assert _parses_as_itself(HoldModifier(AxisAction(Axes.ABS_X),
			DoubleclickModifier(AxisAction(Axes.ABS_Y), AxisAction(Axes.ABS_Z)
		)))
	
	
	def test_sens(self):
		"""
		Tests if SensitivityModifier can be converted to string and parsed
		back to same.
		"""
		assert _parses_as_itself(SensitivityModifier(2.0, AxisAction(Axes.ABS_X)))
		assert _parses_as_itself(SensitivityModifier(2.0, 3.0, AxisAction(Axes.ABS_X)))
		assert _parses_as_itself(SensitivityModifier(2.0, 3.0, 4.0, AxisAction(Axes.ABS_X)))
	
	
	def test_feedback(self):
		"""
		Tests if FeedbackModifier can be converted to string and parsed
		back to same.
		"""
		assert _parses_as_itself(FeedbackModifier(HapticPos.BOTH, MouseAction()))
		assert _parses_as_itself(FeedbackModifier(HapticPos.BOTH, 10, MouseAction()))
		assert _parses_as_itself(FeedbackModifier(HapticPos.BOTH, 10, 8, MouseAction()))
		assert _parses_as_itself(FeedbackModifier(HapticPos.BOTH, 10, 8, 512, MouseAction()))
	
	
	def test_rotate(self):
		"""
		Tests if RotateInputModifier can be converted to string and parsed
		back to same.
		"""
		assert _parses_as_itself(RotateInputModifier(61, MouseAction()))
