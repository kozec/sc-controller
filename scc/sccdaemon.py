#!/usr/bin/env python2
"""
SC-Controller - Daemon class

This class can either act as, or controll already running daemon.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.actions import TalkingActionParser
from scc.controller import SCController
from scc.tools import set_logging_level
from scc.constants import SCButtons
from scc.profile import Profile
from scc.mapper import Mapper
from scc.uinput import Keys, Axes
from scc.daemon import Daemon


import os, sys, signal,socket, logging
log = logging.getLogger("App")

class SCCDaemon(Daemon):
	def __init__(self, piddile, socket_file):
		Daemon.__init__(self, piddile)
		self.socket_file = socket_file
		self.profile = Profile(TalkingActionParser())
		self.mapper = Mapper(self.profile)
	
	
	def load_profile(self, filename):
		self.profile.load(filename)
	
	
	def start(self):
		Daemon.start(self)
	
	
	def sigterm(self, *a):
		log.debug("SIGTERM")
		self.remove_socket()
		sys.exit(0)
	
	
	def run(self):
		log.debug("Starting SCCDaemon...")
		signal.signal(signal.SIGTERM, self.sigterm)
		self.create_socket()
		sc = SCController(callback=self.mapper.callback)
		sc.run()
	
	
	def create_socket(self):
		if os.path.exists(self.socket_file):
			os.unlink(self.socket_file)
		self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.socket.bind(self.socket_file)
		log.debug("Created control socket %s" % (self.socket_file,))
	
	
	def remove_socket(self):
		self.socket.close()
		if os.path.exists(self.socket_file):
			os.unlink(self.socket_file)
		log.debug("Control socket removed")
	
	
	def debug(self):
		set_logging_level(True, True)
		try:
			self.run()
		except KeyboardInterrupt:
			log.debug("Break")
		self.remove_socket()

