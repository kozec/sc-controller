#!/usr/bin/env python2
"""
SC-Controller - Daemon class

To control running daemon instance, unix socket in user directory is used.
Controlling "protocol" is dead-simple:
 - When new connection is accepted, daemon sends two lines:
      SCCDaemon version 0.1
      Current profile: filename.json
 - Connection is held until client side closes it.
 - Recieved line is treated as filename of profie, that should be loaded istead
   currently active profile.
 - If profile is loaded, daemon responds with 'OK'.
 - If loading fails, error along with entire backtrace is sent to client side.
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

from SocketServer import UnixStreamServer, ThreadingMixIn, StreamRequestHandler
import os, sys, signal, socket, select, logging, threading, traceback
log = logging.getLogger("App")
tlog = logging.getLogger("Socket Thread")

class ThreadingUnixStreamServer(ThreadingMixIn, UnixStreamServer): daemon_threads = True

DEFAULT_PID_FILE =	os.path.expanduser('~/.scccontroller.pid')
DEFAULT_SOCKET =	os.path.expanduser('~/.scccontroller.socket')

class SCCDaemon(Daemon):
	VERSION = "0.1"
	
	def __init__(self, piddile, socket_file):
		set_logging_level(True, True)
		Daemon.__init__(self, piddile)
		self.started = False
		self.socket_file = socket_file
		self.sserver = None
		self.mapper = None
		self.lock = threading.Lock()
		self.profile_file = None
		self.cwd = os.getcwd()
	
	
	def load_profile(self, filename):
		self.profile_file = filename
		if self.mapper is not None:
			self.mapper.profile.load(filename)
	
	
	def _set_profile(self, filename):
		# Called from socket server thread
		p = Profile(TalkingActionParser())
		p.load(filename)
		self.profile_file = filename
		# This last line kinda depends on GIL...
		self.mapper.profile = p
	
	
	def on_start(self):
		os.chdir(self.cwd)
		self.mapper = Mapper(Profile(TalkingActionParser()))
		if self.profile_file is not None:
			try:
				self.mapper.profile.load(self.profile_file)
			except Exception, e:
				log.warning("Failed to load profile. Starting with no mappings.")
				log.warning("Reason:")
				log.warning(e)
	
	
	def sigterm(self, *a):
		log.debug("SIGTERM")
		self.remove_socket()
		sys.exit(0)
	
	
	def run(self):
		log.debug("Starting SCCDaemon...")
		signal.signal(signal.SIGTERM, self.sigterm)
		self.start_listening()
		sc = SCController(callback=self.mapper.callback)
		sc.run()
	
	
	def start_listening(self):
		if os.path.exists(self.socket_file):
			os.unlink(self.socket_file)
		instance = self
		
		class SSHandler(StreamRequestHandler):
			def handle(self):
				instance._sshandler(self.rfile, self.wfile)
		
		self.sserver = ThreadingUnixStreamServer(self.socket_file, SSHandler)
		t = threading.Thread(target=self.sserver.serve_forever)
		t.daemon = True
		t.start()
		os.chmod(self.socket_file, 0600)
		log.debug("Created control socket %s", self.socket_file)
	
	
	def _sshandler(self, rfile, wfile):
		self.lock.acquire()
		wfile.write(b"SCCDaemon\n")
		wfile.write(("Version: %s\n" % (SCCDaemon.VERSION,)).encode("utf-8"))
		wfile.write(("PID: %s\n" % (os.getpid(),)).encode("utf-8"))
		wfile.write(("Current profile: %s\n" % (self.profile_file,)).encode("utf-8"))
		self.lock.release()
		while True:
			line = rfile.readline()
			if len(line) == 0: break
			self.lock.acquire()
			try:
				filename = line.decode("utf-8").strip("\t\n ")
				self._set_profile(filename)
				log.info("Loaded profile '%s'", filename)
				self.lock.release()
				wfile.write("OK\n")
			except Exception, e:
				log.error(e)
				self.lock.release()
				tb = traceback.format_exc()
				wfile.write(unicode(tb).encode("utf-8"))
	
	
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
					reads.append(connection)
					connection.send(b"SCCDaemon\n")
					connection.send(("Version: %s\n" % (SCCDaemon.VERSION,)).encode("utf-8"))
					connection.send(("PID: %s\n" % (os.getpid(),)).encode("utf-8"))
					connection.send(("Current profile: %s\n" % (self.profile_file,)).encode("utf-8"))
				else:
					try:
						data = s.recv(1024)
					except socket.error:
						# Remote side closed
						data = None
					if data and "\n" in data:
						data = data.decode("utf-8")
						filename = data[0:data.index("\n")]
						tlog.debug("Loading profile '%s'", filename)
						try:
							self._set_profile(filename)
							connection.send(b"OK\n")
						except Exception, e:
							tb = traceback.format_exc()
							tlog.debug("Failed")
							tlog.error(e)
							connection.send(unicode(tb).encode("utf-8"))
						while s in reads:
							reads.remove(s)
						s.close()
					else:
						while s in reads:
							reads.remove(s)
						s.close()
	
	
	def remove_socket(self):
		self.sserver.shutdown()
		if os.path.exists(self.socket_file):
			os.unlink(self.socket_file)
		log.debug("Control socket removed")
	
	
	def debug(self):
		set_logging_level(True, True)
		self.on_start()
		self.write_pid()
		try:
			self.run()
		except KeyboardInterrupt:
			log.debug("Break")
		self.remove_socket()
		sys.exit(0)
