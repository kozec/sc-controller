#!/usr/bin/env python2
"""
SC-Controller - Daemon - CemuHookUDP motion provider

Accepts all connections from clients and sends data captured
by 'cemuhook' actions to them.
"""

from scc.tools import find_library
from scc.lib.enum import IntEnum
from ctypes import c_uint32, c_int, c_bool, c_char_p, c_size_t, c_float
from ctypes import create_string_buffer
import logging, socket
log = logging.getLogger("CemuHook")

BUFFER_SIZE = 1024
PORT = 26760


class MessageType(IntEnum):
	DSUC_VERSIONREQ =	0x100000
	DSUS_VERSIONRSP =	0x100000
	DSUC_LISTPORTS =	0x100001
	DSUS_PORTINFO =		0x100001
	DSUC_PADDATAREQ =	0x100002
	DSUS_PADDATARSP =	0x100002


class CemuhookServer:
	C_DATA_T = c_float * 6
	
	def __init__(self, daemon):
		self._lib = find_library('libcemuhook')
		self._lib.cemuhook_data_recieved.argtypes = [ c_int, c_int, c_char_p, c_size_t ]
		self._lib.cemuhook_data_recieved.restype = None
		self._lib.cemuhook_feed.argtypes = [ c_int, c_int, CemuhookServer.C_DATA_T ]
		self._lib.cemuhook_feed.restype = None
		self._lib.cemuhook_socket_enable.argtypes = []
		self._lib.cemuhook_socket_enable.restype = c_bool
		
		if not self._lib.cemuhook_socket_enable():
			raise OSError("cemuhook_socket_enable failed")
		
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		
		poller = daemon.get_poller()
		daemon.poller.register(self.socket.fileno(), poller.POLLIN, self.on_data_recieved)
		
		self.socket.bind(('127.0.0.1', 26760))
		log.info("Created CemuHookUDP Motion Provider")
	
	
	def on_data_recieved(self, fd, event_type):
		if fd != self.socket.fileno(): return
		message, (ip, port) = self.socket.recvfrom(BUFFER_SIZE)
		buffer = create_string_buffer(BUFFER_SIZE)
		self._lib.cemuhook_data_recieved(fd, port, message, len(message), buffer)
	
	
	def feed(self, data):
		c_data = CemuhookServer.C_DATA_T()
		c_data[3:6] = data[0:3]
		self._lib.cemuhook_feed(self.socket.fileno(), 0, c_data)


