from scc.uinput import Keys, Axes, Rels
from scc.actions import *
from scc.modifiers import BallModifier
from . import parser
import inspect

class TestActions(object):
	
	# def test_tests(self):
	#	Tests if this class has test for every Action defined in actions.py.
	#	Removed: profile is not parsed this way anymore, so newly added actions
	#			don't have to support what's tested.
	
	
	def test_none(self):
		"""
		Tests if empty json dict or dict without action is parsed NoAction.
		"""
		assert isinstance(parser.from_json_data({}), NoAction)
		assert isinstance(parser.from_json_data({ 'action' : 'None' }), NoAction)
		assert isinstance(parser.from_json_data({ '___' : 'Invalid' }), NoAction)
	
	
	def test_axis(self):
		"""
		Tests if AxisAction is parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'axis(ABS_X)' }), AxisAction)
		assert parser.from_json_data({ 'action' : 'axis(ABS_X)' }).id == Axes.ABS_X
	
	
	def test_raxis(self):
		"""
		Tests if RAxisAction is parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'raxis(ABS_X)' }), RAxisAction)
		assert parser.from_json_data({ 'action' : 'raxis(ABS_X)' }).id == Axes.ABS_X
	
	
	def test_hats(self):
		"""
		Tests if every Hat* actions can be parsed correctly from json.
		"""	
		assert isinstance(parser.from_json_data({ 'action' : 'hatup(ABS_X)' }), HatUpAction)
		assert isinstance(parser.from_json_data({ 'action' : 'hatdown(ABS_X)' }), HatDownAction)
		assert isinstance(parser.from_json_data({ 'action' : 'hatleft(ABS_X)' }), HatLeftAction)
		assert isinstance(parser.from_json_data({ 'action' : 'hatright(ABS_X)' }), HatRightAction)
		
		assert parser.from_json_data({ 'action' : 'hatup(ABS_X)' }).id == Axes.ABS_X
		assert parser.from_json_data({ 'action' : 'hatdown(ABS_X)' }).id == Axes.ABS_X
		assert parser.from_json_data({ 'action' : 'hatleft(ABS_X)' }).id == Axes.ABS_X
		assert parser.from_json_data({ 'action' : 'hatright(ABS_X)' }).id == Axes.ABS_X
		
		assert parser.from_json_data({ 'action' : 'hatup(ABS_X)' }).min == 0
		assert parser.from_json_data({ 'action' : 'hatdown(ABS_X)' }).min == 0
		assert parser.from_json_data({ 'action' : 'hatleft(ABS_X)' }).min == 0
		assert parser.from_json_data({ 'action' : 'hatright(ABS_X)' }).min == 0
		
		assert parser.from_json_data({ 'action' : 'hatup(ABS_X)' }).max == STICK_PAD_MIN + 1
		assert parser.from_json_data({ 'action' : 'hatdown(ABS_X)' }).max == STICK_PAD_MAX - 1
		assert parser.from_json_data({ 'action' : 'hatleft(ABS_X)' }).max == STICK_PAD_MIN + 1
		assert parser.from_json_data({ 'action' : 'hatright(ABS_X)' }).max == STICK_PAD_MAX - 1
	
	
	def test_mouse(self):
		"""
		Tests if MouseAction is parsed correctly from json.
		"""
		assert parser.from_json_data({ 'action' : 'mouse()' })._mouse_axis == None
		assert parser.from_json_data({ 'action' : 'trackpad()' })._mouse_axis == None
		assert parser.from_json_data({ 'action' : 'mouse(REL_WHEEL)' })._mouse_axis == Rels.REL_WHEEL


	def test_mouseabs(self):
		"""
		Tests if MouseAction is parsed correctly from json.
		"""
		assert parser.from_json_data({ 'action' : 'mouseabs(REL_X)' })._mouse_axis == Rels.REL_X
		assert parser.from_json_data({ 'action' : 'mouseabs()' })._mouse_axis is None
	
	
	def test_area(self):
		"""
		Tests if AreaAction are parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'area(10, 10, 50, 50)' }), AreaAction)
		assert parser.from_json_data({ 'action' : 'area(10, 10, 50, 50)' }).coords == (10, 10, 50, 50)
	
	
	def test_relarea(self):
		"""
		Tests if  RelAreaAction are parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'relarea(10, 10, 50, 50)' }), RelAreaAction)
		assert parser.from_json_data({ 'action' : 'relarea(10, 10, 50, 50)' }).coords == (10, 10, 50, 50)
	
	
	def test_winarea(self):
		"""
		Tests if WinAreaAction are parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'winarea(10, 10, 50, 50)' }), WinAreaAction)
		assert parser.from_json_data({ 'action' : 'winarea(10, 10, 50, 50)' }).coords == (10, 10, 50, 50)
	
	
	def test_relwinarea(self):
		"""
		Tests if RelWinAreaAction are parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'relwinarea(10, 10, 50, 50)' }), RelWinAreaAction)
		assert parser.from_json_data({ 'action' : 'relwinarea(10, 10, 50, 50)' }).coords == (10, 10, 50, 50)
	
	
	def test_gyro(self):
		"""
		Tests if GyroAction is parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'gyro(ABS_X)' }), GyroAction)
		
		assert parser.from_json_data({ 'action' : 'gyro(ABS_X)' }).axes[0] == Axes.ABS_X
		assert parser.from_json_data({ 'action' : 'gyro(ABS_X)' }).axes[1] is None
		assert parser.from_json_data({ 'action' : 'gyro(ABS_X, ABS_Y)' }).axes[1] == Axes.ABS_Y
		assert parser.from_json_data({ 'action' : 'gyro(ABS_X, ABS_Y)' }).axes[2] is None
		assert parser.from_json_data({ 'action' : 'gyro(ABS_X, ABS_Y, ABS_Z)' }).axes[2] == Axes.ABS_Z
	
	
	def test_gyroabs(self):
		"""
		Tests if GyroAbsAction is parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'gyroabs(ABS_X)' }), GyroAbsAction)
		
		assert parser.from_json_data({ 'action' : 'gyroabs(ABS_X)' }).axes[0] == Axes.ABS_X
		assert parser.from_json_data({ 'action' : 'gyroabs(ABS_X)' }).axes[1] is None
		assert parser.from_json_data({ 'action' : 'gyroabs(ABS_X, ABS_Y)' }).axes[1] == Axes.ABS_Y
		assert parser.from_json_data({ 'action' : 'gyroabs(ABS_X, ABS_Y)' }).axes[2] is None
		assert parser.from_json_data({ 'action' : 'gyroabs(ABS_X, ABS_Y, ABS_Z)' }).axes[2] == Axes.ABS_Z
	
	
	def test_resetgyro(self):
		"""
		Tests if ResetGyroAction is parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'resetgyro()' }), ResetGyroAction)
	
	
	def test_tilt(self):
		"""
		Tests if TiltAction can be converted to string and
		parsed back to same action.
		"""
		# With only one button
		assert parser.from_json_data({
			'action' : 'tilt( button(KEY_D) )'
		}).actions[0].button == Keys.KEY_D
		
		# With all buttons
		assert parser.from_json_data({
			'action' : 'tilt( button(KEY_D), button(KEY_U), button(KEY_L), button(KEY_R))'
		}).actions[3].button == Keys.KEY_R
	
	
	def test_trackball(self):
		"""
		Tests if TrackballAction is parsed correctly from json.
		"""
		# assert isinstance(parser.from_json_data({ 'action' : 'trackball' }), TrackballAction)
		a = parser.from_json_data({ 'action' : 'trackball' })
		assert isinstance(a, BallModifier)
		assert isinstance(a.action, MouseAction)
	
	
	def test_button(self):
		"""
		Tests if ButtonAction is parsed correctly from json.
		"""
		assert isinstance(parser.from_json_data({ 'action' : 'button(KEY_X)' }), ButtonAction)
		
		assert parser.from_json_data({ 'action' : 'button(KEY_X)' }).button == Keys.KEY_X
		assert parser.from_json_data({ 'action' : 'button(KEY_X)' }).button2 is None
		assert parser.from_json_data({ 'action' : 'button(KEY_X, KEY_Z)' }).button == Keys.KEY_X
		assert parser.from_json_data({ 'action' : 'button(KEY_X, KEY_Z)' }).button2 == Keys.KEY_Z
	
	
	def test_multiaction(self):
		"""
		Tests if MultiAction is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : 'button(KEY_X) and button(KEY_Y)' })
		assert isinstance(a, MultiAction)
		assert isinstance(a.actions[0], ButtonAction)
		assert a.actions[0].button == Keys.KEY_X
		assert isinstance(a.actions[1], ButtonAction)
		assert a.actions[1].button == Keys.KEY_Y
	
	
	def test_dpad(self):
		"""
		Tests if DPadAction is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'dpad' : [{
				'action' : 'button(KEY_A)'
				} , {
				'action' : 'button(KEY_B)'
				} , {
				'action' : 'button(KEY_C)'
				} , {
				'action' : 'button(KEY_D)'
			}]
		})
		
		assert isinstance(a, DPadAction)
		for sub in a.actions:
			assert isinstance(sub, ButtonAction)
	
	
	def test_ring(self):
		"""
		Tests if DPadAction is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'ring' : {
				'radius' : 0.3,
				'outer' : {
					'dpad' : [{
						'action' : 'button(KEY_A)'
						} , {
						'action' : 'button(KEY_B)'
						} , {
						'action' : 'button(KEY_C)'
						} , {
						'action' : 'button(KEY_D)'
					}]
				},
				'inner' : {
					'X' : { 'action' : 'axis(ABS_X)' },
					'Y' : { 'action' : 'axis(ABS_Y)' },
				}
			}
		})
		
		assert isinstance(a.outer, DPadAction)
		for sub in a.outer.actions:
			assert isinstance(sub, ButtonAction)
		assert isinstance(a.inner, XYAction)
		for sub in a.inner.actions:
			assert isinstance(sub, AxisAction)
	
	
	def test_dpad8(self):
		"""
		Tests if DPad8Action is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'dpad' : [{
				'action' : 'button(KEY_A)'
				} , {
				'action' : 'button(KEY_B)'
				} , {
				'action' : 'button(KEY_C)'
				} , {
				'action' : 'button(KEY_D)'
				} , {
				'action' : 'button(KEY_E)'
				} , {
				'action' : 'button(KEY_F)'
				} , {
				'action' : 'button(KEY_G)'
				} , {
				'action' : 'button(KEY_H)'
			}]
		})
		
		print(a)
		print(a.actions)
		assert isinstance(a, DPadAction)
		for sub in a.actions:
			assert isinstance(sub, ButtonAction)
	
	
	def test_XY(self):
		"""
		Tests if XYAction is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'X' : { 'action' : 'axis(ABS_X)' },
			'Y' : { 'action' : 'axis(ABS_Y)' },
		})
		
		assert isinstance(a, XYAction)
		assert isinstance(a.x, AxisAction)
		assert isinstance(a.y, AxisAction)
	
	
	def test_trigger(self):
		"""
		Tests if TriggerAction is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : 'button(KEY_X)',
			'levels' : [ 10, 80 ]
		})
		
		assert isinstance(a, TriggerAction)
		assert isinstance(a.action, ButtonAction)
		assert a.press_level == 10
		assert a.release_level == 80
