#!/usr/bin/python2
from __future__ import unicode_literals

from SocketServer import TCPServer, ThreadingMixIn


class StreamServer(ThreadingMixIn, TCPServer):
	PORT = 19555
	daemon_threads = True
	def __init__(self, whatever, handler):
		TCPServer.__init__(self, ("localhost", self.PORT), handler)
