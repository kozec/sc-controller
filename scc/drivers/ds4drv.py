#!/usr/bin/env python2
"""
SC Controller - Dualshock 4 Driver

Extends HID driver with DS4-specific options.
"""

from scc.drivers.hiddrv import BUTTON_COUNT, ButtonData, AxisType, AxisData
from scc.drivers.hiddrv import HIDController, HIDDecoder, hiddrv_test
from scc.drivers.hiddrv import AxisMode, AxisDataUnion, AxisModeData
from scc.drivers.hiddrv import HatswitchModeData, _lib
from scc.drivers.evdevdrv import HAVE_EVDEV, EvdevController, get_axes
from scc.drivers.evdevdrv import get_evdev_devices_from_syspath
from scc.drivers.evdevdrv import make_new_device
from scc.drivers.usb import register_hotplug_device
from scc.constants import SCButtons, ControllerFlags
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX
from scc.tools import init_logging, set_logging_level
import sys, logging, ctypes
log = logging.getLogger("DS4")

VENDOR_ID = 0x054c
PRODUCT_ID = 0x09cc


class DS4Controller(HIDController):
	# Most of axes are the same
	BUTTON_MAP = (
		SCButtons.X,
		SCButtons.A,
		SCButtons.B,
		SCButtons.Y,
		SCButtons.LB,
		SCButtons.RB,
		1 << 64,
		1 << 64,
		SCButtons.BACK,
		SCButtons.START,
		SCButtons.STICKPRESS,
		SCButtons.RPAD,
		SCButtons.C,
		SCButtons.CPADPRESS,
	)
	
	flags = ( ControllerFlags.EUREL_GYROS
			| ControllerFlags.HAS_RSTICK
			| ControllerFlags.HAS_CPAD
			| ControllerFlags.HAS_DPAD
			| ControllerFlags.SEPARATE_STICK
			| ControllerFlags.NO_GRIPS
	)
	
	
	def _load_hid_descriptor(self, config, max_size, vid, pid, test_mode):
		# Overrided and hardcoded
		self._decoder = HIDDecoder()
		self._decoder.axes[AxisType.AXIS_LPAD_X] = AxisData(
			mode = AxisMode.HATSWITCH, byte_offset = 5, size = 8,
			data = AxisDataUnion(hatswitch = HatswitchModeData(
				button = SCButtons.LPAD | SCButtons.LPADTOUCH,
				min = STICK_PAD_MIN, max = STICK_PAD_MAX
		)))
		self._decoder.axes[AxisType.AXIS_STICK_X] = AxisData(
			mode = AxisMode.AXIS, byte_offset = 1, size = 8,
			data = AxisDataUnion(axis = AxisModeData(
				scale = 1.0, offset = -127.5, clamp_max = 257, deadzone = 10
		)))
		self._decoder.axes[AxisType.AXIS_STICK_Y] = AxisData(
			mode = AxisMode.AXIS, byte_offset = 2, size = 8,
			data = AxisDataUnion(axis = AxisModeData(
				scale = -1.0, offset = 127.5, clamp_max = 257, deadzone = 10
		)))
		self._decoder.axes[AxisType.AXIS_RPAD_X] = AxisData(
			mode = AxisMode.AXIS, byte_offset = 3, size = 8,
			data = AxisDataUnion(axis = AxisModeData(
				button = SCButtons.RPADTOUCH,
				scale = 1.0, offset = -127.5, clamp_max = 257, deadzone = 10
		)))
		self._decoder.axes[AxisType.AXIS_RPAD_Y] = AxisData(
			mode = AxisMode.AXIS, byte_offset = 4, size = 8,
			data = AxisDataUnion(axis = AxisModeData(
				button = SCButtons.RPADTOUCH,
				scale = -1.0, offset = 127.5, clamp_max = 257, deadzone = 10
		)))
		self._decoder.axes[AxisType.AXIS_LTRIG] = AxisData(
			mode = AxisMode.AXIS, byte_offset = 8, size = 8,
			data = AxisDataUnion(axis = AxisModeData(
				scale = 1.0, clamp_max = 1, deadzone = 10
		)))
		self._decoder.axes[AxisType.AXIS_RTRIG] = AxisData(
			mode = AxisMode.AXIS, byte_offset = 9, size = 8,
			data = AxisDataUnion(axis = AxisModeData(
				scale = 1.0, clamp_max = 1, deadzone = 10
		)))
		self._decoder.axes[AxisType.AXIS_GPITCH] = AxisData(
			mode = AxisMode.DS4ACCEL, byte_offset = 13)
		self._decoder.axes[AxisType.AXIS_GROLL] = AxisData(
			mode = AxisMode.DS4ACCEL, byte_offset = 17)
		self._decoder.axes[AxisType.AXIS_GYAW] = AxisData(
			mode = AxisMode.DS4ACCEL, byte_offset = 15)
		self._decoder.axes[AxisType.AXIS_Q1] = AxisData(
			mode = AxisMode.DS4GYRO, byte_offset = 23)
		self._decoder.axes[AxisType.AXIS_Q2] = AxisData(
			mode = AxisMode.DS4GYRO, byte_offset = 19)
		self._decoder.axes[AxisType.AXIS_Q3] = AxisData(
			mode = AxisMode.DS4GYRO, byte_offset = 21)
		
		self._decoder.axes[AxisType.AXIS_CPAD_X] = AxisData(
			mode = AxisMode.DS4TOUCHPAD, byte_offset = 36)
		self._decoder.axes[AxisType.AXIS_CPAD_Y] = AxisData(
			mode = AxisMode.DS4TOUCHPAD, byte_offset = 37, bit_offset=4)
		self._decoder.buttons = ButtonData(
			enabled = True, byte_offset=5, bit_offset=4, size=14,
			button_count = 14
		)
		
		if test_mode:
			for x in range(BUTTON_COUNT):
				self._decoder.buttons.button_map[x] = x
		else:
			for x in range(BUTTON_COUNT):
				self._decoder.buttons.button_map[x] = 64
			for x, sc in enumerate(DS4Controller.BUTTON_MAP):
				self._decoder.buttons.button_map[x] = self.button_to_bit(sc)
		
		self._packet_size = 64
	
	
	def input(self, endpoint, data):
		# Special override for CPAD touch button
		if _lib.decode(ctypes.byref(self._decoder), data):
			if self.mapper:
				if ord(data[35]) >> 7:
					# cpad is not touched
					self._decoder.state.buttons &= ~SCButtons.CPADTOUCH
				else:
					self._decoder.state.buttons |= SCButtons.CPADTOUCH
				self.mapper.input(self,
						self._decoder.old_state, self._decoder.state)

	
	def get_gyro_enabled(self):
		# Cannot be actually turned off, so it's always active
		# TODO: Maybe emulate turning off?
		return True
	
	
	def get_type(self):
		return "ds4"
	
	
	def get_gui_config_file(self):
		return "ds4-config.json"
	
	
	def __repr__(self):
		return "<DS4Controller %s>" % (self.get_id(), )
	
	
	def _generate_id(self):
		"""
		ID is generated as 'ds4' or 'ds4:X' where 'X' starts as 1 and increases
		as controllers with same ids are connected.
		"""
		magic_number = 1
		id = "ds4"
		while id in self.daemon.get_active_ids():
			id = "ds4:%s" % (magic_number, )
			magic_number += 1
		return id


class DS4EvdevController(EvdevController):
	TOUCH_FACTOR_X = STICK_PAD_MAX / 940.0
	TOUCH_FACTOR_Y = STICK_PAD_MAX / 470.0
	BUTTON_MAP = {
		304: "A",
		305: "B",
		307: "Y",
		308: "X",
		310: "LB",
		311: "RB",
		314: "BACK",
		315: "START",
		316: "C",
		317: "STICKPRESS",
		318: "RPAD"
		# 319: "CPAD",
	}
	AXIS_MAP = {
		0:  { "axis": "stick_x", "deadzone": 4, "max": 255, "min": 0 },
		1:  { "axis": "stick_y", "deadzone": 4, "max": 0, "min": 255 },
		3:  { "axis": "rpad_x", "deadzone": 4, "max": 255, "min": 0 },
		4:  { "axis": "rpad_y", "deadzone": 8, "max": 0, "min": 255 },
		2:  { "axis": "ltrig", "max": 255, "min": 0 },
		5:  { "axis": "rtrig", "max": 255, "min": 0 },
		16: { "axis": "lpad_x", "deadzone": 0, "max": 1, "min": -1 },
		17: { "axis": "lpad_y", "deadzone": 0, "max": -1, "min": 1 }
	}
	BUTTON_MAP_OLD = {
		304: "X",
		305: "A",
		306: "B",
		307: "Y",
		308: "LB",
		309: "RB",
		312: "BACK",
		313: "START",
		314: "STICKPRESS",
		315: "RPAD",
		316: "C",
		# 317: "CPAD",
	}
	AXIS_MAP_OLD = {
		0:  { "axis": "stick_x", "deadzone": 4, "max": 255, "min": 0 },
		1:  { "axis": "stick_y", "deadzone": 4, "max": 0, "min": 255 },
		2:  { "axis": "rpad_x", "deadzone": 4, "max": 255, "min": 0 },
		5:  { "axis": "rpad_y", "deadzone": 8, "max": 0, "min": 255 },
		3:  { "axis": "ltrig", "max": 32767, "min": -32767 },
		4:  { "axis": "rtrig", "max": 32767, "min": -32767 },
		16: { "axis": "lpad_x", "deadzone": 0, "max": 1, "min": -1 },
		17: { "axis": "lpad_y", "deadzone": 0, "max": -1, "min": 1 }
	}
	GYRO_MAP = {
		EvdevController.ECODES.ABS_RX : ('gpitch', 0.01),
		EvdevController.ECODES.ABS_RY : ('gyaw', 0.01),
		EvdevController.ECODES.ABS_RZ : ('groll', 0.01),
		EvdevController.ECODES.ABS_X : (None, 1),		# 'q2'
		EvdevController.ECODES.ABS_Y : (None, 1),		# 'q3'
		EvdevController.ECODES.ABS_Z : (None, -1),		# 'q1'
	}
	flags = ( ControllerFlags.EUREL_GYROS
			| ControllerFlags.HAS_RSTICK
			| ControllerFlags.HAS_CPAD
			| ControllerFlags.HAS_DPAD
			| ControllerFlags.SEPARATE_STICK
			| ControllerFlags.NO_GRIPS
	)
	
	def __init__(self, daemon, controllerdevice, gyro, touchpad):
		config = {
			'axes' : DS4EvdevController.AXIS_MAP,
			'buttons' : DS4EvdevController.BUTTON_MAP,
			'dpads' : {}
		}
		if controllerdevice.info.version & 0x8000 == 0:
			# Older kernel uses different mappings
			# see kernel source, drivers/hid/hid-sony.c#L2748
			config['axes'] = DS4EvdevController.AXIS_MAP_OLD
			config['buttons'] = DS4EvdevController.BUTTON_MAP_OLD
		self._gyro = gyro
		self._touchpad = touchpad
		for device in (self._gyro, self._touchpad):
			if device:
				device.grab()
		EvdevController.__init__(self, daemon, controllerdevice, None, config)
		if self.poller:
			self.poller.register(touchpad.fd, self.poller.POLLIN, self._touchpad_input)
			self.poller.register(gyro.fd, self.poller.POLLIN, self._gyro_input)
	
	
	def _gyro_input(self, *a):
		new_state = self._state
		try:
			for event in self._gyro.read():
				if event.type == self.ECODES.EV_ABS:
					axis, factor = DS4EvdevController.GYRO_MAP[event.code]
					if axis:
						new_state = new_state._replace(
								**{ axis : int(event.value * factor) })
		except IOError:
			# Errors here are not even reported, evdev class handles important ones
			return
		
		if new_state is not self._state:
			old_state, self._state = self._state, new_state
			if self.mapper:
				self.mapper.input(self, old_state, new_state)
	
	
	def _touchpad_input(self, *a):
		new_state = self._state
		try:
			for event in self._touchpad.read():
				if event.type == self.ECODES.EV_ABS:
					if event.code == self.ECODES.ABS_MT_POSITION_X:
						value = event.value * DS4EvdevController.TOUCH_FACTOR_X
						value = STICK_PAD_MIN + int(value)
						new_state = new_state._replace(cpad_x = value)
					elif event.code == self.ECODES.ABS_MT_POSITION_Y:
						value = event.value * DS4EvdevController.TOUCH_FACTOR_Y
						value = STICK_PAD_MAX - int(value)
						new_state = new_state._replace(cpad_y = value)
				elif event.type == 0:
					pass
				elif event.code == self.ECODES.BTN_LEFT:
					if event.value == 1:
						b = new_state.buttons | SCButtons.CPADPRESS
						new_state = new_state._replace(buttons = b)
					else:
						b = new_state.buttons & ~SCButtons.CPADPRESS
						new_state = new_state._replace(buttons = b)
				elif event.code == self.ECODES.BTN_TOUCH:
					if event.value == 1:
						b = new_state.buttons | SCButtons.CPADTOUCH
						new_state = new_state._replace(buttons = b)
					else:
						b = new_state.buttons & ~SCButtons.CPADTOUCH
						new_state = new_state._replace(buttons = b,
								cpad_x = 0, cpad_y = 0)
		except IOError:
			# Errors here are not even reported, evdev class handles important ones
			return
		
		if new_state is not self._state:
			old_state, self._state = self._state, new_state
			if self.mapper:
				self.mapper.input(self, old_state, new_state)
	
	
	def close(self):
		EvdevController.close(self)
		for device in (self._gyro, self._touchpad):
			try:
				self.poller.unregister(device.fd)
				device.ungrab()
			except: pass
	
	
	def get_gyro_enabled(self):
		# Cannot be actually turned off, so it's always active
		# TODO: Maybe emulate turning off?
		return True
	
	
	def get_type(self):
		return "ds4evdev"
	
	
	def get_gui_config_file(self):
		return "ds4-config.json"
	
	
	def __repr__(self):
		return "<DS4EvdevController %s>" % (self.get_id(), )
	
	
	def _generate_id(self):
		"""
		ID is generated as 'ds4' or 'ds4:X' where 'X' starts as 1 and increases
		as controllers with same ids are connected.
		"""
		magic_number = 1
		id = "ds4"
		while id in self.daemon.get_active_ids():
			id = "ds4:%s" % (magic_number, )
			magic_number += 1
		return id


def init(daemon, config):
	""" Registers hotplug callback for ds4 device """
		
	def hid_callback(device, handle):
		return DS4Controller(device, daemon, handle, None, None)
	
	def make_evdev_device(syspath, *whatever):
		devices = get_evdev_devices_from_syspath(syspath)
		# With kernel 4.10 or later, PS4 controller pretends to be 3 different devices.
		# 1st, determining which one is actual controller is needed
		controllerdevice = None
		for device in devices:
			count = len(get_axes(device))
			if count == 8:
				# 8 axes - Controller
				controllerdevice = device
		if not controllerdevice:
			log.warning("Failed to determine controller device")
			return None
		# 2nd, find motion sensor and touchpad with physical address matching controllerdevice
		gyro, touchpad = None, None
		phys = device.phys.split("/")[0]
		for device in devices:
			if device.phys.startswith(phys):
				axes = get_axes(device)
				count = len(axes)
				if count == 6:
					# 6 axes
					if EvdevController.ECODES.ABS_MT_POSITION_X in axes:
						# kernel 4.17+ - touchpad
						touchpad = device
					else:
						# gyro sensor
						gyro = device
					pass
				elif count == 4:
					# 4 axes - Touchpad
					touchpad = device
		# 3rd, do a magic
		if controllerdevice and gyro and touchpad:
			return make_new_device(DS4EvdevController, controllerdevice, gyro, touchpad)
	
	
	def fail_cb(syspath, vid, pid):
		if HAVE_EVDEV:
			log.warning("Failed to acquire USB device, falling back to evdev driver. This is far from optimal.")
			make_evdev_device(syspath)
		else:
			log.error("Failed to acquire USB device and evdev is not available. Everything is lost and DS4 support disabled.")
			# TODO: Maybe add_error here, but error reporting needs little rework so it's not threated as fatal
			# daemon.add_error("ds4", "No access to DS4 device")
	
	if config["drivers"].get("hiddrv") or (HAVE_EVDEV and config["drivers"].get("evdevdrv")):
		register_hotplug_device(hid_callback, VENDOR_ID, PRODUCT_ID, on_failure=fail_cb)
		if HAVE_EVDEV and config["drivers"].get("evdevdrv"):
			daemon.get_device_monitor().add_callback("bluetooth",
							VENDOR_ID, PRODUCT_ID, make_evdev_device, None)
		return True
	else:
		log.warning("Neither HID nor Evdev driver is enabled, DS4 support cannot be enabled.")
		return False


if __name__ == "__main__":
	""" Called when executed as script """
	init_logging()
	set_logging_level(True, True)
	sys.exit(hiddrv_test(DS4Controller, [ "054c:09cc" ]))
