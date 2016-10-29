from scc.actions import Action, ButtonAction, AxisAction, MouseAction
from scc.constants import SCButtons, STICK, HapticPos
from scc.uinput import Keys, Axes, Rels
from scc.modifiers import *
from . import _parses_as, parser
import inspect

class TestModifiers(object):
	
	# TODO: Much more tests
	# TODO: test_tests
	
	def test_ball(self):
		"""
		Tests if BallModifier can be converted from string
		"""
		# All options
		assert _parses_as(
			"ball(15, 40, 15, 0.1, 3265, 4, axis(ABS_X))",
			BallModifier(15, 40, 15, 0.1, 3265, 4, AxisAction(Axes.ABS_X))
		)
