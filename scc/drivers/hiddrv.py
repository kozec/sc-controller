#!/usr/bin/env python2
"""
SC Controller - Universal HID driver. For all three universal HID devices.

Borrows bit of code and configuration from evdevdrv.
"""

from scc.lib.hid_fixups import HID_FIXUPS
from scc.lib.hidparse import HIDPARSE_TYPE_AXIS, HIDPARSE_TYPE_BUTTONS
from scc.lib.hidparse import make_parsers
from scc.lib import IntEnum, usb1
from scc.drivers.usb import USBDevice, register_hotplug_device
from scc.drivers.evdevdrv import parse_config, AxisCalibrationData
from scc.constants import SCButtons, HapticPos, ControllerFlags
from scc.controller import Controller
from scc.paths import get_config_path
from scc.config import Config
from scc.tools import clamp

from collections import namedtuple
from math import pi as PI, sin, cos
import os, json, logging
log = logging.getLogger("HID")

DEV_CLASS_HID = 3
TRANSFER_TYPE_INTERRUPT = 3
LIBUSB_DT_REPORT = 0x22

HIDControllerInput = namedtuple('HIDControllerInput',
	'buttons ltrig rtrig stick_x stick_y lpad_x lpad_y rpad_x rpad_y'
)


class HIDError(Exception): pass
class NotHIDDevice(HIDError): pass
class UnparsableDescriptor(HIDError): pass


class HIDController(USBDevice, Controller):
	
	def __init__(self, device, handle, config, test_mode=False):
		USBDevice.__init__(self, device, handle)
		self._parsers = None
		
		id, size = None, 64
		for inter in self.device[0]:
			for setting in inter:
				if setting.getClass() == DEV_CLASS_HID:
					for endpoint in setting:
						if endpoint.getAttributes() == TRANSFER_TYPE_INTERRUPT:
							id = endpoint.getAddress()
							size = endpoint.getMaxPacketSize()
		
		if id is None:
			raise NotHIDDevice()
		
		vid, pid = self.device.getVendorID(), self.device.getProductID()
		if vid in HID_FIXUPS and pid in HID_FIXUPS[vid]:
			data = HID_FIXUPS[vid][pid]
		else:
			data = self.handle.getRawDescriptor(LIBUSB_DT_REPORT, 0, 512)
		
		size, self._parsers = make_parsers(data)
		self.claim_by(klass=DEV_CLASS_HID, subclass=0, protocol=0)
		Controller.__init__(self)
		self._id = "%.4xhid%.4x" % (vid, pid)
		self.flags = ControllerFlags.HAS_RSTICK | ControllerFlags.SEPARATE_STICK
		
		self.values = [ p.value for p in self._parsers ]
		self._range = list(xrange(0, len(self.values)))
		self._state = HIDControllerInput( *[0] * len(HIDControllerInput._fields) )
		
		if test_mode:
			self.set_input_interrupt(id, size, self.test_input)
		else:
			try:
				(self._button_map,
				self._axis_map,
				self._dpad_map,
				self._calibrations) = parse_config(config)
			except Exception, e:
				log.error("Failed to parse config for HID controller")
				raise
			self.set_input_interrupt(id, size, self.input)
	
	
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
		for parser in self._parsers:
			parser.decode(data)
		
		new_values = [ p.value for p in self._parsers ]
		for i in self._range:
			if self.values[i] != new_values[i]:
				p = self._parsers[i]
				if p.TYPE == HIDPARSE_TYPE_AXIS:
					print "Axis", p.id, new_values[i]
					pass
				if p.TYPE == HIDPARSE_TYPE_BUTTONS:
					pressed = new_values[i] & ~self.values[i]
					released = self.values[i] & ~new_values[i]
					# Note: This is _slow_. Doesn't matter. It's test
					for b in xrange(0, p.count):
						mask = 1 << b
						if pressed & mask:
							print "ButtonPress", p.id + b
						if released & mask:
							print "ButtonRelease", p.id + b
		
		self.values = new_values
	
	
	def input(self, endpoint, data):
		for parser in self._parsers:
			parser.decode(data)
		
		new_state = self._state
		new_values = [ p.value for p in self._parsers ]
		for i in self._range:
			if self.values[i] != new_values[i]:
				p = self._parsers[i]
				if p.TYPE == HIDPARSE_TYPE_AXIS and p.id in self._axis_map:
					cal = self._calibrations[p.id]
					value = (float(p.value) * cal.scale) + cal.offset
					if value >= -cal.deadzone and value <= cal.deadzone:
						value = 0
					else:
						value = clamp(cal.clamp_min,
								int(value * cal.clamp_max), cal.clamp_max)
					axis = self._axis_map[p.id]
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
		
		if new_state is not self._state:
			old_state, self._state = self._state, new_state
			if self.mapper:
				print "MAAAPER", new_state
				self.mapper.input(self, old_state, new_state)
		
		self.values = new_values
	
	
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


def hiddrv_test():
	"""
	Small driver tester used by GUI while setting up the device.
	Basically, if HID device works with this, it will work with daemon as well.
	"""
	import sys
	from scc.poller import Poller
	from scc.drivers.usb import _usb
	from scc.tools import init_logging, set_logging_level
	
	try:
		if ":" in sys.argv[1]:
			sys.argv[1:2] = sys.argv[1].split(":")
		vendor_id = int(sys.argv[1], 16)
		product_id = int(sys.argv[2], 16)
	except Exception, e:
		print >>sys.stderr, "Usage: %s vendor_id device_id" % (sys.argv[0], )
		sys.exit(1)
	
	class FakeDaemon(object):
		
		def __init__(self):
			self.poller = Poller()
		
		def add_error(self, id, error):
			log.error(error)
		
		def remove_error(*a): pass
		
		def get_poller(self):
			return self.poller
	
	fake_daemon = FakeDaemon()
	
	def cb(device, handle):
		return HIDController(device, handle, fake_daemon, test_mode=True)
	
	init_logging()
	set_logging_level(True, True)
	register_hotplug_device(cb, vid, pid)
	_usb._daemon = fake_daemon
	_usb.start()
	while True:
		fake_daemon.poller.poll()
		_usb.mainloop()


def init(daemon):
	""" Called from scc-daemon """
	HIDDrv(daemon)

if __name__ == "__main__":
	""" Called when executed as script """
	hiddrv_test()