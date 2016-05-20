#!/usr/bin/env python2
"""
SC-Controller - DaemonManager

Starts, kills and controls sccdaemon instance.

I'd call it DaemonController normally, but having something with
full name of "Steam Controller Controller Daemon Controller" sounds
probably too crazy even for me.
"""
from __future__ import unicode_literals

from scc.paths import get_daemon_socket
from scc.tools import find_binary
from gi.repository import GObject, Gio, GLib

import os, sys, logging
log = logging.getLogger("DaemonCtrlr")


class DaemonManager(GObject.GObject):
	"""
	List of signals:
		alive ()
			Emited after daemon is started or found to be alraedy running
		
		unknown-msg (message)
			Emited when message that can't be parsed internally
			is recieved from daemon.
		
		dead ()
			Emited after daemon is killed (or exits for some other reason)
		
		event (pad_stick_or_button, values)
			Emited when pad, stick or button is locked using lock() method
			and position or pressed state of that button is changed
		
		profile-changed (profile)
			Emited after profile is changed. Profile is filename of currently
			active profile
		
		error (description)
			Emited when daemon reports error, most likely not being able to
			access to USB dongle.
	"""
	
	__gsignals__ = {
			b"alive"			: (GObject.SIGNAL_RUN_FIRST, None, ()),
			b"unknown-msg"		: (GObject.SIGNAL_RUN_FIRST, None, (object,)),
			b"dead"				: (GObject.SIGNAL_RUN_FIRST, None, ()),
			b"error"			: (GObject.SIGNAL_RUN_FIRST, None, (object,)),
			b"event"			: (GObject.SIGNAL_RUN_FIRST, None, (object,object)),
			b"profile-changed"	: (GObject.SIGNAL_RUN_FIRST, None, (object,)),
	}
	
	RECONNECT_INTERVAL = 5
	
	def __init__(self):
		GObject.GObject.__init__(self)
		self.alive = None
		self.connection = None
		self.connecting = False
		self.buffer = ""
		self._connect()
		self._requests = []
	
	
	def _connect(self):
		if self.connecting : return
		self.connecting = True
		sc = Gio.SocketClient()
		address = Gio.UnixSocketAddress.new(get_daemon_socket())
		sc.connect_async(address, None, self._on_connected)
	
	
	def _on_daemon_died(self, *a):
		""" Called from various places when daemon looks like dead """
		# Log stuff
		if self.alive is True:
			log.debug("Connection to daemon lost")
		if self.alive is True or self.alive is None:
			self.alive = False
			self.emit("dead")
		self.alive = False
		# Close connection, if any
		if self.connection is not None:
			self.connection.close()
			self.connection = None
		# Emit event
		# Try to reconnect
		GLib.timeout_add_seconds(self.RECONNECT_INTERVAL, self._connect)
	
	
	def _on_connected(self, sc, results):
		""" Called when connection to daemon socket is initiated """
		self.connecting = False
		try:
			self.connection = sc.connect_finish(results)
			if self.connection == None:
				raise Exception("Unknown error")
		except Exception, e:
			self._on_daemon_died()
			return
		self.buffer = ""
		self.connection.get_input_stream().read_bytes_async(102400,
			1, None, self._on_read_data)
	
	
	def _on_read_data(self, sc, results):
		""" Called when daemon sends some data """
		try:
			response = sc.read_bytes_finish(results)
			if response == None:
				raise Exception("No data recieved")
		except Exception, e:
			# Broken sonnection, daemon was probbaly terminated
			self._on_daemon_died()
			return
		data = response.get_data().decode("utf-8")
		if len(data) == 0:
			# Connection terminated
			self._on_daemon_died()
			return
		self.buffer += data
		while "\n" in self.buffer:
			line, self.buffer = self.buffer.split("\n", 1)
			if line.startswith("Version:"):
				version = line.split(":", 1)[-1].strip()
				log.debug("Connected to daemon, version %s", version)
			elif line.startswith("Ready."):
				log.debug("Daemon is ready.")
				self.alive = True
				self.emit('alive')
			elif line.startswith("OK."):
				if len(self._requests) > 0:
					success_cb, error_cb = self._requests[-1]
					self._requests = self._requests[0:-1]
					success_cb()
			elif line.startswith("Fail:"):
				if len(self._requests) > 0:
					success_cb, error_cb = self._requests[-1]
					self._requests = self._requests[0:-1]
					error_cb(line[5:].strip())
			elif line.startswith("Event:"):
				data = line[6:].strip().split(" ")
				self.emit('event', data[0], [ int(x) for x in data[1:] ])
			elif line.startswith("Error:"):
				error = line.split(":", 1)[-1].strip()
				self.alive = True
				log.debug("Daemon reported error '%s'", error)
				self.emit('error', error)
			elif line.startswith("Current profile:"):
				profile = line.split(":", 1)[-1].strip()
				log.debug("Daemon reported profile change: %s", profile)
				self.emit('profile-changed', profile)
			elif line.startswith("PID:") or line == "SCCDaemon":
				# ignore
				pass
			else:
				self.emit('unknown-msg', line)
		# Connection is held forever to detect when daemon exits
		self.connection.get_input_stream().read_bytes_async(102400,
			1, None, self._on_read_data)
	
	
	def is_alive(self):
		""" Returns True if daemon is running """
		return self.alive
	
	
	def request(self, message, success_cb, error_cb):
		"""
		Creates request and remembers callback for next 'Ok' or 'Fail' message.
		"""
		if self.alive and self.connection is not None:
			self._requests.append(( success_cb, error_cb ))
			(self.connection.get_output_stream()
				.write_all(message.encode('utf-8') + b'\n', None))
		else:
			# Instant failure
			error_cb("Not connected.")
	
	def set_profile(self, filename):
		""" Asks daemon to change profile """
		def nocallback(*a):
			# This one doesn't need error checking
			pass
		self.request("Profile: %s" % (filename,), nocallback, nocallback)
	
	
	def stop(self):
		""" Stops the daemon """
		Gio.Subprocess.new([ find_binary('scc-daemon'), "/dev/null", "stop" ], Gio.SubprocessFlags.NONE)
	
	
	def start(self, mode="start"):
		"""
		Starts the daemon and forces connection to be created immediately.
		"""
		if self.alive:
			# Just to clean up living connection
			self.alive = None
			self._on_daemon_died()
		Gio.Subprocess.new([ find_binary('scc-daemon'), "/dev/null", mode ], Gio.SubprocessFlags.NONE)
		self._connect()
	
	
	def restart(self):
		"""
		Restarts the daemon and forces connection to be created immediately.
		"""
		self.start(mode="restart")
	
	
	def lock(self, success_cb, error_cb, *what_to_lock):
		"""
		Locks physical button, axis or pad. Events from locked sources are
		sent to this client and processed using 'event' singal, until
		unlock_all() is called.
		
		Calls success_cb() on success or error_cb(error) on failure.
		"""
		what = " ".join(what_to_lock)
		self.request("Lock: %s" % (what,), success_cb, error_cb)
	
	
	def unlock_all(self):
		if self.alive:
			self.request("Unlock.", lambda *a: False, lambda *a: False)
