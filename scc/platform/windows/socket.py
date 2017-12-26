#!/usr/bin/env python2
"""
SC-Controller - Windows Socket

This is just copy-pasted from normal Socket class and rewritten to use TCP.
"""
from __future__ import unicode_literals, absolute_import

from SocketServer import TCPServer, ThreadingMixIn, StreamRequestHandler
from scc.constants import TCP_PORT

import threading, logging, socket
log = logging.getLogger("SCCDaemon")	# Same as sccdaemon.py, intentionally


class _ThreadedServer(ThreadingMixIn, TCPServer):
	daemon_threads = True
	pass


class Socket(object):
	def __init__(self, connection_handler):
		self._connection_handler = connection_handler
	
	
	def start_listening(self):
		class Handler(StreamRequestHandler):
			def handle(handler):
				return self._connection_handler(handler.connection,
					handler.rfile, handler.wfile)
		
		self._server = _ThreadedServer(("localhost", TCP_PORT), Handler)
		self._thread = threading.Thread(target=self._server.serve_forever)
		self._thread.daemon = True
		self._thread.start()
		
		log.debug("Listening on :%s", TCP_PORT)
		return self
	
	
	def shutdown(self):
		self._server.shutdown()
		log.debug("Control socket closed")


def ClientSocket():
	return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
