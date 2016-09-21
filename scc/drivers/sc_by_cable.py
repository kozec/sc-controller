#!/usr/bin/env python2

from scc.lib import usb1
from scc.drivers.usb import USBDevice, register_hotplug_device
from sc_dongle import ControllerInput, SCI_NULL, TUP_FORMAT
from sc_dongle import SCStatus, SCPacketType, SCConfigType, SCController
import struct, time, logging

VENDOR_ID = 0x28de
PRODUCT_ID = 0x1102
ENDPOINT = 3
CONTROLIDX = 2

log = logging.getLogger("SCCable")

def init(daemon):
	""" Registers hotplug callback for controller dongle """
	def cb(device, handle):
		return SCByCable(device, handle, daemon)
	
	register_hotplug_device(cb, VENDOR_ID, PRODUCT_ID)


class SCByCable(USBDevice, SCController):
	def __init__(self, device, handle, daemon):
		USBDevice.__init__(self, device, handle)
		SCController.__init__(self, self, CONTROLIDX, ENDPOINT)
		self.daemon = daemon
		self._ready = False
		
		self.claim_by(klass=3, subclass=0, protocol=0)
		
		rawserial = self._driver.make_request(CONTROLIDX,
			struct.pack('>BBB61x', 0xae, 0x15, 0x01), timeout=2)
		self._serial = "".join(struct.unpack(">xxx12c49x", rawserial))
		log.debug("Got wired SC with serial %s", self._serial)
		
		self.set_input_interrupt(ENDPOINT, 64, self._wait_input)
	
	
	def _wait_input(self, endpoint, data):
		tup = ControllerInput._make(struct.unpack(TUP_FORMAT, data))
		if not self._ready:
			self.daemon.add_controller(self)
			self._configure()
			self._ready = True
		if tup.status == SCStatus.INPUT:
			self.input(tup)
	
	
	def close(self):
		if self._ready:
			self.daemon.remove_controller(self)
			self._ready = False
	
	
	def turnoff(self):
		log.warning("Ignoring request to turn off wired controller.")
	