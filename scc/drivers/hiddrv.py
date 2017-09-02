#!/usr/bin/env python2
"""
SC Controller - Universal HID driver. For all three universal HID devices.

Borrows bit of code and configuration from evdevdrv.
"""

from scc.lib.hidparse import HIDPARSE_TYPE_AXIS, HIDPARSE_TYPE_BUTTONS
from scc.lib.hidparse import GlobalItem, LocalItem, MainItem, ItemType
from scc.lib.hidparse import UsagePage, parse_report_descriptor, AXES
from scc.lib.hid_fixups import HID_FIXUPS
from scc.drivers.usb import USBDevice, register_hotplug_device
from scc.constants import SCButtons, HapticPos, ControllerFlags
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX
from scc.drivers.evdevdrv import FIRST_BUTTON, TRIGGERS, parse_axis
from scc.tools import find_library, clamp
from scc.controller import Controller
from scc.paths import get_config_path
from scc.lib import IntEnum, usb1
from scc.config import Config

from collections import namedtuple
from math import pi as PI, sin, cos
import os, json, ctypes, sys, logging
log = logging.getLogger("HID")

DEV_CLASS_HID = 3
TRANSFER_TYPE_INTERRUPT = 3
LIBUSB_DT_REPORT = 0x22
AXIS_COUNT = 8		# Must match number of axis fields in HIDControllerInput and values in AxisType
BUTTON_COUNT = 32	# Must match (or be less than) number of bits in HIDControllerInput.buttons
ALLOWED_SIZES = [1, 2, 4, 8, 16, 32]


class HIDDrvError(Exception): pass
class NotHIDDevice(HIDDrvError): pass
class UnparsableDescriptor(HIDDrvError): pass

class HIDControllerInput(ctypes.Structure):
	_fields_ = [
		('buttons', ctypes.c_uint32),
		# Note: Axis order is same as in AxisType enum
		('lpad_x', ctypes.c_int32),
		('lpad_y', ctypes.c_int32),
		('rpad_x', ctypes.c_int32),
		('rpad_y', ctypes.c_int32),
		('stick_x', ctypes.c_int32),
		('stick_y', ctypes.c_int32),
		('ltrig', ctypes.c_int32),
		('rtrig', ctypes.c_int32),
	]


class AxisType(IntEnum):
	AXIS_LPAD_X  = 0
	AXIS_LPAD_Y  = 1
	AXIS_RPAD_X = 2
	AXIS_RPAD_Y = 3
	AXIS_STICK_X = 4
	AXIS_STICK_Y = 5
	AXIS_LTRIG   = 6
	AXIS_RTRIG   = 7


class AxisMode(IntEnum):
	DISABLED      = 0
	AXIS          = 1
	AXIS_NO_SCALE = 2
	DPAD          = 3


class AxisModeData(ctypes.Structure):
	_fields_ = [
		('scale', ctypes.c_float),
		('offset', ctypes.c_float),
		('clamp_min', ctypes.c_int),
		('clamp_max', ctypes.c_int),
		('deadzone', ctypes.c_float),
	]


class DPadModeData(ctypes.Structure):
	_fields_ = [
		('button1', ctypes.c_uint8),
		('button2', ctypes.c_uint8),
		('min', ctypes.c_int),
		('max', ctypes.c_int),
	]


class AxisDataUnion(ctypes.Union):
	_fields_ = [
		('axis', AxisModeData),
		('dpad', DPadModeData),
	]


class AxisData(ctypes.Structure):
	_fields_ = [
		('mode', ctypes.c_int),
		('byte_offset', ctypes.c_size_t),
		('bit_offset', ctypes.c_uint8),
		('size', ctypes.c_uint8),	# TODO: Currently unused
		
		('data', AxisDataUnion),
	]


class ButtonData(ctypes.Structure):
	_fields_ = [
		('enabled', ctypes.c_bool),
		('byte_offset', ctypes.c_size_t),
		('bit_offset', ctypes.c_uint8),
		('size', ctypes.c_uint8),
		('button_count', ctypes.c_uint8),
		('button_map', ctypes.c_uint8 * BUTTON_COUNT),
	]


class HIDDecoder(ctypes.Structure):
	_fields_ = [
		('axes', AxisData * AXIS_COUNT),
		('buttons', ButtonData),
		('packet_size', ctypes.c_size_t),
		
		('old_state', HIDControllerInput),
		('state', HIDControllerInput),
	]


HIDDecoderPtr = ctypes.POINTER(HIDDecoder)


_lib = find_library('libhiddrv')
_lib.decode.restype = bool
_lib.decode.argtypes = [ HIDDecoderPtr, ctypes.c_char_p ]


class HIDController(USBDevice, Controller):
	
	def __init__(self, device, handle, config, test_mode=False):
		USBDevice.__init__(self, device, handle)
		
		id = None
		max_size = 64
		for inter in self.device[0]:
			for setting in inter:
				if setting.getClass() == DEV_CLASS_HID:
					for endpoint in setting:
						if endpoint.getAttributes() == TRANSFER_TYPE_INTERRUPT:
							if id is None or endpoint.getAddress() > id:
								id = endpoint.getAddress()
								max_size = endpoint.getMaxPacketSize()
		
		if id is None:
			raise NotHIDDevice()
		
		log.debug("Endpoint: %s", id)
		
		vid, pid = self.device.getVendorID(), self.device.getProductID()
		self._packet_size = 64
		self._load_hid_descriptor(config, max_size, vid, pid)
		self.claim_by(klass=DEV_CLASS_HID, subclass=0, protocol=0)
		self._id = "%.4xhid%.4x" % (vid, pid)
		Controller.__init__(self)
		self.flags = ControllerFlags.HAS_RSTICK | ControllerFlags.SEPARATE_STICK
		
		if test_mode:
			self.set_input_interrupt(id, self._packet_size, self.test_input)
		else:
			self.set_input_interrupt(id, self._packet_size, self.input)
	
	
	def _load_hid_descriptor(self, config, max_size, vid, pid):
		if vid in HID_FIXUPS and pid in HID_FIXUPS[vid]:
			hid_descriptor = HID_FIXUPS[vid][pid]
		else:
			hid_descriptor = self.handle.getRawDescriptor(
					LIBUSB_DT_REPORT, 0, 512)
		self._build_hid_decoder(hid_descriptor, config, max_size)
		self._packet_size = self._decoder.packet_size
	
	
	def _build_button_map(self, config):
		"""
		Returns button  map readed from configuration, in format situable
		for HIDDecoder.buttons.button_map field.
		
		Generates default if config is not available.
		"""
		if config:
			# Last possible value is default "maps-to-nothing" mapping
			buttons = [BUTTON_COUNT - 1] * BUTTON_COUNT
			for keycode, value in config.get('buttons', {}).items():
				keycode = int(keycode) - FIRST_BUTTON
				if keycode < 0 or keycode >= BUTTON_COUNT:
					# Out of range
					continue
				if value in TRIGGERS:
					# Not used here
					pass
				else:
					sc, bit = int(getattr(SCButtons, value)), 0
					while sc and (sc & 1 == 0):
						sc >>= 1
						bit += 1
					if sc & 1 == 1:
						buttons[keycode] = bit
					else:
						buttons[keycode] = BUTTON_COUNT - 1
		else:
			buttons = list(xrange(BUTTON_COUNT))
		
		return (ctypes.c_uint8 * BUTTON_COUNT)(*buttons)
	
	
	def _build_axis_maping(self, axis, config):
		"""
		Converts configuration mapping for _one_ axis to value situable
		for self._decoder.axes field.
		"""
		axis_config = config.get("axes", {}).get(str(int(axis)))
		if axis_config:
			try:
				target = ( list([ x for (x, y) in HIDControllerInput._fields_ ])
					.index(axis_config.get("axis")) - 1 )
			except Exception:
				# Maps to unknown axis
				return None, None
			cdata = parse_axis(axis_config)
			axis_data = AxisData(
				mode = AxisMode.AXIS,
				data = AxisDataUnion(
					axis = AxisModeData(**{
						field : getattr(cdata, field) for field in cdata._fields
					})
				)
			)
			return target, axis_data
		return None, None
	
	
	def _build_hid_decoder(self, data, config, max_size):
		size, count, total, kind = 1, 0, 0, None
		next_axis = AxisType.AXIS_LPAD_X
		self._decoder = HIDDecoder()
		for x in parse_report_descriptor(data, True):
			if x[0] == GlobalItem.ReportSize:
				size = x[1]
			elif x[0] == GlobalItem.ReportCount:
				count = x[1]
			elif x[0] == LocalItem.Usage:
				kind = x[1]
			elif x[0] == MainItem.Input:
				if x[1] == ItemType.Constant:
					total += count * size
					log.debug("Found %s bits of nothing", count * size)
				elif x[1] == ItemType.Data:
					if kind in AXES:
						if not size in ALLOWED_SIZES:
							raise UnparsableDescriptor("Axis with invalid size (%s bits)" % (size, ))
						for i in xrange(count):
							if next_axis < AXIS_COUNT:
								log.debug("Found axis #%s at bit %s", int(next_axis), total)
								if config:
									target, axis_data = self._build_axis_maping(next_axis, config)
									if axis_data:
										axis_data.byte_offset = total / 8
										axis_data.bit_offset = total % 8
										axis_data.size = size
										self._decoder.axes[target] = axis_data
								else:
									self._decoder.axes[next_axis] = AxisData(mode = AxisMode.AXIS_NO_SCALE)
									self._decoder.axes[next_axis].byte_offset = total / 8
									self._decoder.axes[next_axis].bit_offset = total % 8
									self._decoder.axes[next_axis].size = size
								next_axis = next_axis + 1
								if next_axis < AXIS_COUNT:
									next_axis = AxisType(next_axis)
							total += size
					elif kind == UsagePage.ButtonPage:
						if self._decoder.buttons.enabled:
							raise UnparsableDescriptor("HID descriptor with two sets of buttons")
						if count * size < 8:
							buttons_size = 8
						elif count * size < 32:
							buttons_size = 32
						else:
							raise UnparsableDescriptor("Too many buttons (up to 32 supported)")
						log.debug("Found %s buttons at bit %s", count, total)
						self._decoder.buttons = ButtonData(
							enabled = True,
							byte_offset = total / 8,
							bit_offset = total % 8,
							size = buttons_size,
							button_count = count,
							button_map = self._build_button_map(config)
						)
						total += count * size
					else:
						log.debug("Skipped over %s bits for %s at bit %s", count * size, kind, total)
						total += count * size
		
		self._decoder.packet_size = total / 8
		if total % 8 > 0:
			self._decoder.packet_size += 1
		if self._decoder.packet_size > max_size:
			self._decoder.packet_size = max_size
		log.debug("Packet size: %s", self._decoder.packet_size)
		print "Buttons:", " ".join([ str(x + FIRST_BUTTON)
				for x in xrange(self._decoder.buttons.button_count) ])
		print "Axes:", " ".join([ str(x)
				for x in xrange(len([
					a for a in self._decoder.axes
					if a.mode != AxisMode.DISABLED
				]))])
	
	
	def close(self):
		# Called when pad is disconnected
		USBDevice.close(self)
	
	
	def get_type(self):
		return "hid"
	
	
	def get_id(self):
		return self._id
	
	
	def get_id_is_persistent(self):
		return True
	
	
	def __repr__(self):
		vid, pid = self.device.getVendorID(), self.device.getProductID()
		return "<HID %.4x%.4x>" % (vid, pid)
	
	
	def test_input(self, endpoint, data):
		if not _lib.decode(ctypes.byref(self._decoder), data):
			# Returns True if anything changed
			return
		# Note: This is quite slow, but good enough for test mode
		code = 0
		for attr, trash in self._decoder.state._fields_:
			if attr == "buttons": continue
			if getattr(self._decoder.state, attr) != getattr(self._decoder.old_state, attr):
				print "Axis", code, getattr(self._decoder.state, attr)
				sys.stdout.flush()
			code += 1
		
		pressed = self._decoder.state.buttons & ~self._decoder.old_state.buttons
		released = self._decoder.old_state.buttons & ~self._decoder.state.buttons
		for j in xrange(0, self._decoder.buttons.button_count):
			mask = 1 << j
			if pressed & mask:
				print "ButtonPress", FIRST_BUTTON + j
				sys.stdout.flush()
			if released & mask:
				print "ButtonRelease", FIRST_BUTTON + j
				sys.stdout.flush()
	
	
	def input(self, endpoint, data):
		if _lib.decode(ctypes.byref(self._decoder), data):
			if self.mapper:
				self.mapper.input(self,
						self._decoder.old_state, self._decoder.state)
	
	
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


class HIDDrv(object):
	
	def __init__(self, daemon):
		self.daemon = daemon
		self.registered = set()
		self.configs = {}
		self.scan_files()
	
	
	def hotplug_cb(self, device, handle):
		vid, pid = device.getVendorID(), device.getProductID()
		if (vid, pid) in self.configs:
			controller = HIDController(device, handle, self.configs[vid, pid])
			self.daemon.add_controller(controller)
			return controller
		return None
	
	
	def scan_files(self):
		"""
		Goes through ~/.config/scc/devices and enables hotplug callback for
		every known HID device
		"""
		path = os.path.join(get_config_path(), "devices")
		if not os.path.exists(path):
			# Nothing to do
			return
		
		known = set()
		for name in os.listdir(path):
			if name.startswith("HID:") and name.endswith(".json"):
				vid, pid = name.split("-", 1)[0].split(":")[1:]
				vid = int(vid, 16)
				pid = int(pid, 16)
				config_file = os.path.join(path, name)
				try:
					config = json.loads(open(config_file, "r").read())
				except Exception, e:
					log.warning("Ignoring file that cannot be parsed: %s", name)
					continue
				
				self.configs[vid, pid] = config
				known.add((vid, pid))
		
		for new in known - self.registered:
			vid, pid = new
			register_hotplug_device(self.hotplug_cb, vid, pid)
			self.registered.add(new)
		
		for removed in self.registered - known:
			vid, pid = removed
			unregister_hotplug_device(self.hotplug_cb, vid, pid)
			self.registered.remove(removed)
			if (vid, pid) in self.configs:
				del self.config[vid, pid]


def hiddrv_test(cls, args):
	"""
	Small input test used by GUI while setting up the device.
	Basically, if HID device works with this, it will work with daemon as well.
	"""
	from scc.poller import Poller
	from scc.drivers.usb import _usb
	from scc.scripts import InvalidArguments
	from scc.tools import init_logging, set_logging_level
	
	try:
		if ":" in args[0]:
			args[0:1] = args[0].split(":")
		vid = int(args[0], 16)
		pid = int(args[1], 16)
	except Exception, e:
		raise InvalidArguments()
	
	class FakeDaemon(object):
		
		def __init__(self):
			self.poller = Poller()
			self.exitcode = -1
		
		def add_error(self, id, error):
			fake_daemon.exitcode = 2
			log.error(error)
		
		def remove_error(*a): pass
		
		def get_poller(self):
			return self.poller
	
	fake_daemon = FakeDaemon()
	
	def cb(device, handle):
		return cls(device, handle, None, test_mode=True)
		try:
			pass
		except NotHIDDevice:
			print >>sys.stderr, "%.4x:%.4x is not a HID device" % (vid, pid)
			fake_daemon.exitcode = 3
		except UnparsableDescriptor, e:
			print >>sys.stderr, "Invalid or unparsable HID descriptor", str(e)
			fake_daemon.exitcode = 4
		except Exception, e:
			print >>sys.stderr, "Failed to open device:", str(e)
			fake_daemon.exitcode = 2
	
	register_hotplug_device(cb, vid, pid)
	_usb._daemon = fake_daemon
	_usb.start()
	
	#print "Buttons:", " ".join([ str(x - FIRST_BUTTON)
	#		for x in caps.get(evdev.ecodes.EV_KEY, [])])
	#print "Axes:", " ".join([ str(axis)
	#		for (axis, trash) in caps.get(evdev.ecodes.EV_ABS, []) ])
	
	print "Ready"
	sys.stdout.flush()
	while fake_daemon.exitcode < 0:
		fake_daemon.poller.poll()
		_usb.mainloop()
	
	return fake_daemon.exitcode


def init(daemon):
	""" Called from scc-daemon """
	HIDDrv(daemon)


if __name__ == "__main__":
	""" Called when executed as script """
	init_logging()
	set_logging_level(True, True)
	sys.exit(hiddrv_test(HIDController, sys.argv[1:]))
