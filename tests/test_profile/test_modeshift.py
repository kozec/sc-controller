from scc.uinput import Keys, Axes, Rels
from scc.actions import ButtonAction, AxisAction, GyroAction
from scc.constants import SCButtons, HapticPos
from scc.modifiers import *
from . import parser
import inspect

class TestModeshift(object):
	"""
	Tests various combinations of modeshift and modifiers.
	Most are based on stuff that was failing in past.
	"""
	
	def test_146_1(self):
		"""
		https://github.com/kozec/sc-controller/issues/146
		"""
		STR = "mode(LB, dpad(button(Keys.KEY_UP)), rotate(3.8, sens(2.0, 2.0, ball(0.552, mouse()))))"
		a = parser.from_json_data({
			"action": "mouse()",
			"ball": [ 0.552 ],
			"rotate": 3.8,
			"sensitivity": [2.0, 2.0, 1.0],
			"modes": {
				"LB": {
					"dpad": [{
						"action": "button(Keys.KEY_UP)"
					}]
				}
			}
		})
		
		assert a.to_string() == STR
		assert isinstance(a, ModeModifier)
		assert isinstance(a.default, RotateInputModifier)
		sens = a.default.action
		assert isinstance(sens, SensitivityModifier)
		assert tuple(sens.speeds) == (2.0, 2.0, 1.0)
		ball = sens.action
		assert isinstance(ball, BallModifier)
		assert ball.friction == 0.552
	
	
	def test_146_2(self):
		"""
		https://github.com/kozec/sc-controller/issues/146
		"""
		STR = "mode(LGRIP, ball(XY(mouse(Rels.REL_HWHEEL), mouse(Rels.REL_WHEEL))), rotate(3.8, sens(2.0, 2.0, mouse())))"
		a = parser.from_json_data({	
			"action": "mouse()", 
			"rotate": 3.8, 
			"sensitivity": [2.0, 2.0, 1.0],
			"modes": {
				"LGRIP": {
					"X": { "action": "mouse(Rels.REL_HWHEEL)" }, 
					"Y": { "action": "mouse(Rels.REL_WHEEL)" }, 
					"ball": []
				}
			},
		})
		
		assert a.to_string() == STR
		assert isinstance(a, ModeModifier)
		assert isinstance(a.default, RotateInputModifier)
		sens = a.default.action
		assert isinstance(sens, SensitivityModifier)
		assert tuple(sens.speeds) == (2.0, 2.0, 1.0)
		lgrip = a.mods[SCButtons.LGRIP]
		assert isinstance(lgrip, BallModifier)
		assert isinstance(lgrip.action, XYAction)
