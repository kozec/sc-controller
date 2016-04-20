#!/usr/bin/env python2
"""
SC-Controller - DaemonManager

Starts, kills and controls sccdaemon instance.

I'd call it DaemonController normally, but having something with
full name of "Steam Controller Controller Daemon Controller" sounds
probably too crazy even for me.
"""
from __future__ import unicode_literals

from scc.gui.paths import get_daemon_path, get_daemon_socket
from gi.repository import GObject, Gio, GLib

import os, sys, logging
log = logging.getLogger("DaemonCtrlr")


class DaemonManager(GObject.GObject):
	"""
	List of signals:
		alive ()
			Emited after daemon is started or found to be alraedy running
		
		dead ()
			Emited after daemon is killed (or exits for some other reason)
		
		profile-changed (profile)
			Emited after profile is changed. Profile is filename of currently
			active profile
	"""
	
	__gsignals__ = {
			b"alive"			: (GObject.SIGNAL_RUN_FIRST, None, ()),
			b"dead"				: (GObject.SIGNAL_RUN_FIRST, None, ()),
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
				self.alive = True
				self.emit('alive')
			elif line.startswith("Current profile:"):
				profile = line.split(":", 1)[-1].strip()
				log.debug("Daemon reported profile change: %s", profile)
				self.emit('profile-changed', profile)
		# Connection is held forever to detect when daemon exits
		self.connection.get_input_stream().read_bytes_async(102400,
			1, None, self._on_read_data)
	
	
	def is_alive(self):
		""" Returns True if daemon is running """
		return self.alive
	
	
	def set_profile(self, filename):
		""" Asks daemon to change profile """
		if self.alive and self.connection is not None:
			self.connection.get_output_stream().write_all(filename.encode("utf-8") + b"\n", None)
	
	
	def stop(self):
		""" Stops the daemon """
		Gio.Subprocess.new([ get_daemon_path(), "/dev/null", "stop" ], Gio.SubprocessFlags.NONE)
	
	
	def start(self, mode="start"):
		"""
		Starts the daemon and forces connection to be created immediately.
		"""
		if self.alive:
			# Just to clean up living connection
			self.alive = None
			self._on_daemon_died()
		Gio.Subprocess.new([ get_daemon_path(), "/dev/null", mode ], Gio.SubprocessFlags.NONE)
		self._connect()
	
	
	def restart(self):
		"""
		Restarts the daemon and forces connection to be created immediately.
		"""
		self.start(mode="restart")