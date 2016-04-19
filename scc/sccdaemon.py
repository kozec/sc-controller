#!/usr/bin/env python2
"""
SC-Controller - Daemon class

To control running daemon instance, unix socket in user directory is used.
Controlling "protocol" is dead-simple:
 - When new connection is accepted, daemon sends two lines:
      SCCDaemon version 0.1
      Current profile: filename.json
 - Connection is held until other side closes it or sends line of text
 - Recieved line is treated as filename of profie, that should be loaded istead
   currently active profile.
 - If profile is loaded, daemon responds with 'OK' and closes connection.
 - If loading fails, error along with entire backtrace is sent and connection
   is closed anyway.
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

import os, sys, signal, socket, select, logging, threading, traceback
log = logging.getLogger("App")
tlog = logging.getLogger("Socket Thread")

class SCCDaemon(Daemon):
	VERSION = "0.1"
	
	def __init__(self, piddile, socket_file):
		set_logging_level(True, True)
		Daemon.__init__(self, piddile)
		self.started = False
		self.socket_file = socket_file
		self.mapper = None
		self.profile_file = None
		self.cwd = os.getcwd()
	
	
	def load_profile(self, filename):
		self.profile_file = filename
		if self.mapper is not None:
			self.mapper.profile.load(filename)
	
	
	def _set_profile(self, filename):
		# Called from socket thread
		# This kinda depends on GIL - new profile object is created and
		# profile is loaded in socket thread and then mapper profile is
		# is switched on the fly.
		p = Profile(TalkingActionParser())
		p.load(filename)
		self.profile_file = filename
		self.mapper.profile = p
	
	
	def on_start(self):
		os.chdir(self.cwd)
		self.mapper = Mapper(Profile(TalkingActionParser()))
		if self.profile_file is not None:
			self.mapper.profile.load(self.profile_file)
	
	
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
		self.socket.setblocking(0)
		self.socket.bind(self.socket_file)
		os.chmod(self.socket_file, 0600)
		log.debug("Created control socket %s" % (self.socket_file,))
		threading.Thread(target=self._listen_on_socket).start()
	
	
	def _listen_on_socket(self):
		tlog.debug("Listening...")
		self.socket.listen(2)
		reads = [ self.socket ]
		while len(reads):
			try:
				readable, trash, errors = select.select(reads, [], reads, 1)
			except socket.error:
				# Happens durring exit
				tlog.debug("Socket lost")
				return
			for s in reads:
				if s is self.socket:
					try:
						connection, client = s.accept()
					except socket.error:
						# Happens when ^C is pressed
						continue
					connection.setblocking(0)
					reads.append(connection)
					connection.send("SCCDaemon version %s\n" % (SCCDaemon.VERSION,))
					connection.send("Current profile: %s\n" % (self.profile_file,))
				else:
					try:
						data = s.recv(1024)
					except socket.error:
						# Remote side closed
						data = None
					if data and "\n" in data:
						filename = data[0:data.index("\n")]
						tlog.debug("Loading profile '%s'" % (filename,))
						try:
							self._set_profile(filename)
							connection.send("OK\n")
						except Exception, e:
							tb = traceback.format_exc()
							tlog.debug("Failed")
							tlog.error(e)
							connection.send(str(tb))
					else:
						while s in reads:
							reads.remove(s)
						s.close()
	
	
	def remove_socket(self):
		self.socket.close()
		if os.path.exists(self.socket_file):
			os.unlink(self.socket_file)
		log.debug("Control socket removed")
	
	
	def debug(self):
		set_logging_level(True, True)
		self.on_start()
		try:
			self.run()
		except KeyboardInterrupt:
			log.debug("Break")
		self.remove_socket()
		sys.exit(0)
