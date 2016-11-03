from scc.uinput import Keys, Axes, Rels
from scc.constants import SCButtons, HapticPos
from scc.special_actions import *
from scc.actions import ButtonAction
from . import parser
import inspect

MENU_CLASSES = MenuAction, GridMenuAction, RadialMenuAction

class TestSpecialActions(object):
	
	def test_tests(self):
		"""
		Tests if this class has test for each known SpecialAction defined.
		"""
		for cls in Action.ALL.values():
			if "/special_actions.py" in inspect.getfile(cls):
				if cls in MENU_CLASSES:
					# Skip over some hard-coded cases, these have
					# tests merged together under weird names
					continue
				method_name = "test_%s" % (cls.COMMAND,)
				assert hasattr(self, method_name), \
					"There is no test for %s" % (cls.COMMAND)
	
	
	def test_profile(self):
		"""
		Tests if ChangeProfileAction is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : "profile('xyz')" })
		assert isinstance(a, ChangeProfileAction)
		assert a.profile == "xyz"
	
	
	def test_shell(self):
		"""
		Tests if ShellCommandAction is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : "shell('ls -la')" })
		assert isinstance(a, ShellCommandAction)
		assert a.command == "ls -la"
	
	
	def test_turnoff(self):
		"""
		Tests if TurnOffAction is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : "turnoff" })
		assert isinstance(a, TurnOffAction)
	
	
	def test_restart(self):
		"""
		Tests if RestartDaemonAction is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : "restart" })
		assert isinstance(a, RestartDaemonAction)
	
	
	def test_led(self):
		"""
		Tests if LockedAction is parsed correctly from json.
		"""
		a = parser.from_json_data({ 'action' : "led(66)" })
		assert isinstance(a, LedAction)
		assert a.brightness == 66
	
	
	def test_osd(self):
		"""
		Tests if OSDAction is parsed correctly from json.
		"""
		# With text
		a = parser.from_json_data({ 'action' : "osd('something')" })
		assert isinstance(a, OSDAction)
		assert a.text == "something"
		# As modifier
		a = parser.from_json_data({
			'action' : "button(KEY_X)",
			'osd' : True
		})
		assert isinstance(a, OSDAction)
		assert isinstance(a.action, ButtonAction)
	
	
	def test_menus(self):
		"""
		Tests if all Menu*Actions are parsed correctly from json.
		"""
		for cls in MENU_CLASSES:
			a_str = "%s('some.menu', LEFT, X, Y, True)" % (cls.COMMAND,)
			a = parser.from_json_data({ 'action' : a_str })
			assert isinstance(a, cls)
			assert a.control_with == HapticPos.LEFT
			assert a.confirm_with == SCButtons.X
			assert a.cancel_with == SCButtons.Y
			assert a.show_with_release == True
	
	
	def test_position(self):
		"""
		Tests if PositionModifier is parsed correctly from json.
		"""
		a = parser.from_json_data({
			'action' : "menu('some.menu', LEFT, X, Y, True)",
			'position' : [ -10, 10 ]
		}).compress()
		
		assert isinstance(a, MenuAction)
		assert a.x == -10
		assert a.y ==  10
	
	
	def test_keyboard(self):
		"""
		Tests if KeyboardAction is parsed correctly from json.
		"""
		# With text
		a = parser.from_json_data({ 'action' : "keyboard" })
		assert isinstance(a, KeyboardAction)
	
	
	def test_gestures(self):
		"""
		Tests if GesturesAction is parsed correctly from json.
		"""
		# Simple
		a = parser.from_json_data({
			'gestures' : {
				'UD' : { 'action' : 'turnoff' },
				'LR' : { 'action' : 'keyboard' }
			}
		})
		assert isinstance(a, GesturesAction)
		assert isinstance(a.gestures['UD'], TurnOffAction)
		assert isinstance(a.gestures['LR'], KeyboardAction)
		# With OSD
		a = parser.from_json_data({
			'gestures' : {
				'UD' : { 'action' : 'turnoff' },
			},
			'osd' : True
		})
		assert isinstance(a, OSDAction)
		assert isinstance(a.action, GesturesAction)
		assert isinstance(a.action.gestures['UD'], TurnOffAction)
