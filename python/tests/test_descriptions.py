from scc.actions import Action, NoAction
from scc.parser import ActionParser

parser = ActionParser()

class TestDescriptions(object):
	
	DESCRIPTIONS = {
		"button(Keys.KEY_ENTER)":			"ENTER",
		"button(Keys.KEY_ESC)":				"ESC",
		"button(Keys.BTN_RIGHT)":			"Mouse Right",
		"menu('Default.menu')":				"Menu",
		"mouse(Rels.REL_WHEEL)":			"Wheel",
		"mouse(Rels.REL_HWHEEL)":			"Horizontal Wheel",
		"ball(mouse())":					"Trackball",
		"XY(mouse(Rels.REL_HWHEEL), mouse(Rels.REL_WHEEL))":						"Horizontal Wheel Wheel",
		"ball(XY(mouse(Rels.REL_HWHEEL), mouse(Rels.REL_WHEEL)))":					"Mouse Wheel",
		"feedback(LEFT, ball(XY(mouse(Rels.REL_HWHEEL), mouse(Rels.REL_WHEEL))))":	"Mouse Wheel",
		"feedback(LEFT, ball(XY(axis(Axes.ABS_X), axis(Axes.ABS_Y))))":				"Mouse-like LStick",
		"feedback(LEFT, ball(XY(axis(Axes.ABS_RX), axis(Axes.ABS_RY))))":			"Mouse-like RStick",
		"dpad(button(Keys.KEY_UP), button(Keys.KEY_DOWN))":							"DPad",
		# TODO: WSAD, Arrows
	}
	
	def test_noaction_is_false(self):
		for a_str, desc in TestDescriptions.DESCRIPTIONS.items():
			a = parser.restart(a_str).parse()
			assert a.describe() == desc
		

