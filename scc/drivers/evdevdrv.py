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
from scc.config import Config
from scc.poller import Poller
from scc.tools import clamp

from collections import namedtuple
import evdev
import struct, threading, Queue, os, time, binascii, json, logging
log = logging.getLogger("evdev")

TRIGGERS = "ltrig", "rtrig"

EvdevControllerInput = namedtuple('EvdevControllerInput',
	'buttons ltrig rtrig stick_x stick_y lpad_x lpad_y rpad_x rpad_y'
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
	
	def __init__(self, daemon, device, config):
		try:
			self._parse_config(config)
		except Exception, e:
			log.error("Failed to parse config for evdev device")
			raise
		Controller.__init__(self)
		self.flags = ControllerFlags.HAS_RSTICK | ControllerFlags.SEPARATE_STICK
		self.device = device
		self.config = config
		self.poller = daemon.get_poller()
		self.poller.register(self.device.fd, self.poller.POLLIN, self.input)
		self.device.grab()
		self._id = self._generate_id()
		self._state = EvdevControllerInput( *[0] * len(EvdevControllerInput._fields) )
		self._padpressemu_task = None
	
	def _parse_config(self, config):
		self._evdev_to_button = {}
		self._evdev_to_axis = {}
		self._evdev_to_dpad = {}
		self._calibrations = {}
		
		def _parse_axis(axis):
			min       = value.get("min", -127)
			max       = value.get("max",  128)
			center    = value.get("center", 0)
			clamp_min = STICK_PAD_MIN
			clamp_max = STICK_PAD_MAX
			deadzone  = value.get("deadzone", 0)
			if max > min:
				scale = (-2.0 / (min-max)) if min != max else 1.0
				deadzone = abs(float(deadzone) * scale)
				offset = -1.0
			else:
				scale = (-2.0 / (min-max)) if min != max else 1.0
				deadzone = abs(float(deadzone) * scale)
				offset = 1.0
			if axis in TRIGGERS:
				clamp_min = TRIGGER_MIN
				clamp_max = TRIGGER_MAX
				offset += 1.0
				scale *= 0.5
			
			return AxisCalibrationData(scale, offset, center, clamp_min, clamp_max, deadzone)
		
		for x, value in config.get("buttons", {}).iteritems():
			try:
				keycode = int(x)
				if value in TRIGGERS:
					self._evdev_to_axis[keycode] = value
				else:
					sc = getattr(SCButtons, value)
					self._evdev_to_button[keycode] = sc
			except: pass
		for x, value in config.get("axes", {}).iteritems():
			code, axis = int(x), value.get("axis")
			if axis in EvdevControllerInput._fields:
				self._calibrations[code] = _parse_axis(axis)
				self._evdev_to_axis[code] = axis
		for x, value in config.get("dpads", {}).iteritems():
			code, axis = int(x), value.get("axis")
			if axis in EvdevControllerInput._fields:
				self._calibrations[code] = _parse_axis(axis)
				self._evdev_to_dpad[code] = value.get("positive", False)
				self._evdev_to_axis[code] = axis
	
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
	
	
	def _generate_id(self):
		"""
		ID is generated as 'ev' + upper_case(hex(crc32(device name + X)))
		where 'X' starts as 0 and increases as controllers with same name are
		connected.
		"""
		magic_number = 0
		id = None
		while id is None or id in _evdevdrv._used_ids:
			crc32 = binascii.crc32("%s%s" % (self.device.name, magic_number))
			id = "ev%s" % (hex(crc32).upper().strip("-0X"),)
			magic_number += 1
		_evdevdrv._used_ids.add(id)
		return id
	
	
	def get_id_is_persistent(self):
		return True
	
	
	def __repr__(self):
		return "<Evdev %s>" % (self.device.name,)
	
	
	def input(self, *a):
		new_state = self._state
		need_cancel_padpressemu = False
		try:
			for event in self.device.read():
				if event.type == evdev.ecodes.EV_KEY and event.code in self._evdev_to_dpad:
					cal = self._calibrations[event.code]
					if event.value:
						if self._evdev_to_dpad[event.code]:
							# Positive
							value = STICK_PAD_MAX
						else:
							value = STICK_PAD_MIN
						cal = self._calibrations[event.code]
						value = value * cal.scale * STICK_PAD_MAX
					else:
						value = 0
					axis = self._evdev_to_axis[event.code]
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
				elif event.type == evdev.ecodes.EV_KEY and event.code in self._evdev_to_button:
					if event.value:
						b = new_state.buttons | self._evdev_to_button[event.code]
						new_state = new_state._replace(buttons=b)
					else:
						b = new_state.buttons & ~self._evdev_to_button[event.code]
						new_state = new_state._replace(buttons=b)
				elif event.type == evdev.ecodes.EV_KEY and event.code in self._evdev_to_axis:
					axis = self._evdev_to_axis[event.code]
					if event.value:
						new_state = new_state._replace(**{ axis : TRIGGER_MAX })
					else:
						new_state = new_state._replace(**{ axis : TRIGGER_MIN })
				elif event.type == evdev.ecodes.EV_ABS and event.code in self._evdev_to_axis:
					cal = self._calibrations[event.code]
					value = (float(event.value) * cal.scale) + cal.offset
					if value >= -cal.deadzone and value <= cal.deadzone:
						value = 0
					else:
						value = clamp(cal.clamp_min,
								int(value * cal.clamp_max), cal.clamp_max)
					axis = self._evdev_to_axis[event.code]
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
		except IOError, e:
			# TODO: Maybe check e.errno to determine exact error
			# all of them are fatal for now
			log.error(e)
			_evdevdrv.device_removed(self.device)
		
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


class EvdevDriver(object):
	SCAN_INTERVAL = 5
	
	def __init__(self):
		self._daemon = None
		self._devices = {}
		self._new_devices = Queue.Queue()
		self._lock = threading.Lock()
		self._scan_thread = None
		self._used_ids = set()
		self._next_scan = None
	
	
	def handle_new_device(self, dev, config):
		try:
			controller = EvdevController(self._daemon, dev, config)
		except Exception, e:
			log.debug("Failed to add evdev device: %s", e)
			log.exception(e)
			return
		self._devices[dev.fn] = controller
		self._daemon.add_controller(controller)
		log.debug("Evdev device added: %s", dev.name)
	
	
	def device_removed(self, dev):
		if dev.fn in self._devices:
			controller = self._devices[dev.fn]
			del self._devices[dev.fn]
			self._daemon.remove_controller(controller)
			self._used_ids.remove(controller.get_id())
			controller.close()
	
	
	def scan(self):
		# Scanning is slow, so it runs in thread
		with self._lock:
			if self._scan_thread is None:
				self._scan_thread = threading.Thread(
						target = self._scan_thread_target)
				self._scan_thread.start()
	
	
	def _scan_thread_target(self):
		c = Config()
		for fname in evdev.list_devices():
			dev = evdev.InputDevice(fname)
			if dev.fn not in self._devices:
				config_file = os.path.join(get_config_path(), "devices",
					"%s.json" % (dev.name.strip(),))
				if os.path.exists(config_file):
					config = None
					try:
						config = json.loads(open(config_file, "r").read())
						with self._lock:
							self._new_devices.put(( dev, config ))
					except Exception, e:
						log.exception(e)
		with self._lock:
			self._scan_thread = None
			self._next_scan = time.time() + EvdevDriver.SCAN_INTERVAL
	
	
	def start(self):
		self.scan()
	
	
	def mainloop(self):
		if time.time() > self._next_scan:
			self.scan()
		with self._lock:
			while not self._new_devices.empty():
				dev, config = self._new_devices.get()
				if dev.fn not in self._devices:
					self.handle_new_device(dev, config)

# Just like USB driver, EvdevDriver is process-wide singleton
_evdevdrv = EvdevDriver()

def init(daemon):
	_evdevdrv._daemon = daemon
	daemon.add_mainloop(_evdevdrv.mainloop)
	# daemon.on_daemon_exit(_evdevdrv.on_exit)

def start(daemon):
	_evdevdrv.start()
