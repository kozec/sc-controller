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
from scc.tools import clamp

HAVE_INOTIFY = False
try:
	import pyinotify
	HAVE_INOTIFY = True
except ImportError:
	pass

HAVE_EVDEV = False
try:
	# Driver disables itself if evdev is not available
	import evdev
	HAVE_EVDEV = True
except ImportError:
	pass

from collections import namedtuple
import threading, Queue, os, sys, time, binascii, json, logging
log = logging.getLogger("evdev")

TRIGGERS = "ltrig", "rtrig"
FIRST_BUTTON = 288

EvdevControllerInput = namedtuple('EvdevControllerInput',
	'buttons ltrig rtrig stick_x stick_y lpad_x lpad_y rpad_x rpad_y cpad_x cpad_y'
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
	ECODES = evdev.ecodes
	
	def __init__(self, daemon, device, config_file, config):
		try:
			self._parse_config(config)
		except Exception:
			log.error("Failed to parse config for evdev controller")
			raise
		Controller.__init__(self)
		self.flags = ControllerFlags.HAS_RSTICK | ControllerFlags.SEPARATE_STICK
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
		
		for x, value in config.get("buttons", {}).iteritems():
			try:
				keycode = int(x)
				if value in TRIGGERS:
					self._axis_map[keycode] = value
				else:
					sc = getattr(SCButtons, value)
					self._button_map[keycode] = sc
			except: pass
		for x, value in config.get("axes", {}).iteritems():
			code, axis = int(x), value.get("axis")
			if axis in EvdevControllerInput._fields:
				self._calibrations[code] = parse_axis(value)
				self._axis_map[code] = axis
		for x, value in config.get("dpads", {}).iteritems():
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
		return "<Evdev %s>" % (self.device.name,)
	
	
	def input(self, *a):
		new_state = self._state
		need_cancel_padpressemu = False
		try:
			for event in self.device.read():
				if event.type == evdev.ecodes.EV_KEY and event.code in self._dpad_map:
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
				elif event.type == evdev.ecodes.EV_KEY and event.code in self._button_map:
					if event.value:
						b = new_state.buttons | self._button_map[event.code]
						new_state = new_state._replace(buttons=b)
					else:
						b = new_state.buttons & ~self._button_map[event.code]
						new_state = new_state._replace(buttons=b)
				elif event.type == evdev.ecodes.EV_KEY and event.code in self._axis_map:
					axis = self._axis_map[event.code]
					if event.value:
						new_state = new_state._replace(**{ axis : TRIGGER_MAX })
					else:
						new_state = new_state._replace(**{ axis : TRIGGER_MIN })
				elif event.type == evdev.ecodes.EV_ABS and event.code in self._axis_map:
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
	
	
	def test_input(self, event):
		if event.type == evdev.ecodes.EV_KEY:
			if event.code >= FIRST_BUTTON:
				if event.value:
					print "ButtonPress", event.code
				else:
					print "ButtonRelease", event.code
				sys.stdout.flush()
		elif event.type == evdev.ecodes.EV_ABS:
			print "Axis", event.code, event.value
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
		self._new_devices = Queue.Queue()
		self._lock = threading.Lock()
		self._scan_thread = None
		self._next_scan = None
	
	
	def set_daemon(self, daemon):
		self.daemon = daemon
	
	
	def handle_new_device(self, dev, config_path, config):
		try:
			controller = EvdevController(self.daemon, dev, config_path, config)
		except Exception, e:
			log.debug("Failed to add evdev device: %s", e)
			log.exception(e)
			return
		self._devices[dev.fn] = controller
		self.daemon.add_controller(controller)
		log.debug("Evdev device added: %s", dev.name)
	
	
	def make_new_device(self, vendor_id, product_id, factory, repeat=0):
		"""
		Similar to handle_new_device, but meant for use by other drivers.
		See global make_new_device method for more info
		"""
		devices = []
		for fname in evdev.list_devices():
			try:
				dev = evdev.InputDevice(fname)
			except Exception:
				continue
			if dev.fn not in self._devices:
				if vendor_id == dev.info.vendor and product_id == dev.info.product:
					devices.append(dev)
		if len(devices) == 0 and repeat < 2:
			# Sometimes evdev is slow; Give it another try
			self.daemon.get_scheduler().schedule(1, self.make_new_device, vendor_id, product_id, factory, repeat + 1)
			return
		
		controller = factory(self.daemon, devices)
		if controller:
			self._devices[controller.device.fn] = controller
			self.daemon.add_controller(controller)
			log.debug("Evdev device added: %s", controller.device.name)
	
	
	def device_removed(self, dev):
		if dev.fn in self._devices:
			controller = self._devices[dev.fn]
			del self._devices[dev.fn]
			self.daemon.remove_controller(controller)
			controller.close()
	
	
	def scan(self):
		# Scanning is slow, so it runs in thread
		with self._lock:
			if self._scan_thread is None:
				self._scan_thread = threading.Thread(
						target = self._scan_thread_target)
				if HAVE_INOTIFY:
					log.debug("Rescan started")
				self._scan_thread.start()
	
	
	def _scan_thread_target(self):
		for fname in evdev.list_devices():
			try:
				dev = evdev.InputDevice(fname)
			except Exception:
				continue
			if dev.fn not in self._devices:
				config_file = os.path.join(get_config_path(), "devices",
					"evdev-%s.json" % (dev.name.strip(),))
				if os.path.exists(config_file):
					config = None
					try:
						config = json.loads(open(config_file, "r").read())
						with self._lock:
							self._new_devices.put(( dev, config_file, config ))
					except Exception, e:
						log.exception(e)
		with self._lock:
			self._scan_thread = None
			self._next_scan = time.time() + EvdevDriver.SCAN_INTERVAL
			if HAVE_INOTIFY and not self._new_devices.empty():
				self.daemon.get_scheduler().schedule(0, self.add_new_devices)
	
	
	def add_new_devices(self):
		with self._lock:
			while not self._new_devices.empty():
				dev, config_file, config = self._new_devices.get()
				if dev.fn not in self._devices:
					self.handle_new_device(dev, config_file, config)
	
	
	def start(self):
		self.scan()
	
	
	def _inotify_cb(self, *a):
		self._notifier.read_events()
		self._notifier.process_events() 
		# I don't really care about events above,
		# just scheduling rescan is enough here.
		self.daemon.get_scheduler().schedule(1, self.scan)
	
	
	def enable_inotify(self):
		self._wm = pyinotify.WatchManager()
		self._notifier = pyinotify.Notifier(self._wm, lambda *a, **b: False)
		self._wm.add_watch('/dev/input', pyinotify.IN_CREATE, False)
		self.daemon.get_poller().register(self._notifier._fd,
				self.daemon.get_poller().POLLIN, self._inotify_cb)
	
	
	def dumb_mainloop(self):
		if time.time() > self._next_scan:
			self.scan()
		if not self._new_devices.empty():
			self.add_new_devices()

if HAVE_EVDEV:
	# Just like USB driver, EvdevDriver is process-wide singleton
	_evdevdrv = EvdevDriver()
	
	
	def start(daemon):
		_evdevdrv.start()
	
	
def init(daemon, config):
	if not HAVE_EVDEV:
		log.warning("'evdev' package is missing. Evdev support is disabled.")
		return False
	
	_evdevdrv.set_daemon(daemon)
	if HAVE_INOTIFY:
		_evdevdrv.enable_inotify()
		daemon.on_rescan(_evdevdrv.scan)
	else:
		log.warning("Failed to import pyinotify. Evdev driver will scan for new devices every 5 seconds.")
		log.warning("Consider installing python-pyinotify package.")
		daemon.add_mainloop(_evdevdrv.dumb_mainloop)
	return True


def make_new_device(vendor_id, product_id, factory):
	"""
	Searchs for device with given USB vendor and product_id and if it's
	found, calls given factory method to create new EvdevController instance.
	Everything after is handled as if instance was created by evdev driver.
	
	Does scan on main thread, so it may cause small lag.
	
	Factory is called as factory(daemon, devices), where devices is list of
	matching devices. Factory should return None or EvdevController instance.
	
	Returns created instance or None if no matching device was found.
	"""
	assert HAVE_EVDEV, "evdev driver is not available"
	return _evdevdrv.make_new_device(vendor_id, product_id, factory)


def get_axes(dev):
	""" Helper function to get list ofa available axes """
	assert HAVE_EVDEV, "evdev driver is not available"
	caps = dev.capabilities(verbose=False)
	return [ axis for (axis, trash) in caps.get(evdev.ecodes.EV_ABS, []) ]

def evdevdrv_test(args):
	"""
	Small input test used by GUI while setting up the device.
	Output and usage matches one from hiddrv.
	"""
	from scc.poller import Poller
	from scc.scripts import InvalidArguments
	from scc.tools import init_logging, set_logging_level
	
	try:
		path = args[0]
		dev = evdev.InputDevice(path)
	except IndexError:
		raise InvalidArguments()
	except Exception, e:
		print >>sys.stderr, "Failed to open device:", str(e)
		return 2
	
	c = EvdevController(None, dev, None, {})
	caps = dev.capabilities(verbose=False)
	print "Buttons:", " ".join([ str(x)
			for x in caps.get(evdev.ecodes.EV_KEY, [])])
	print "Axes:", " ".join([ str(axis)
			for (axis, trash) in caps.get(evdev.ecodes.EV_ABS, []) ])
	print "Ready"
	sys.stdout.flush()
	for event in dev.read_loop():
		c.test_input(event)
	return 0


if __name__ == "__main__":
	""" Called when executed as script """
	from scc.tools import init_logging, set_logging_level
	init_logging()
	set_logging_level(True, True)
	sys.exit(evdevdrv_test(sys.argv[0], sys.argv[1:]))
