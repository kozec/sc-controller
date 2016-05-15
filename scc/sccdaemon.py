#!/usr/bin/env python2
"""
SC-Controller - Daemon class
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.lib.daemon import Daemon
from scc.lib.usb1 import USBErrorAccess, USBErrorBusy, USBErrorPipe
from scc.paths import get_profiles_path, get_default_profiles_path
from scc.constants import SCButtons, LEFT, RIGHT, STICK
from scc.parser import TalkingActionParser
from scc.controller import SCController
from scc.tools import set_logging_level
from scc.uinput import Keys, Axes
from scc.profile import Profile
from scc.actions import Action
from scc.mapper import Mapper

from SocketServer import UnixStreamServer, ThreadingMixIn, StreamRequestHandler
import os, sys, signal, socket, select, time, logging, threading, traceback
log = logging.getLogger("SCCDaemon")
tlog = logging.getLogger("Socket Thread")

class ThreadingUnixStreamServer(ThreadingMixIn, UnixStreamServer): daemon_threads = True


class SCCDaemon(Daemon):
	VERSION = "0.1"
	
	def __init__(self, piddile, socket_file):
		set_logging_level(True, True)
		Daemon.__init__(self, piddile)
		self.started = False
		self.socket_file = socket_file
		self.sserver = None
		self.mapper = None
		self.error = None
		self.lock = threading.Lock()
		self.profile_file = None
		self.clients = set()
		self.cwd = os.getcwd()
	
	
	def load_profile(self, filename):
		self.profile_file = filename
		if self.mapper is not None:
			self.mapper.profile.load(filename).compress()
	
	
	def _set_profile(self, filename):
		# Called from socket server thread
		p = Profile(TalkingActionParser())
		p.load(filename).compress()
		self.profile_file = filename
		
		if self.mapper.profile.gyro and not p.gyro:
			# Turn off gyro sensor that was enabled but is no longer needed
			if self.mapper.get_controller():
				log.debug("Turning gyrosensor OFF")
				self.mapper.get_controller().configure_controller(enable_gyros=False)
		elif not self.mapper.profile.gyro and p.gyro:
			# Turn on gyro sensor that was turned off, if profile has gyro action set
			if self.mapper.get_controller():
				log.debug("Turning gyrosensor ON")
				self.mapper.get_controller().configure_controller(enable_gyros=True)
		
		# This last line kinda depends on GIL...
		self.mapper.profile = p
		# Re-apply all locks
		for c in self.clients:
			c.reaply_locks(self)
		# Notify all connected clients about change
		self._send_to_all(("Current profile: %s\n" % (self.profile_file,)).encode("utf-8"))
	
	
	def _send_to_all(self, message_str):
		"""
		Sends message to all connect clients.
		Message should be utf-8 encoded str.
		"""
		for client in self.clients:
			try:
				client.wfile.write(message_str)
			except: pass
	
	
	def on_sa_turnoff_(self, mapper, action):
		""" Called when 'turnoff' action is used """
		if mapper.get_controller():
			mapper.get_controller().turnoff()
	
	
	def on_sa_shell(self, mapper, action):
		""" Called when 'shell' action is used """
		os.system(action.command + " &")
	
	
	def on_sa_profile(self, mapper, action):
		""" Called when 'profile' action is used """
		name = action.profile
		if name.startswith(".") or "/" in name:
			# Small sanity check
			log.error("Cannot load profile: Profile '%s' not found", name)
			return
		filename = name + ".sccprofile"
		for p in (get_profiles_path(), get_default_profiles_path()):
			path = os.path.join(p, filename)
			if os.path.exists(path):
				self.lock.acquire()
				try:
					self._set_profile(path)
					self.lock.release()
					log.info("Loaded profile '%s'", name)
				except Exception, e:
					self.lock.release()
					log.error(e)
				return
		log.error("Cannot load profile: Profile '%s' not found", name)
	
	
	def on_start(self):
		os.chdir(self.cwd)
		self.mapper = Mapper(Profile(TalkingActionParser()))
		self.mapper.set_special_actions_handler(self)
		if self.profile_file is not None:
			try:
				self.mapper.profile.load(self.profile_file).compress()
			except Exception, e:
				log.warning("Failed to load profile. Starting with no mappings.")
				log.warning("Reason: %s", e)
	
	
	def on_controller_status(self, sc, onoff):
		if onoff:
			log.debug("Controller turned ON")
		else:
			log.debug("Controller turned OFF")
	
	
	def sigterm(self, *a):
		log.debug("SIGTERM")
		self._remove_socket()
		sys.exit(0)
	
	
	def run(self):
		log.debug("Starting SCCDaemon...")
		signal.signal(signal.SIGTERM, self.sigterm)
		self.lock.acquire()
		self.start_listening()
		while True:
			#try:
				sc = SCController(callback=self.mapper.callback)
				sc.configure_controller(enable_gyros=bool(self.mapper.profile.gyro))
				self.mapper.set_controller(sc)
				sc.setStatusCallback(self.on_controller_status)
				if self.error is not None:
					self.error = None
					log.debug("Recovered after error")
					self._send_to_all(b"Ready.\n")
				self.lock.release()
				sc.run()
			except (ValueError, USBErrorAccess, USBErrorBusy, USBErrorPipe), e:
				# When SCController fails to initialize, daemon should
				# still stay alive, so it is able to report this failure.
				#
				# As this is most likely caused by hw device being not
				# connected or busy, daemon will also repeadedly try to
				# reinitialize SCController instance expecting error to be
				# fixed by higher power (aka. user)
				was_error = self.error is not None
				self.error = unicode(e)
				try:
					self.lock.release()
				except: pass
				log.error(e)
				if not was_error:
					self._send_to_all(("Error: %s\n" % (self.error,)).encode("utf-8"))
				time.sleep(5)
				self.lock.acquire()
	
	
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
		client = Client(rfile, wfile)
		self.clients.add(client)
		wfile.write(b"SCCDaemon\n")
		wfile.write(("Version: %s\n" % (SCCDaemon.VERSION,)).encode("utf-8"))
		wfile.write(("PID: %s\n" % (os.getpid(),)).encode("utf-8"))
		wfile.write(("Current profile: %s\n" % (self.profile_file,)).encode("utf-8"))
		if self.error is None:
			wfile.write(b"Ready.\n")
		else:
			wfile.write(("Error: %s\n" % (self.error,)).encode("utf-8"))
		
		self.lock.release()
		while True:
			try:
				line = rfile.readline()
			except Exception:
				# Connection terminated
				break
			if len(line) == 0: break
			if len(line.strip("\t\n ")) > 0:
				self._handle_message(client, line.strip("\n"))
		self.lock.acquire()
		client.unlock_actions(self)
		self.clients.remove(client)
		self.lock.release()
	
	
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
	
	
	def _handle_message(self, client, message):
		"""
		Handles message recieved from client.
		"""
		if message.startswith("Profile:"):
			self.lock.acquire()
			try:
				filename = message[8:].decode("utf-8").strip("\t ")
				self._set_profile(filename)
				log.info("Loaded profile '%s'", filename)
				self.lock.release()
				client.wfile.write(b"OK.\n")
			except Exception, e:
				log.error(e)
				self.lock.release()
				tb = unicode(traceback.format_exc()).encode("utf-8").encode('string_escape')
				client.wfile.write(b"Fail: " + tb + b"\n")
		elif message.startswith("Lock:"):
			to_lock = [ x for x in message[5:].strip(" \t\r").split(" ") ]
			self.lock.acquire()
			try:
				for l in to_lock:
					if not self._can_lock_action(SCCDaemon.source_to_constant(l)):
						client.wfile.write(b"Fail: Cannot lock " + l.encode("utf-8") + b"\n")
						self.lock.release()
						return
			except ValueError, e:
				tb = unicode(traceback.format_exc()).encode("utf-8").encode('string_escape')
				client.wfile.write(b"Fail: " + tb + b"\n")
				self.lock.release()
				return
			for l in to_lock:
				self._lock_action(SCCDaemon.source_to_constant(l), client)
			self.lock.release()
			client.wfile.write(b"OK.\n")
		elif message.startswith("Unlock."):
			self.lock.acquire()
			client.unlock_actions(self)
			self.lock.release()
			client.wfile.write(b"OK.\n")
		else:
			client.wfile.write(b"Fail: Unknown command\n")
	
	
	def _can_lock_action(self, what):
		"""
		Returns True if action assigned to axis,
		pad or button is not yet locked.
		
		Should be called while self.lock is acquired.
		"""
		if what == STICK:
			if isinstance(self.mapper.profile.buttons[SCButtons.STICK], LockedAction):
				return False
			if isinstance(self.mapper.profile.stick, LockedAction):
				return False
			return True
		if what in SCButtons:
			return not isinstance(self.mapper.profile.buttons[what], LockedAction)
		if what in (LEFT, RIGHT):
			return not isinstance(self.mapper.profile.pads[what], LockedAction)
		return False
	
	
	def _lock_action(self, what, client):
		"""
		Locks action so event can be send to client instead of handling it.
		
		Should be called while self.lock is acquired.
		"""
		if what == STICK:
			a = self.mapper.profile.stick.compress()
			self.mapper.profile.stick = LockedAction(what, client, a)
			return
		if what in SCButtons:
			a = self.mapper.profile.buttons[what].compress()
			self.mapper.profile.buttons[what] = LockedAction(what, client, a)
			return
		if what in (LEFT, RIGHT):
			a = self.mapper.profile.pads[what].compress()
			self.mapper.profile.pads[what] = LockedAction(what, client, a)
			return
		# TODO: Triggers
			
		# Shouldn't really reach here
		log.warning("Failed to lock action: Don't know what is %s", what)
	
	
	def _unlock_action(self, what):
		"""
		Unlocks action so event can be handled normally.
		
		Should be called while self.lock is acquired.
		"""
		if what == STICK:
			a = self.mapper.profile.stick.original_action
			self.mapper.profile.stick = a
			return
		if what in SCButtons:
			a = self.mapper.profile.buttons[what].original_action
			self.mapper.profile.buttons[what] = a
			return
		if what in (LEFT, RIGHT):
			a = self.mapper.profile.pads[what].original_action
			self.mapper.profile.pads[what] = a
			return
		# TODO: Triggers
			
		# Shouldn't really reach here
		log.warning("Failed to unlock action: Don't know what is %s", what)
	
	
	@staticmethod
	def source_to_constant(s):
		"""
		Turns string as 'A', 'LEFT' or 'ABS_X' into one of SCButtons.*,
		LEFT, RIGHT or STICK constants.
		
		Raises ValueError if passed string cannot be converted.
		
		Used when parsing `Lock: ...` message
		"""
		s = s.strip(" \t\r\n")
		if s in (STICK, LEFT, RIGHT):
			return s
		if hasattr(SCButtons, s):
			return getattr(SCButtons, s)
		raise ValueError("Unknown source: %s" % (s,))
	
	
	def _remove_socket(self):
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
		self._remove_socket()
		sys.exit(0)


class Client(object):
	def __init__(self, rfile, wfile):
		self.rfile = rfile
		self.wfile = wfile
		self.locked_actions = set()
	
	
	def unlock_actions(self, daemon):
		""" Should be called while daemon.lock is acquired """
		s, self.locked_actions = self.locked_actions, set()
		for a in s:
			daemon._unlock_action(a.what)
			log.debug("%s unlocked", a.what)
	
	
	def reaply_locks(self, daemon):
		"""
		Called after profile is changed.
		Should be called while daemon.lock is acquired
		"""
		s, self.locked_actions = self.locked_actions, set()
		for a in s:
			daemon._lock_action(a.what, self)



class LockedAction(Action):
	def __init__(self, what, client, original_action):
		self.what = what
		self.client = client
		self.original_action = original_action
		self.client.locked_actions.add(self)
		log.debug("%s locked by %s", what, client)
	
	
	def button_press(self, mapper):
		self.client.wfile.write(("Event: %s 1\n" % (self.what.name,)).encode("utf-8"))
	
	def button_release(self, mapper):
		self.client.wfile.write(("Event: %s 0\n" % (self.what.name,)).encode("utf-8"))
	
	def whole(self, mapper, x, y, what):
		self.client.wfile.write(("Event: %s %s %s\n" % (what, x, y)).encode("utf-8"))
