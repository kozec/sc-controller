from scc.uinput import Keys, Axes, Rels
from scc.actions import *
from . import _parses_as_itself, parser
import inspect

class TestActions(object):
	
	def test_tests(self):
		"""
		Tests if this class has test for every Action defined in acitons.py.
		"""
		for cls in Action.ALL.values():
			if "/actions.py" in inspect.getfile(cls):
				if HatAction in cls.__bases__ or cls in (NoAction,) :
					# Skip over some hard-coded cases, these have
					# tests merged together under weird names
					continue
				method_name = "test_%s" % (cls.COMMAND,)
				assert hasattr(self, method_name), \
					"There is no test for %s" % (cls.COMMAND)
	
	def test_none(self):
		"""
		Tests if everything what should parse as NoAction parses as NoAction.
		"""
		assert not parser.restart("None").parse()
		assert not parser.restart("None()").parse()
	
	
	def test_axis(self):
		"""
		Tests if AxisAction can be converted to string and parsed back to
		same action.
		"""	
		# With no optional parameters
		assert _parses_as_itself(AxisAction(Axes.ABS_X))
		# With min and max set
		assert _parses_as_itself(AxisAction(Axes.ABS_X, -10, 10.0))
	
	
	def test_raxis(self):
		"""
		Tests if RAxisAction can be converted to string and parsed back to
		same action.
		"""	
		# With no optional parameters
		assert _parses_as_itself(RAxisAction(Axes.ABS_X))
		# With min and max set
		assert _parses_as_itself(RAxisAction(Axes.ABS_X, -10, 10.0))
	
	
	def test_hats(self):
		"""
		Tests if every Hat* actions can be converted to string and parsed back to
		same action.
		"""	
		assert _parses_as_itself(HatUpAction(Axes.ABS_X))
		assert _parses_as_itself(HatDownAction(Axes.ABS_X))
		assert _parses_as_itself(HatLeftAction(Axes.ABS_X))
		assert _parses_as_itself(HatRightAction(Axes.ABS_X))


	def test_mouse(self):
		"""
		Tests if MouseAction can be converted to string and parsed back to
		same action.
		"""
		# With axis specified
		assert _parses_as_itself(MouseAction(Rels.REL_WHEEL))
		# Without axis (when used as trackbal)
		assert _parses_as_itself(MouseAction())
	
	
	def test_circular(self):
		"""
		Tests if CircularAction can be converted to string and parsed back to
		same action.
		"""
		assert _parses_as_itself(CircularAction(Rels.REL_WHEEL))


	def test_area(self):
		"""
		Tests if AreaAction can be converted to string and
		parsed back to same action.
		"""
		assert _parses_as_itself(AreaAction(10, 10, 50, 50))
	
	
	def test_relarea(self):
		"""
		Tests if RelAreaAction can be converted to string
		and parsed back to same action.
		"""
		assert _parses_as_itself(RelAreaAction(10, 10, 50, 50))
	
	
	def test_winarea(self):
		"""
		Tests if WinAreaAction can be converted to string
		and parsed back to same action.
		"""
		assert _parses_as_itself(WinAreaAction(10, 10, 50, 50))
	
	
	def test_relwinarea(self):
		"""
		Tests if RelWinAreaAction can be converted to
		string and parsed back to same action.
		"""
		assert _parses_as_itself(RelWinAreaAction(10, 10, 50, 50))
	
	
	def test_gyro(self):
		"""
		Tests if GyroAction can be converted to string and
		parsed back to same action.
		"""
		# With one, two and three axes set
		assert _parses_as_itself(GyroAction(Axes.ABS_X))
		assert _parses_as_itself(GyroAction(Axes.ABS_X, Axes.ABS_Y))
		assert _parses_as_itself(GyroAction(Axes.ABS_X, Axes.ABS_Y, Axes.ABS_Z))
	
	
	def test_gyroabs(self):
		"""
		Tests if GyroAbsAction can be converted to string and
		parsed back to same action.
		"""
		assert _parses_as_itself(GyroAbsAction(Axes.ABS_X))
		assert _parses_as_itself(GyroAbsAction(Axes.ABS_X, Axes.ABS_Y))
		assert _parses_as_itself(GyroAbsAction(Axes.ABS_X, Axes.ABS_Y, Axes.ABS_Z))
	
	
	def test_trackball(self):
		"""
		Tests if TrackballAction can be converted to string and parsed
		back to same action.
		"""
		assert _parses_as_itself(TrackballAction())
	
	
	def test_button(self):
		"""
		Tests if ButtonAction can be converted to string and parsed back to
		same action.
		"""
		# Simple
		assert _parses_as_itself(ButtonAction(Keys.BTN_LEFT))
		# Two buttons
		assert _parses_as_itself(ButtonAction(Keys.BTN_LEFT, Keys.BTN_RIGHT))
		# With one trigger setting
		assert _parses_as_itself(ButtonAction(Keys.BTN_LEFT, Keys.BTN_RIGHT, 10))
		# With two trigger settings
		assert _parses_as_itself(ButtonAction(Keys.BTN_LEFT, Keys.BTN_RIGHT, 10, 90))


	def test_multiaction(self):
		"""
		Tests if MultiAction can be converted to string and parsed back to
		same action.
		"""
		assert _parses_as_itself(MultiAction(
			ButtonAction(Keys.BTN_LEFT),
			ButtonAction(Keys.BTN_RIGHT),
			ButtonAction(Keys.BTN_MIDDLE)
		))


	def test_dpad(self):
		"""
		Tests if DPadAction can be converted to string and
		parsed back to same action.
		"""
		assert _parses_as_itself(DPadAction(
			ButtonAction(Keys.BTN_LEFT),
			ButtonAction(Keys.BTN_RIGHT),
			ButtonAction(Keys.BTN_MIDDLE),
			ButtonAction(Keys.KEY_A)
		))
	
	
	def test_dpad8(self):
		"""
		Tests if DPad8Action can be converted to string and
		parsed back to same action.
		"""
		assert _parses_as_itself(DPad8Action(
			ButtonAction(Keys.BTN_LEFT),
			ButtonAction(Keys.BTN_RIGHT),
			ButtonAction(Keys.BTN_MIDDLE),
			ButtonAction(Keys.KEY_A),
			ButtonAction(Keys.KEY_B),
			ButtonAction(Keys.KEY_C),
			ButtonAction(Keys.KEY_D),
			ButtonAction(Keys.KEY_E)
		))
	
	
	def test_XY(self):
		"""
		Tests if XYAciton can be converted to string and parsed back to
		same action.
		"""
		assert _parses_as_itself(XYAction(
			AxisAction(Axes.ABS_X),
			AxisAction(Axes.ABS_Y)
		))


	def test_trigger(self):
		"""
		Tests if TriggerAction can be converted to string and parsed back to
		same action.
		"""
		assert _parses_as_itself(TriggerAction(
			15, 234,
			ButtonAction(Keys.KEY_A)
		))
