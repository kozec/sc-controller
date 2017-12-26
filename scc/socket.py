#!/usr/bin/env python2
"""
SC-Controller - Socket

Class that daemon uses to initialize socket used to communicate with GUI, OSD and
other clients.

Uses Unix socket on Linux, so this module exists mainly so Windows can override it.
"""
from __future__ import unicode_literals, absolute_import

from SocketServer import UnixStreamServer, ThreadingMixIn, StreamRequestHandler
from scc.paths import get_daemon_socket

import os, threading, socket, logging
log = logging.getLogger("SCCDaemon")	# Same as sccdaemon.py, intentionally


class _ThreadedServer(ThreadingMixIn, UnixStreamServer):
	daemon_threads = True
	pass


class Socket(object):
	def __init__(self, connection_handler):
		self._connection_handler = connection_handler
	
	
	def start_listening(self):
		socket_file = get_daemon_socket()
		if os.path.exists(socket_file):
			os.unlink(socket_file)
		
		class Handler(StreamRequestHandler):
			def handle(handler):
				return self._connection_handler(handler.connection,
					handler.rfile, handler.wfile)
		
		self._server = _ThreadedServer(socket_file, Handler)
		self._thread = threading.Thread(target=self._server.serve_forever)
		self._thread.daemon = True
		self._thread.start()
		
		os.chmod(socket_file, 0600)
		log.debug("Created control socket %s", socket_file)
		
		return self
	
	
	def shutdown(self):
		socket_file = get_daemon_socket()
		self._server.shutdown()
		if os.path.exists(socket_file):
			os.unlink(socket_file)
		log.debug("Control socket removed")


def ClientSocket():
	return socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
