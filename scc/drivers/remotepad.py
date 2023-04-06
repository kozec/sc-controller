#!/usr/bin/env python3
"""
SC Controller - remotepad driver

This is implementation or protocol used by Retroarch's Remote RetroPad core.
Based on https://github.com/libretro/RetroArch/blob/master/cores/libretro-net-retropad.
"""
from scc.tools import find_library
from scc.constants import ControllerFlags
from scc.controller import Controller
from ctypes import CFUNCTYPE, POINTER, byref, cast, c_void_p
import logging, socket, ctypes

log = logging.getLogger("remotepad")


class ControllerInput(ctypes.Structure):
	_fields_ = [
		("buttons",		ctypes.c_uint32),
		("ltrig",		ctypes.c_uint8),
		("rtrig",		ctypes.c_uint8),
		("stick_x",		ctypes.c_int16),
		("stick_y",		ctypes.c_int16),
		("lpad_x",		ctypes.c_int16),
		("lpad_y",		ctypes.c_int16),
		("rpad_x",		ctypes.c_int16),
		("rpad_y",		ctypes.c_int16),
		("cpad_x",		ctypes.c_int16),
		("cpad_y",		ctypes.c_int16),
		("gpitch",		ctypes.c_int16),
		("groll",		ctypes.c_int16),
		("gyaw",		ctypes.c_int16),
		("q1",			ctypes.c_int16),
		("q2",			ctypes.c_int16),
		("q3",			ctypes.c_int16),
		("q4",			ctypes.c_int16),
	]


MapperInputCB = CFUNCTYPE(None, c_void_p, POINTER(ControllerInput))


class Mapper(ctypes.Structure):
	_fields_ = [
		("input",		MapperInputCB),
	]


class RemotePad(ctypes.Structure):
	_fields_ = [
		("mapper",		POINTER(Mapper)),
		("input",		ControllerInput),
	]


class RemoteJoypadMessage(ctypes.Structure):
	_fields_ = [
		('port',		ctypes.c_int),
		('device',		ctypes.c_int),
		('index',		ctypes.c_int),
		('id',			ctypes.c_int),
		('state',		ctypes.c_uint16),
	]


class RemotePadController(Controller):
	flags = ( ControllerFlags.HAS_DPAD | ControllerFlags.NO_GRIPS |
				ControllerFlags.HAS_RSTICK | ControllerFlags.SEPARATE_STICK )
	
	def __init__(self, driver, address):
		Controller.__init__(self)
		self._id = "rpad%s" % (self._id, )
		self._driver = driver
		self._address = address
		self._enabled = True
		self._mapper = Mapper()
		self._mapper.input = MapperInputCB(self._input)
		self._old_state = ControllerInput()
		self._state_size = ctypes.sizeof(ControllerInput)
		self._pad = RemotePad()
		self._pad.mapper = POINTER(Mapper)(self._mapper)
	
	def get_type(self):
		return "rpad"
	
	def _remove(self, *a):
		self._driver._remove(self._address)
	
	def turnoff(self):
		log.debug("Disconnecting %s", self._address)
		self._disabled = True
		self._driver.daemon.remove_controller(self)
		self._driver.daemon.get_scheduler().schedule(10.0, self._remove)
	
	def _input(self, trash, data):
		if self._enabled and self.mapper:
			self.mapper.input(self, self._old_state, data.contents)
			ctypes.memmove(byref(self._old_state), data, self._state_size)
	
	def get_gui_config_file(self):
		return "remotepad.json"


class Driver:
	PORT = 55400
	
	def __init__(self, daemon, config):
		self._controllers = {}
		self.daemon = daemon
		self.config = config
		self._lib = find_library('libremotepad')
		self._lib.remotepad_input.argtypes = [ POINTER(RemotePad), POINTER(RemoteJoypadMessage) ]
		self._lib.remotepad_input.restype = None
		self._size = ctypes.sizeof(RemoteJoypadMessage)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		server_address = ('0.0.0.0', self.PORT)
		self.sock.bind(server_address)
		poller = self.daemon.get_poller()
		poller.register(self.sock.fileno(), poller.POLLIN, self.on_data_ready)
		log.info("Listening on %s:%s", *server_address)
	
	def _remove(self, address):
		if address in self._controllers:
			del self._controllers[address]
	
	def on_data_ready(self, *a):
		data, source = self.sock.recvfrom(self._size)
		address, port = source
		controller = None
		if address not in self._controllers:
			controller = RemotePadController(self, address)
			self._controllers[address] = controller
			self.daemon.add_controller(controller)
		else:
			controller = self._controllers[address]
		
		self._lib.remotepad_input(controller._pad, cast(
				ctypes.c_char_p(data), POINTER(RemoteJoypadMessage)))


def init(daemon, config):
	""" Registers hotplug callback for controller dongle """
	
	_drv = Driver(daemon, config)
	return True
