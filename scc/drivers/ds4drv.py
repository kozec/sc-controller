#!/usr/bin/env python2
"""
SC Controller - Dualshock 4 Driver

Extends HID driver with DS4-specific options.
"""

from scc.drivers.hiddrv import BUTTON_COUNT, ButtonData, AxisType, AxisData
from scc.drivers.hiddrv import HIDController, HIDDecoder, hiddrv_test
from scc.drivers.hiddrv import AxisMode, AxisDataUnion, AxisModeData
from scc.drivers.hiddrv import HatswitchModeData
from scc.drivers.evdevdrv import HAVE_EVDEV, EvdevController
from scc.drivers.evdevdrv import make_new_device, get_axes
from scc.drivers.usb import register_hotplug_device
from scc.constants import SCButtons, ControllerFlags
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX
from scc.tools import init_logging, set_logging_level
import sys, logging
log = logging.getLogger("DS4")

VENDOR_ID = 0x054c
PRODUCT_ID = 0x09cc


def init(daemon):
	""" Registers hotplug callback for ds4 device """
	def cb(device, handle):
		return DS4Controller(device, daemon, handle, None, None)
	
	def fail_cb(vid, pid):
		if HAVE_EVDEV:
			log.warning("Failed to acquire USB device, falling back to evdev driver. This is far from optimal.")
			make_new_device(vid, pid, evdev_make_device_callback)
		else:
			log.error("Failed to acquire USB device and evdev is not available. Everything is lost and DS4 support disabled.")
			# TODO: Maybe add_error here, but error reporting needs little rework so it's not threated as fatal
			# daemon.add_error("ds4", "No access to DS4 device")
	
	register_hotplug_device(cb, VENDOR_ID, PRODUCT_ID, on_failure=fail_cb)


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
		SCButtons.CPAD,
	)
	
	def __init__(self, *a, **b):
		HIDController.__init__(self, *a, **b)
		self.flags = ( ControllerFlags.EUREL_GYROS | ControllerFlags.HAS_RSTICK
						| ControllerFlags.SEPARATE_STICK )
	
	
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
		self._decoder.buttons = ButtonData(
			enabled = True, byte_offset=5, bit_offset=4, size=14,
			button_count = 14
		)
		
		if test_mode:
			for x in xrange(BUTTON_COUNT):
				self._decoder.buttons.button_map[x] = x
		else:
			for x in xrange(BUTTON_COUNT):
				self._decoder.buttons.button_map[x] = 64
			for x, sc in enumerate(DS4Controller.BUTTON_MAP):
				self._decoder.buttons.button_map[x] = self.button_to_bit(sc)
		
		self._packet_size = 64
	
	
	def get_gyro_enabled(self):
		# Cannot be actually turned off, so it's always active
		# TODO: Maybe emulate turning off?
		return True
	
	
	def get_type(self):
		return "ds4evdev"
	
	
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
	
	def __init__(self, daemon, controllerdevice, motion, touchpad):
		config = {
			'axes' : DS4EvdevController.AXIS_MAP,
			'buttons' : DS4EvdevController.BUTTON_MAP,
			'dpads' : {}
		}
		self._motion = motion
		self._touchpad = touchpad
		for device in (self._motion, self._touchpad):
			device.grab()
		EvdevController.__init__(self, daemon, controllerdevice, None, config)
	
	
	def close(self):
		EvdevController.close(self)
		for device in (self._motion, self._touchpad):
			try:
				device.ungrab()
			except: pass
	
	
	def get_gyro_enabled(self):
		# TODO: Gyro over evdev
		return False
	
	
	def get_type(self):
		return "ds4"
	
	
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


def evdev_make_device_callback(daemon, evdevdevices):
	# With kernel 4.10 or later, PS4 controller pretends to be 3 different devices.
	# 1st, determining which one is actual controller is needed
	controllerdevice = None
	for device in evdevdevices:
		count = len(get_axes(device))
		if count == 8:
			# 8 axes - Controller
			controllerdevice = device
	if not controllerdevice:
		return
	# 2nd, find motion sensor and touchpad with physical address matching
	# controllerdevice
	motion, touchpad = None, None
	phys = device.phys.split("/")[0]
	for device in evdevdevices:
		if device.phys.startswith(phys):
			count = len(get_axes(device))
			if count == 6:
				# 6 axes - Motion sensor
				motion = device
			elif count == 4:
				# 4 axes - Touchpad
				touchpad = device
	# 3rd, do a magic
	return DS4EvdevController(daemon, controllerdevice, motion, touchpad)

if __name__ == "__main__":
	""" Called when executed as script """
	init_logging()
	set_logging_level(True, True)
	sys.exit(hiddrv_test(DS4Controller, [ "054c:09cc" ]))
