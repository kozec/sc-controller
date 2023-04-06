"""
Universal driver for gamepads managed by evdev.

Handles no devices by default. Instead of trying to guess which evdev device
is a gamepad and which user actually wants to be handled by SCC, list of enabled
devices is read from config file.
"""

from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX, TRIGGER_MIN, TRIGGER_MAX
from scc.constants import SCButtons, ControllerFlags
from scc.controller import Controller
from scc.paths import get_config_path
from scc.tools import clamp


HAVE_EVDEV = False
try:
	# Driver disables itself if evdev is not available
	import evdev
	from evdev import ecodes
	HAVE_EVDEV = True
except ImportError:
	class FakeECodes:
		def __getattr__(self, key):
			return key
	ecodes = FakeECodes()

from collections import namedtuple
import os, sys, binascii, json, logging
log = logging.getLogger("evdev")

TRIGGERS = "ltrig", "rtrig"
FIRST_BUTTON = 288

EvdevControllerInput = namedtuple('EvdevControllerInput',
	'buttons ltrig rtrig stick_x stick_y lpad_x lpad_y rpad_x rpad_y '
	'gpitch groll gyaw q1 q2 q3 q4 '
	'cpad_x cpad_y'
)

AxisCalibrationData = namedtuple('AxisCalibrationData',
	'scale offset center clamp_min clamp_max deadzone'
)

class EvdevController(Controller):
	"""
	Wrapper around evdev device.
	To keep stuff simple, this class tries to provide and use same methods
	as SCController class does.
	"""
	PADPRESS_EMULATION_TIMEOUT = 0.2
	ECODES = ecodes
	flags = ( ControllerFlags.HAS_RSTICK
			| ControllerFlags.SEPARATE_STICK
			| ControllerFlags.HAS_DPAD
			| ControllerFlags.NO_GRIPS )
	
	def __init__(self, daemon, device, config_file, config):
		try:
			self._parse_config(config)
		except Exception:
			log.error("Failed to parse config for evdev controller")
			raise
		Controller.__init__(self)
		self.device = device
		self.config_file = config_file
		self.config = config
		self.daemon = daemon
		self.poller = None
		if daemon:
			self.poller = daemon.get_poller()
			self.poller.register(self.device.fd, self.poller.POLLIN, self.input)
			self.device.grab()
			self._id = self._generate_id()
		self._state = EvdevControllerInput( *[0] * len(EvdevControllerInput._fields) )
		self._padpressemu_task = None
	
	
	def _parse_config(self, config):
		self._button_map = {}
		self._axis_map = {}
		self._dpad_map = {}
		self._calibrations = {}
		
		for x, value in config.get("buttons", {}).items():
			try:
				keycode = int(x)
				if value in TRIGGERS:
					self._axis_map[keycode] = value
				else:
					sc = getattr(SCButtons, value)
					self._button_map[keycode] = sc
			except: pass
		for x, value in config.get("axes", {}).items():
			code, axis = int(x), value.get("axis")
			if axis in EvdevControllerInput._fields:
				self._calibrations[code] = parse_axis(value)
				self._axis_map[code] = axis
		for x, value in config.get("dpads", {}).items():
			code, axis = int(x), value.get("axis")
			if axis in EvdevControllerInput._fields:
				self._calibrations[code] = parse_axis(value)
				self._dpad_map[code] = value.get("positive", False)
				self._axis_map[code] = axis
	
	
	def close(self):
		self.poller.unregister(self.device.fd)
		try:
			self.device.ungrab()
		except: pass
		self.device.close()
	
	
	def get_type(self):
		return "evdev"
	
	
	def get_id(self):
		return self._id
	
	
	def get_device_filename(self):
		return self.device.fn
	
	
	def get_device_name(self):
		return self.device.name	
	
	
	def _generate_id(self):
		"""
		ID is generated as 'ev' + upper_case(hex(crc32(device name + X)))
		where 'X' starts as 0 and increases as controllers with same name are
		connected.
		"""
		magic_number = 0
		id = None
		while id is None or id in self.daemon.get_active_ids():
			crc32 = binascii.crc32("%s%s" % (self.device.name, magic_number))
			id = "ev%s" % (hex(crc32).upper().strip("-0X"),)
			magic_number += 1
		return id
	
	
	def get_gui_config_file(self):
		return self.config_file
	
	
	def __repr__(self):
		return "<Evdev %s>" % (self.device.name.decode("utf-8"),)
	
	
	def input(self, *a):
		new_state = self._state
		need_cancel_padpressemu = False
		try:
			for event in self.device.read():
				if event.type == ecodes.EV_KEY and event.code in self._dpad_map:
					cal = self._calibrations[event.code]
					if event.value:
						if self._dpad_map[event.code]:
							# Positive
							value = STICK_PAD_MAX
						else:
							value = STICK_PAD_MIN
						cal = self._calibrations[event.code]
						value = int(value * cal.scale * STICK_PAD_MAX)
					else:
						value = 0
					axis = self._axis_map[event.code]
					if not new_state.buttons & SCButtons.LPADTOUCH and axis in ("lpad_x", "lpad_y"):
						b = new_state.buttons | SCButtons.LPAD | SCButtons.LPADTOUCH
						need_cancel_padpressemu = True
						new_state = new_state._replace(buttons=b, **{ axis : value })
					elif not new_state.buttons & SCButtons.RPADTOUCH and axis in ("rpad_x", "rpad_y"):
						b = new_state.buttons | SCButtons.RPADTOUCH
						need_cancel_padpressemu = True
						new_state = new_state._replace(buttons=b, **{ axis : value })
					else:
						new_state = new_state._replace(**{ axis : value })
				elif event.type == ecodes.EV_KEY and event.code in self._button_map:
					if event.value:
						b = new_state.buttons | self._button_map[event.code]
						new_state = new_state._replace(buttons=b)
					else:
						b = new_state.buttons & ~self._button_map[event.code]
						new_state = new_state._replace(buttons=b)
				elif event.type == ecodes.EV_KEY and event.code in self._axis_map:
					axis = self._axis_map[event.code]
					if event.value:
						new_state = new_state._replace(**{ axis : TRIGGER_MAX })
					else:
						new_state = new_state._replace(**{ axis : TRIGGER_MIN })
				elif event.type == ecodes.EV_ABS and event.code in self._axis_map:
					cal = self._calibrations[event.code]
					value = (float(event.value) * cal.scale) + cal.offset
					if value >= -cal.deadzone and value <= cal.deadzone:
						value = 0
					else:
						value = clamp(cal.clamp_min,
								int(value * cal.clamp_max), cal.clamp_max)
					axis = self._axis_map[event.code]
					if not new_state.buttons & SCButtons.LPADTOUCH and axis in ("lpad_x", "lpad_y"):
						b = new_state.buttons | SCButtons.LPAD | SCButtons.LPADTOUCH
						need_cancel_padpressemu = True
						new_state = new_state._replace(buttons=b, **{ axis : value })
					elif not new_state.buttons & SCButtons.RPADTOUCH and axis in ("rpad_x", "rpad_y"):
						b = new_state.buttons | SCButtons.RPADTOUCH
						need_cancel_padpressemu = True
						new_state = new_state._replace(buttons=b, **{ axis : value })
					else:
						new_state = new_state._replace(**{ axis : value })
		except IOError as e:
			# TODO: Maybe check e.errno to determine exact error
			# all of them are fatal for now
			log.error(e)
			_evdevdrv.device_removed(self.device.fn)
		
		if new_state is not self._state:
			# Something got changed
			old_state, self._state = self._state, new_state
			if self.mapper:
				if need_cancel_padpressemu:
					if self._padpressemu_task:
						self.mapper.cancel_task(self._padpressemu_task)
					self._padpressemu_task = self.mapper.schedule(
						self.PADPRESS_EMULATION_TIMEOUT,
						self.cancel_padpress_emulation
					)
				self.mapper.input(self, old_state, new_state)
	
	
	def test_input(self, event):
		if event.type == ecodes.EV_KEY:
			if event.code >= FIRST_BUTTON:
				if event.value:
					print("ButtonPress", event.code)
				else:
					print("ButtonRelease", event.code)
				sys.stdout.flush()
		elif event.type == ecodes.EV_ABS:
			print("Axis", event.code, event.value)
			sys.stdout.flush()
	
	
	def cancel_padpress_emulation(self, mapper):
		"""
		Since evdev gamepad typically can't generate LPADTOUCH nor RPADTOUCH
		buttons/events, pushing those buttons is emulated when apropriate stick
		is moved.
		
		Emulated *PADTOUCH button is held until stick is being moved and then
		for small time set by PADPRESS_EMULATION_TIMEOUT.
		Then, to release those purely virtual buttons, this method is called.
		"""
		 
		need_reschedule = False
		new_state = self._state
		if new_state.buttons & SCButtons.LPADTOUCH:
			if self._state.lpad_x == 0 and self._state.lpad_y == 0:
				b = new_state.buttons & ~(SCButtons.LPAD | SCButtons.LPADTOUCH)
				new_state = new_state._replace(buttons=b)
			else:
				need_reschedule = True

		if new_state.buttons & SCButtons.RPADTOUCH:
			if self._state.rpad_x == 0 and self._state.rpad_y == 0:
				b = new_state.buttons & ~SCButtons.RPADTOUCH
				new_state = new_state._replace(buttons=b)
			else:
				need_reschedule = True
		
		if new_state is not self._state:
			# Something got changed
			old_state, self._state = self._state, new_state
			if self.mapper:
				self.mapper.input(self, old_state, new_state)
		
		if need_reschedule:
			self._padpressemu_task = mapper.schedule(
				self.PADPRESS_EMULATION_TIMEOUT, self.cancel_padpress_emulation)
		else:
			self._padpressemu_task = None
	
	
	def apply_config(self, config):
		# TODO: This?
		pass
	
	
	def disconnected(self):
		# TODO: This!
		pass
	
	
	# def configure(self, idle_timeout=None, enable_gyros=None, led_level=None):
	
	
	def set_led_level(self, level):
		# TODO: This?
		pass
	
	
	def set_gyro_enabled(self, enabled):
		# TODO: This, maybe.
		pass
	
	
	def turnoff(self):
		"""
		Exists to stay compatibile with SCController class as evdev controller
		typically cannot be shut down like this.
		"""
		pass
	
	
	def get_gyro_enabled(self):
		""" Returns True if gyroscope input is currently enabled """
		return False
	
	
	def feedback(self, data):
		""" TODO: It would be nice to have feedback... """
		pass


def parse_axis(axis):
	min       = axis.get("min", -127)
	max       = axis.get("max",  128)
	center    = axis.get("center", 0)
	clamp_min = STICK_PAD_MIN
	clamp_max = STICK_PAD_MAX
	deadzone  = axis.get("deadzone", 0)
	offset = 0
	if (max >= 0 and min >= 0):
		offset = 1
	if max > min:
		scale = (-2.0 / (min-max)) if min != max else 1.0
		deadzone = abs(float(deadzone) * scale)
		offset *= -1.0
	else:
		scale = (-2.0 / (min-max)) if min != max else 1.0
		deadzone = abs(float(deadzone) * scale)
	if axis in TRIGGERS:
		clamp_min = TRIGGER_MIN
		clamp_max = TRIGGER_MAX
		offset += 1.0
		scale *= 0.5
	
	return AxisCalibrationData(scale, offset, center, clamp_min, clamp_max, deadzone)


class EvdevDriver(object):
	SCAN_INTERVAL = 5
	
	def __init__(self):
		self.daemon = None
		self._devices = {}
		self._scan_thread = None
		self._next_scan = None
	
	
	def start(self):
		self.daemon.get_device_monitor().add_callback("input", None, None,
				self.handle_new_device, self.handle_removed_device)
	
	
	def set_daemon(self, daemon):
		self.daemon = daemon
	
	
	@staticmethod
	def get_event_node(syspath):
		filename = syspath.split("/")[-1]
		if not filename.startswith("event"):
			return None
		return "/dev/input/%s" % (filename, )
	
	
	def handle_new_device(self, syspath, *bunchofnones):
		# There is no way to get anything usefull from /sys/.../input node,
		# but I'm interested about event devices here anyway
		eventnode = EvdevDriver.get_event_node(syspath)
		if eventnode is None: return False				# Not evdev
		if eventnode in self._devices: return False		# Already handled
		
		try:
			dev = evdev.InputDevice(eventnode)
			assert dev.fn == eventnode
			config_fn = "evdev-%s.json" % (dev.name.strip().replace("/", ""),)
			config_file = os.path.join(get_config_path(), "devices", config_fn)
		except OSError as ose:
			if ose.errno == 13:
				# Excepted error that happens often, don't report
				return False
			log.exception(ose)
			return False
		except Exception as e:
			log.exception(e)
			return False
		
		if os.path.exists(config_file):
			config = None
			try:
				config = json.loads(open(config_file, "r").read())
			except Exception as e:
				log.exception(e)
				return False
			try:
				controller = EvdevController(self.daemon, dev, config_file.decode("utf-8"), config)
			except Exception as e:
				log.debug("Failed to add evdev device: %s", e)
				log.exception(e)
				return False
			self._devices[eventnode] = controller
			self.daemon.add_controller(controller)
			log.debug("Evdev device added: %s", dev.name)
			return True
	
	
	def handle_removed_device(self, syspath, *bunchofnones):
		eventnode = EvdevDriver.get_event_node(syspath)
		self.device_removed(eventnode)
	
	
	def device_removed(self, eventnode):
		if eventnode in self._devices:
			controller = self._devices[eventnode]
			del self._devices[eventnode]
			self.daemon.remove_controller(controller)
			controller.close()	
	
	
	def handle_callback(self, callback, devices):
		try:
			controller = callback(devices)
		except Exception as e:
			log.debug("Failed to add evdev device: %s", e)
			log.exception(e)
			return
		if controller is not None:
			self._devices[controller.get_device_filename()] = controller
			self.daemon.add_controller(controller)
			log.debug("Evdev device added: %s", controller.get_device_name())
	
	
	def make_new_device(self, factory, evdevdevice, *userdata):
		"""
		Similar to handle_new_device, but meant for use by other drivers.
		See global make_new_device method for more info
		"""
		try:
			controller = factory(self.daemon, evdevdevice, *userdata)
		except IOError as e:
			print("Failed to open device:", str(e), file=sys.stderr)
			return None
		if controller:
			self._devices[evdevdevice.fn] = controller
			self.daemon.add_controller(controller)
			log.debug("Evdev device added: %s", controller.get_device_name())
		return controller


if HAVE_EVDEV:
	# Just like USB driver, EvdevDriver is process-wide singleton
	_evdevdrv = EvdevDriver()
	
	
	def start(daemon):
		_evdevdrv.start()
	
	
def init(daemon, config):
	if not HAVE_EVDEV:
		log.warning("Failed to enable Evdev driver: 'python-evdev' package is missing.")
		return False
	
	_evdevdrv.set_daemon(daemon)
	return True


def make_new_device(factory, evdevdevice, *userdata):
	"""
	Creates and registers device using given evdev device and given factory method.
	Factory is called as factory(daemon, device, *userdata) and if it returns device,
	this device is added into watch list, so it can be closed automatically.
	
	Returns whatever Factory returned.
	"""
	assert HAVE_EVDEV, "evdev driver is not available"
	return _evdevdrv.make_new_device(factory, evdevdevice, *userdata)


def get_evdev_devices_from_syspath(syspath):
	"""
	For given syspath, returns all assotiated event devices.
	"""
	assert HAVE_EVDEV, "evdev driver is not available"
	rv = []
	for name in os.listdir(syspath):
		path = os.path.join(syspath, name)
		if name.startswith("event"):
			eventnode = EvdevDriver.get_event_node(path)
			if eventnode is not None:
				try:
					dev = evdev.InputDevice(eventnode)
					assert dev.fn == eventnode
					rv.append(dev)
				except Exception as e:
					log.exception(e)
					continue
		else:
			if os.path.isdir(path) and not os.path.islink(path):
				rv += get_evdev_devices_from_syspath(path)
	return rv


def get_axes(dev):
	""" Helper function to get list ofa available axes """
	assert HAVE_EVDEV, "evdev driver is not available"
	caps = dev.capabilities(verbose=False)
	return [ axis for (axis, trash) in caps.get(ecodes.EV_ABS, []) ]


def evdevdrv_test(args):
	"""
	Small input test used by GUI while setting up the device.
	Output and usage matches one from hiddrv.
	"""
	from scc.scripts import InvalidArguments
	
	try:
		path = args[0]
		dev = evdev.InputDevice(path)
	except IndexError:
		raise InvalidArguments()
	except Exception as e:
		print("Failed to open device:", str(e), file=sys.stderr)
		return 2
	
	c = EvdevController(None, dev, None, {})
	caps = dev.capabilities(verbose=False)
	print("Buttons:", " ".join([ str(x)
			for x in caps.get(ecodes.EV_KEY, [])]))
	print("Axes:", " ".join([ str(axis)
			for (axis, trash) in caps.get(ecodes.EV_ABS, []) ]))
	print("Ready")
	sys.stdout.flush()
	for event in dev.read_loop():
		c.test_input(event)
	return 0


if __name__ == "__main__":
	""" Called when executed as script """
	from scc.tools import init_logging, set_logging_level
	init_logging()
	set_logging_level(True, True)
	sys.exit(evdevdrv_test(sys.argv[1:]))

