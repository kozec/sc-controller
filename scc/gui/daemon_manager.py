#!/usr/bin/env python3
"""
SC-Controller - DaemonManager

Starts, kills and controls sccdaemon instance.

I'd call it DaemonController normally, but having something with
full name of "Steam Controller Controller Daemon Controller" sounds
probably too crazy even for me.
"""


from scc.tools import find_binary, find_button_image, nameof
from scc.paths import get_daemon_socket
from scc.constants import SCButtons
from scc.gui import BUTTON_ORDER
from gi.repository import GObject, Gio, GLib

import os, json, logging
log = logging.getLogger("DaemonCtrl")


class DaemonManager(GObject.GObject):
	"""
	Communicates with daemon socket and provides wrappers around everything
	it can do.
	
	List of signals:
		alive ()
			Emited after daemon is started or found to be alraedy running
		
		controller-count-changed(count)
			Emited after daemon reports change in controller count, ie when
			new controller is connnected or disconnected.
			Also emited shortly after connection to daemon is initiated.
		
		dead ()
			Emited after daemon is killed (or exits for some other reason)
		
		error (description)
			Emited when daemon reports error, most likely not being able to
			access to USB dongle.
		
		event (controller, pad_stick_or_button, values)
			As 'event' signal on Controller. Allows for capturing events from
			all controllers using single signal.
		
		profile-changed (profile)
			Emited after profile set for first controller is changed.
			Profile is filename of currently active profile
		
		reconfigured()
			Emited when daemon reports change in configuration file
		
		unknown-msg (message)
			Emited when message that can't be parsed internally
			is recieved from daemon.
		
		version (ver)
			Emited daemon reports its version - usually only once per connection.
	"""
	
	__gsignals__ = {
			"alive"					: (GObject.SignalFlags.RUN_FIRST, None, ()),
			"controller-count-changed"	: (GObject.SignalFlags.RUN_FIRST, None, (int,)),
			"dead"						: (GObject.SignalFlags.RUN_FIRST, None, ()),
			"error"					: (GObject.SignalFlags.RUN_FIRST, None, (object,)),
			"event"					: (GObject.SignalFlags.RUN_FIRST, None, (object,object,object)),
			"profile-changed"			: (GObject.SignalFlags.RUN_FIRST, None, (object,)),
			"reconfigured"				: (GObject.SignalFlags.RUN_FIRST, None, ()),
			"unknown-msg"				: (GObject.SignalFlags.RUN_FIRST, None, (object,)),
			"version"					: (GObject.SignalFlags.RUN_FIRST, None, (object,)),
	}
	
	RECONNECT_INTERVAL = 5
	
	def __init__(self):
		GObject.GObject.__init__(self)
		self.alive = None
		self.connection = None
		self.connecting = False
		self.buffer = b""
		self._connect()
		self._requests = []
		self._controllers = []			# Ordered as daemon says
		self._controller_by_id = {}		# Source of memory leak
	
	
	def get_controllers(self):
		"""
		Returns list of all controllers connected to daemon.
		Value is cached locally.
		"""
		return [] + self._controllers
	
	
	def get_controller(self, controller_id, type=None):
		"""
		Returns ControllerManager instance bound to provided controller_id.
		Note that this method will return instance for any controller_id,
		even if controller with such ID is not connected to daemon.
		
		For same controller_id, there is always same instance returned.
		"""
		if controller_id not in self._controller_by_id:
			c = self._controller_by_id[controller_id] = ControllerManager(self, controller_id, type)
		else:
			c = self._controller_by_id[controller_id]
			c.set_type(type)
		return c
	
	
	def has_controller(self):
		"""
		Returns True if there is at lease one controller connected to daemon.
		"""
		return len(self._controllers) > 0
	
	
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
		except Exception as e:
			self._on_daemon_died()
			return
		self.buffer = b""
		self.connection.get_input_stream().read_bytes_async(102400,
			1, None, self._on_read_data)
	
	
	def _on_read_data(self, sc, results):
		""" Called when daemon sends some data """
		try:
			response = sc.read_bytes_finish(results)
			if response == None:
				raise Exception("No data recieved")
		except Exception as e:
			# Broken sonnection, daemon was probbaly terminated
			self._on_daemon_died()
			return
		data = response.get_data()
		if len(data) == 0:
			# Connection terminated
			self._on_daemon_died()
			return
		self.buffer += data
		while b"\n" in self.buffer:
			line, self.buffer = self.buffer.split(b"\n", 1)
			line = line.decode("utf-8")
			if line.startswith("Version:"):
				version = line.split(":", 1)[-1].strip()
				log.debug("Connected to daemon, version %s", version)
				self.emit('version', version)
			elif line.startswith("Ready."):
				log.debug("Daemon is ready.")
				self.alive = True
				self.emit('alive')
			elif line.startswith("OK."):
				if len(self._requests) > 0:
					success_cb, error_cb = self._requests[0]
					self._requests = self._requests[1:]
					success_cb()
			elif line.startswith("Fail:"):
				if len(self._requests) > 0:
					success_cb, error_cb = self._requests[0]
					self._requests = self._requests[1:]
					error_cb(line[5:].strip())
			elif line.startswith("Controller:"):
				controller_id, type, flags, config_file = line[11:].strip().split(" ", 3)
				c = self.get_controller(controller_id, type)
				c._connected = True
				c._type = type
				c._flags = int(flags)
				c._config_file = None if config_file in ("", "None") else config_file
				while c in self._controllers:
					self._controllers.remove(c)
				self._controllers.append(c)
			elif line.startswith("Controller profile:"):
				controller_id, profile = line[19:].strip().split(" ", 1)
				c = self.get_controller(controller_id)
				c._profile = profile.strip()
				c.emit("profile-changed", c._profile)
				log.debug("Daemon reported profile change for %s: %s", controller_id, c._profile)
			elif line.startswith("Controller Count:"):
				count = int(line[17:])
				if count == 0:
					old, self._controllers = self._controllers, []
				else:
					old, self._controllers = self._controllers, self._controllers[-count:]
				self.emit('controller-count-changed', count)
				for c in old:
					if c not in self._controllers:
						c.emit('lost')
			elif line.startswith("Event:"):
				data = line[6:].strip().split(" ")
				c = self.get_controller(data[0])
				c.emit('event', data[1], [ int(float(x)) for x in data[2:] ])
				self.emit('event', c, data[1], [ int(float(x)) for x in data[2:] ])
			elif line.startswith("Error:"):
				error = line.split(":", 1)[-1].strip()
				self.alive = True
				log.debug("Daemon reported error '%s'", error)
				self.emit('error', error)
			elif line.startswith("Current profile:"):
				self._profile = line.split(":", 1)[-1].strip()
				self.emit('profile-changed', self._profile)
			elif line.startswith("Reconfigured."):
				self.emit('reconfigured')
			elif line.startswith("PID:") or line == "SCCDaemon":
				# ignore
				pass
			else:
				self.emit('unknown-msg', line)
		# Connection is held forever to detect when daemon exits
		if self.connection:
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
	
	
	@classmethod
	def nocallback(*a):
		""" Used when request doesn't needs callback """
		pass
	
	
	def set_profile(self, filename):
		""" Asks daemon to change 1st controller profile """
		self.request("Controller.\nProfile: %s" % (filename,),
				DaemonManager.nocallback, DaemonManager.nocallback)
	
	
	def reconfigure(self):
		""" Asks daemon reload configuration file """
		self.request("Reconfigure.", DaemonManager.nocallback,
				DaemonManager.nocallback)
	
	
	def rescan(self):
		""" Asks daemon to rescan for new devices """
		self.request("Rescan.", DaemonManager.nocallback,
				DaemonManager.nocallback)
	
	
	def stop(self):
		""" Stops the daemon """
		Gio.Subprocess.new([ find_binary('scc-daemon'), "/dev/null", "stop" ], Gio.SubprocessFlags.NONE)
		self.connecting = False
	
	
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
		GLib.timeout_add_seconds(10, self._check_connected)
	
	
	def restart(self):
		"""
		Restarts the daemon and forces connection to be created immediately.
		"""
		self.start(mode="restart")
	
	
	def _check_connected(self):
		if not self.alive:
			log.debug("Started daemon but connection is not ready")
			self.emit('error', "CANT_SUMMON_THE_DAEMON")
		return False


class ControllerManager(GObject.GObject):
	"""
	Represents controller connected to daemon.
	Returned by DaemonManager.get_controller or DaemonManager.get_controllers.
	
	List of signals:
		event (pad_stick_or_button, values)
			Emited when pad, stick or button is locked using lock() method
			and position or pressed state of that button is changed
		
		lost()
			Emited when controller is disconnected or turned off
		
		profile-changed (profile)
			Emited after profile for controller is changed.
			Profile is filename of currently active profile
	"""
	
	__gsignals__ = {
			"event"			: (GObject.SignalFlags.RUN_FIRST, None, (object,object)),
			"lost"				: (GObject.SignalFlags.RUN_FIRST, None, ()),
			"profile-changed"	: (GObject.SignalFlags.RUN_FIRST, None, (object,)),
	}
	
	DEFAULT_ICONS = [ "A", "B", "X", "Y", "BACK", "C", "START",
		"LB", "RB", "LT", "RT", "STICK", "LPAD", "RPAD", "RGRIP", "LGRIP", "DOTS" ]
	# ^^ those are icon names
	
	def __init__(self, daemon_manager, controller_id, controller_type):
		GObject.GObject.__init__(self)
		self._dm = daemon_manager
		self._controller_id = controller_id
		self._type = controller_type
		self._config_file = None
		self._connected = False
		self._profile = None
		self._type = None
		self._flags = 0
	
	
	def __repr__(self):
		return "<ControllerManager for ID '%s'>" % (self._controller_id,)
	
	
	def _send_id(self):
		"""
		Sends Controller: message to daemon, so next message goes to correct
		controller.
		"""
		self._dm.request("Controller: %s" % (self._controller_id,),
				DaemonManager.nocallback, DaemonManager.nocallback)
	
	
	def is_connected(self):
		"""
		Returns True, if controller is still connected to daemon.
		Value is cached locally.
		"""
		return self._connected
	
	
	def get_type(self):
		"""
		Returns string identifier of controller driver.
		
		Value is cached locally, but may be None before controller is connected.
		"""
		return self._type
	
	def set_type(self, type):
		"""
		Sets type, if none is yet set.
		"""
		if self._type is None:
			self._type = type
	
	def get_flags(self):
		"""
		Returns flags for this controller. See ControllerFlags enum for more info.
		
		Value is cached locally and returns 0 until controller is connected.
		"""
		return self._flags
	
	
	def get_id(self):
		""" Returns ID of this controller. Value is cached locally. """
		return self._controller_id
	
	
	def get_gui_config_file(self):
		"""
		Returns file name of json file that GUI can use to load more data about
		controller (background image, button images, available buttons and
		axes, etc...) File name may be absolute path or just name of file in
		/usr/share/scc
		
		Returns None if there is no configuration file (GUI will use
		defaults in such case)
		"""
		return self._config_file
	
	
	def load_gui_config(self, default_path):
		"""
		As get_gui_config_file, but returns loaded and parsed config.
		Returns None if config cannot be loaded.
		"""
		filename = self.get_gui_config_file()
		if filename:
			if "/" not in filename:
				filename = os.path.join(default_path, filename)
			try:
				data = json.loads(open(filename, "r").read()) or None
				return data
			except Exception as e:
				log.exception(e)
		return None
	
	@staticmethod
	def get_button_icon(config, button, prefer_bw=False):
		"""
		For config returned by load_gui_config() and SCButton constant,
		returns icon filename assigned to that button in controller config or
		default if config is invalid or button unassigned.
		"""
		return find_button_image(
			ControllerManager.get_button_name(config, button),
			prefer_bw=prefer_bw
		)
	
	
	@staticmethod
	def get_button_name(config, button):
		"""
		As get_button_icon, but returns icon name instead of filename.
		"""
		name = nameof(button)
		index = -1
		try:
			if type(button) is str:
				button = SCButtons.__members__[button]
			index = BUTTON_ORDER.index(button)
			name = ControllerManager.DEFAULT_ICONS[index]
			name = config['gui']['buttons'][index]
		except: pass
		return name
	
	
	def get_profile(self):
		""" Returns profile set for this controller. Value is cached locally. """
		return self._profile
	
	
	def lock(self, success_cb, error_cb, *what_to_lock):
		"""
		Locks physical button, axis or pad. Events from locked sources are
		sent to this client and processed using 'event' singal, until
		unlock_all() is called.
		
		Calls success_cb() on success or error_cb(error) on failure.
		"""
		what = " ".join(what_to_lock)
		self._send_id()
		self._dm.request("Lock: %s" % (what,), success_cb, error_cb)
	
	
	def set_led_level(self, value):
		"""
		Sets brightness of controller led.
		"""
		self._send_id()
		self._dm.request("Led: %s" % (int(value),), DaemonManager.nocallback,
			DaemonManager.nocallback)
	
	
	def set_profile(self, filename):
		""" Asks daemon to change this controller profile """
		self._send_id()
		self._dm.request("Profile: %s" % (filename,),
				DaemonManager.nocallback, DaemonManager.nocallback)
	
	
	def turnoff(self):
		""" Asks daemon to turn off this controller """
		self._send_id()
		self._dm.request("Turnoff.",
				DaemonManager.nocallback, DaemonManager.nocallback)
	
	
	def feedback(self, position, amplitude):
		""" Generates feedback effect on controller """
		self._send_id()
		self._dm.request("Feedback: %s %s" % (position, amplitude),
				DaemonManager.nocallback, DaemonManager.nocallback)
	
	
	def observe(self, success_cb, error_cb, *what_to_lock):
		"""
		Enables observing on physical button, axis or pad.
		Events from observed sources are sent to this client and processed
		using 'event' singal, until unlock_all() is called.
		
		Calls success_cb() on success or error_cb(error) on failure.
		"""
		what = " ".join(what_to_lock)
		self._send_id()
		self._dm.request("Observe: %s" % (what,), success_cb, error_cb)
	
	
	def replace(self, success_cb, error_cb, what, action):
		"""
		Temporally replaces action on physical button, axis or pad,
		until unlock_all() is called.
		
		Calls success_cb() on success or error_cb(error) on failure.
		"""
		actionstr = action.to_string().replace("\n", " ")
		self._dm.request("Replace: %s %s" % (what, actionstr),
				success_cb, error_cb)
	
	
	def unlock_all(self):
		if self._dm.alive:
			self._send_id()
			self._dm.request("Unlock.", lambda *a: False, lambda *a: False)
