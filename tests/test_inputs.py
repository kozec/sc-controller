from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX
from scc.drivers.fake import FakeController
from scc.uinput import Dummy, Keys, Axes
from scc.constants import SCButtons
from scc.parser import ActionParser
from scc.profile import Profile
from scc.scheduler import Scheduler
from scc.mapper import Mapper
from collections import namedtuple
import time

"""
Tests various inputs for crashes and incorrect behaviour,
mostly using dummy outputs and FakeController
"""

FakeControllerInput = namedtuple('FakeControllerInput',
	'buttons ltrig rtrig stick_x stick_y lpad_x lpad_y rpad_x rpad_y '
	'gpitch groll gyaw q1 q2 q3 q4 '
)
ZERO_STATE = FakeControllerInput( *[0] * len(FakeControllerInput._fields) )
parser = ActionParser()

def input_test(fn):
	""" Decorator that creates usable mapper """
	def wrapper(*a):
		_time = time.time
		
		def fake_time():
			return fake_time.t
		def add(n):
			fake_time.t += n
		fake_time.t = _time()
		fake_time.add = add
		time.time = fake_time
		
		controller = FakeController(0)
		profile = Profile(parser)
		scheduler = Scheduler()
		mapper = Mapper(profile, scheduler, keyboard=False, mouse=False, gamepad=False, poller=None)
		mapper.keyboard = RememberingDummy()
		mapper.gamepad = RememberingDummy()
		mapper.mouse = RememberingDummy()
		mapper.set_controller(controller)
		mapper._testing = True
		mapper._tick_rate = 0.01
		
		_mapper_input = mapper.input
		def mapper_input(*a):
			add(mapper._tick_rate)
			_mapper_input(*a)
			scheduler.run()
		mapper.input = mapper_input
		
		a = list(a) + [ mapper ]
		try:
			return fn(*a)
		finally:
			time.time = _time
	return wrapper


class RememberingDummy(Dummy):
	def __init__(self, *a, **b):
		Dummy.__init__(self, *a, **b)
		self.pressed = set([])
		self.mouse_x = 0
		self.mouse_y = 0
		self.scroll_x = 0
		self.scroll_y = 0
		self.axes = {}
	
	
	def axisEvent(self, axis, val):
		self.axes[axis] = val
	
	
	def moveEvent(self, dx=0, dy=0):
		self.mouse_x += dx
		self.mouse_y += dy
	
	
	def scrollEvent(self, dx=0, dy=0):
		self.scroll_x += dx
		self.scroll_y += dx
	
	
	def pressEvent(self, keys):
		for k in keys:
			assert k not in self.pressed
			self.pressed.add(k)
	
	
	def releaseEvent(self, keys=[]):
		for k in keys:
			if k in self.pressed:
				self.pressed.remove(k)


class TestInputs(object):
	@input_test
	def test_button(self, mapper):
		"""
		Just test for test, this should work every time.
		"""
		mapper.profile.buttons[SCButtons.A] = (parser
			.restart("button(Keys.KEY_ENTER)")).parse()
		state = ZERO_STATE._replace(buttons=SCButtons.A)
		mapper.input(mapper.controller, ZERO_STATE, state)
		assert Keys.KEY_ENTER in mapper.keyboard.pressed
		mapper.input(mapper.controller, state, state._replace(buttons=0))
		assert Keys.KEY_ENTER not in mapper.keyboard.pressed
	
	
	@input_test
	def test_trackball(self, mapper):
		"""
		Tests trackball emulation
		"""
		mapper.profile.pads[Profile.LEFT] = (parser.restart(
			"ball(XY("
			"	mouse(Rels.REL_HWHEEL, 1.0), "
			"	mouse(Rels.REL_WHEEL, 1.0)"
			"))"
		)).parse()
		
		# Create movement over left pad
		state = ZERO_STATE
		for x in reversed(range(STICK_PAD_MIN * 2 / 3, -10, 1000)):
			new_state = state._replace(buttons=SCButtons.LPADTOUCH, lpad_x=x)
			mapper.input(mapper.controller, state, new_state)
			state = new_state
		assert mapper.mouse.scroll_x == -21000.0
		# Release left pad
		mapper.input(mapper.controller, state, ZERO_STATE)
		# 'Wait' for 2s
		for x in range(20):
			mapper.input(mapper.controller, ZERO_STATE, ZERO_STATE)
		assert int(mapper.mouse.scroll_x) == -24479
	
	
	@input_test
	def test_dpad(self, mapper):
		"""
		Tests WSAD
		"""
		mapper.profile.pads[Profile.LEFT] = (parser.restart(
			"dpad("
			"	button(Keys.KEY_W), button(Keys.KEY_S),"
			"	button(Keys.KEY_A), button(Keys.KEY_D))"
		)).parse()
		
		# Create movements over left pad
		# - A
		state = ZERO_STATE._replace(buttons=SCButtons.LPADTOUCH, lpad_x=STICK_PAD_MIN)
		mapper.input(mapper.controller, ZERO_STATE, state)
		assert Keys.KEY_A in mapper.keyboard.pressed
		mapper.input(mapper.controller, state, ZERO_STATE)
		# - S
		state = ZERO_STATE._replace(buttons=SCButtons.LPADTOUCH, lpad_y=STICK_PAD_MIN)
		mapper.input(mapper.controller, ZERO_STATE, state)
		assert Keys.KEY_S in mapper.keyboard.pressed
		mapper.input(mapper.controller, state, ZERO_STATE)
		# - D
		state = ZERO_STATE._replace(buttons=SCButtons.LPADTOUCH, lpad_x=STICK_PAD_MAX)
		mapper.input(mapper.controller, ZERO_STATE, state)
		assert Keys.KEY_D in mapper.keyboard.pressed
		mapper.input(mapper.controller, state, ZERO_STATE)
	
	
	@input_test
	def test_joystick_camera(self, mapper):
		"""
		Tests joystick camera, mapping trackball to right joystick
		"""
		mapper.profile.pads[Profile.RIGHT] = (parser.restart(
			"ball(XY("
			"	axis(Axes.ABS_RX),"
			"	axis(Axes.ABS_RY)"
			"))"
		)).parse()
		
		# Create movement over right pad
		state = ZERO_STATE
		for x in range(10, STICK_PAD_MAX * 2 / 3, 3000):
			new_state = state._replace(buttons=SCButtons.RPADTOUCH, rpad_x=x)
			mapper.input(mapper.controller, state, new_state)
			state = new_state
		assert mapper.gamepad.axes[Axes.ABS_RX] == 3000
		# Release left pad
		mapper._tick_rate = 0.001
		mapper.input(mapper.controller, state, ZERO_STATE)
		# 'Wait' for 1s
		for x in range(100):
			mapper.input(mapper.controller, ZERO_STATE, ZERO_STATE)
		assert mapper.gamepad.axes[Axes.ABS_RX] == 3510
		# 'Wait' for another 0.5s
		for x in range(50):
			mapper.input(mapper.controller, ZERO_STATE, ZERO_STATE)
		assert mapper.gamepad.axes[Axes.ABS_RX] == 1570
		# 'Wait' for long time so stick recenters
		for x in range(100):
			mapper.input(mapper.controller, ZERO_STATE, ZERO_STATE)
		assert mapper.gamepad.axes[Axes.ABS_RX] == 0
	
	
	@input_test
	def test_modeshift(self, mapper):
		"""
		Tests WSAD
		"""
		mapper.profile.buttons[SCButtons.A] = (parser.restart(
			"mode(B, button(Keys.KEY_V), button(Keys.KEY_Y))"
		)).parse()
		
		# Press single button
		state = ZERO_STATE._replace(buttons=SCButtons.A)
		mapper.input(mapper.controller, ZERO_STATE, state)
		assert Keys.KEY_Y in mapper.keyboard.pressed
		mapper.input(mapper.controller, state, ZERO_STATE)
		assert Keys.KEY_Y not in mapper.keyboard.pressed
		
		# Press modeshifting button
		state = ZERO_STATE._replace(buttons=SCButtons.B)
		mapper.input(mapper.controller, ZERO_STATE, state)
		assert Keys.KEY_Y not in mapper.keyboard.pressed
		assert Keys.KEY_V not in mapper.keyboard.pressed
		
		# Press button again
		_state, state = state, state._replace(buttons=SCButtons.B | SCButtons.A)
		mapper.input(mapper.controller, _state, state)
		assert Keys.KEY_V in mapper.keyboard.pressed
		assert Keys.KEY_Y not in mapper.keyboard.pressed
		
		# Release modeshifting button
		_state, state = state, state._replace(buttons=SCButtons.A)
		mapper.input(mapper.controller, _state, state)
		assert Keys.KEY_V in mapper.keyboard.pressed
		assert Keys.KEY_Y not in mapper.keyboard.pressed
		
		# Release original button and press it again
		_state, state = state, state._replace(buttons=0)
		mapper.input(mapper.controller, _state, state)
		assert Keys.KEY_V not in mapper.keyboard.pressed
		assert Keys.KEY_Y not in mapper.keyboard.pressed

		_state, state = state, state._replace(buttons=SCButtons.A)
		mapper.input(mapper.controller, _state, state)
		assert Keys.KEY_Y in mapper.keyboard.pressed
