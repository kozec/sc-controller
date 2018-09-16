#!/usr/bin/env python2
"""
SC-Controller - Daemon class
"""
from __future__ import unicode_literals

from scc.lib import xwrappers as X
from scc.lib import xinput
from scc.lib.daemon import Daemon
from scc.constants import SCButtons, DAEMON_VERSION, HapticPos
from scc.constants import LEFT, RIGHT, STICK, CPAD
from scc.tools import find_profile, find_menu, nameof, shsplit, shjoin
from scc.uinput import CannotCreateUInputException
from scc.tools import set_logging_level, find_binary, clamp
from scc.device_monitor import create_device_monitor
from scc.custom import load_custom_module
from scc.gestures import GestureDetector
from scc.parser import TalkingActionParser
from scc.controller import HapticData
from scc.scheduler import Scheduler
from scc.menu_data import MenuData
from scc.profile import Profile
from scc.actions import Action
from scc.config import Config
from scc.poller import Poller
from scc.mapper import Mapper
from scc import drivers

from SocketServer import UnixStreamServer, ThreadingMixIn, StreamRequestHandler
import os, sys, pkgutil, signal, time, json, logging
import threading, traceback, subprocess
log = logging.getLogger("SCCDaemon")
tlog = logging.getLogger("Socket Thread")

class ThreadingUnixStreamServer(ThreadingMixIn, UnixStreamServer): daemon_threads = True


class SCCDaemon(Daemon):
	
	def __init__(self, piddile, socket_file):
		set_logging_level(True, True)
		Daemon.__init__(self, piddile)
		Config()					# Generates ~/.config/scc and default config if needed
		self.started = False
		self.exiting = False
		self.socket_file = socket_file
		self.poller = Poller()
		self.dev_monitor = create_device_monitor(self)
		self.scheduler = Scheduler()
		self.xdisplay = None
		self.sserver = None			# UnixStreamServer instance
		self.errors = []
		self.alone = False			# Set by launching script from --alone flag
		self.custom_py_loaded = False
		self.osd_daemon = None
		self.default_profile = None
		self.autoswitch_daemon = None
		# TODO: Use osd_ids for all menus
		self.osd_ids = {}
		self.controllers = []
		self.mainloops = [ self.poller.poll, self.scheduler.run ]
		self.rescan_cbs = [ ]
		self.on_exit_cbs = []
		self.subprocs = []
		self.lock = threading.Lock()
		self.default_mapper = None
		self.free_mappers = [ ]
		self.clients = set()
		self.cwd = os.getcwd()
	
	
	def init_drivers(self):
		"""
		Searchs and initializes all controller drivers.
		See __init__.py in scc.drivers.
		"""
		log.debug("Initializing drivers...")
		cfg = Config()
		self._to_start = set()  # del-eted later by start_drivers
		to_init = []
		for importer, modname, ispkg in pkgutil.walk_packages(path=drivers.__path__, onerror=lambda x: None):
			if not ispkg and modname != "driver":
				if modname == "usb" or cfg["drivers"].get(modname):
					# 'usb' driver has to be always active
					mod = getattr(__import__('scc.drivers.%s' % (modname,)).drivers, modname)
					if hasattr(mod, "init"):
						to_init.append(mod)
				else:
					log.warn("Skipping disabled driver '%s'", modname)
		
		from scc.drivers import MOD_INIT_ORDER as order
		index_fn = lambda n: order.index(n) if n in order else 1024
		sort_fn = lambda m: index_fn(m.__name__)
		
		for mod in sorted(to_init, key=sort_fn):
			if getattr(mod, "init")(self, cfg):
				if hasattr(mod, "start"):
					self._to_start.add(getattr(mod, "start"))
	
	
	def init_default_mapper(self):
		"""
		default_mapper is persistent mapper assigned to first Controller instance.
		Even if all controllers are removed, this mapper stays active. This is
		needed so various stuff (mainlg GUI) doesn't need to check if there is
		any controller connected all the time.
		"""
		# But, despite all above, it's just mapper as every other :)
		return self.init_mapper()
	
	
	def set_default_profile(self, profile_file):
		"""
		Sets profile that is used for first available controller
		"""
		self.default_profile = profile_file
	
	
	def start_drivers(self):
		for s in self._to_start:
			s(self)
		del self._to_start
	
	
	def stop_drivers(self):
		for s in self.drivers_to_stop:
			s(self)
	
	
	def get_poller(self):
		""" Returns poller that can be used for polling file descriptors """
		return self.poller
	
	
	def get_device_monitor(self):
		"""
		Returns device monitor that can be used to listen for device adding and removals
		"""
		return self.dev_monitor
	
	
	def get_scheduler(self):
		""" Returns scheduler instance """
		return self.scheduler
	
	
	def add_mainloop(self, fn):
		"""
		Adds function that is called in every mainloop iteration.
		Can be called only durring initialization, in driver 'init' method.
		"""
		if fn not in self.mainloops:
			self.mainloops.append(fn)
	
	
	def remove_mainloop(self, fn):
		"""
		Removes function added by add_mainloop
		"""
		if fn in self.mainloops:
			self.mainloops.remove(fn)
	
	
	def add_on_exit(self, fn):
		"""
		Adds function that is called just before daemon is stopped.
		Usefull for cleanup.
		"""
		if fn not in self.on_exit_cbs:
			self.on_exit_cbs.append(fn)
	
	
	def add_on_rescan(self, fn):
		"""
		Adds function that is called when `Rescan.` message is recieved.
		"""
		if fn not in self.on_exit_cbs:
			self.rescan_cbs.append(fn)
	
	
	def _set_profile(self, mapper, filename):
		# Called from socket server thread
		p = Profile(TalkingActionParser())
		p.load(filename).compress()
		self.profile_file = filename
		
		if mapper.profile.gyro and not p.gyro:
			# Turn off gyro sensor that was enabled but is no longer needed
			if mapper.get_controller():
				log.debug("Turning gyrosensor OFF")
				mapper.get_controller().set_gyro_enabled(False)
		elif not mapper.profile.gyro and p.gyro:
			# Turn on gyro sensor that was turned off, if profile has gyro action set
			if mapper.get_controller():
				log.debug("Turning gyrosensor ON")
				mapper.get_controller().set_gyro_enabled(True)
		# Cancel everything
		mapper.cancel_all()
		# Release all buttons
		mapper.release_virtual_buttons()
		# Reset mouse (issue #222)
		mapper.mouse.reset()
		
		# This last line kinda depends on GIL...
		mapper.profile = p
		# Re-apply all locks
		for c in self.clients:
			c.reaply_locks(self, mapper)
		if mapper.get_controller():
			self.send_profile_info(mapper.get_controller(), self._send_to_all)
		else:
			self.send_profile_info(None, self._send_to_all, mapper=mapper)
	
	
	def _send_to_all(self, message_str):
		"""
		Sends message to all connect clients.
		Should be called while lock is acquired.
		Message should be utf-8 encoded str.
		"""
		for client in self.clients:
			try:
				client.wfile.write(message_str)
			except: pass
	
	
	def on_sa_turnoff(self, mapper, action):
		""" Called when 'turnoff' action is used """
		if mapper.get_controller():
			mapper.get_controller().turnoff()
	
	
	def on_sa_restart(self, *a):
		""" Called when 'restart' action is used """
		with self.lock:
			for c in self.clients:
				c.close()
		os.system("%s %s None restart &" % ( sys.executable, sys.argv[0] ))
	
	
	def on_sa_led(self, mapper, action):
		""" Called when 'led' action is used """
		if mapper.get_controller():
			mapper.get_controller().set_led_level(action.brightness)
	
	
	def on_sa_shell(self, mapper, action):
		""" Called when 'shell' action is used """
		os.system((action.command + " &").encode('utf-8'))
	
	
	def on_sa_gestures(self, mapper, action, x, y, what):
		""" Called when 'gestures' action is used """
		# TODO: Take up_direction from action
		gd = None
		with self.lock:
			if action.osd_enabled and self.osd_daemon:
				# When OSD is enabled, gesture detection is handled
				# by scc-osd-daemon.
				self.osd_daemon.gesture_action = action
				self._osd('gesture',
					"--controller", mapper.get_controller().get_id(),
				 	'--control-with', what)
				log.debug("Gesture detection request sent to scc-osd-daemon")
			else:
				# Otherwise it is handled internally
				up_direction = 0
				gd = self._start_gesture(
					mapper,
					what,
					up_direction,
					lambda gesture_string : action.gesture(mapper, gesture_string)
				)
		if gd:
			gd.enable()
			log.debug("Gesture detection started on %s", what)
			gd.whole(mapper, x, y, what)
	
	
	def _osd(self, *data):
		"""
		Has to be called with self.lock held.
		Returns True on success.
		"""
		# Pre-format data
		data = b"OSD: %s\n" % (shjoin(data) ,)
		
		# Check if scc-osd-daemon is available
		if not self.osd_daemon:
			log.warning("Cannot show OSD; there is no scc-osd-daemon registered")
			return False
		# Send request
		try:
			self.osd_daemon.wfile.write(data)
			self.osd_daemon.wfile.flush()
		except Exception, e:
			log.error("Failed to display OSD: %s", e)
			self.osd_daemon = None
			return False
		return True
	
	
	def on_sa_osd(self, mapper, action):
		""" Called when 'osd' action is used """
		with self.lock:
			self._osd('message', '-t', action.timeout, action.text)
	
	
	def on_sa_area(self, mapper, action, x1, y1, x2, y2):
		""" Called when *AreaAction has OSD enabled """
		with self.lock:
			self._osd('area', '-x', x1, '-y', y1, '--width', x2-x1, '--height', y2-y1)
	
	
	def on_sa_clear_osd(self, *a):
		with self.lock:
			self._osd('clear')
	
	
	def on_sa_keyboard(self, mapper, action):
		""" Called when 'keyboard' action is used """
		with self.lock:
			self._osd('keyboard')
	
	
	def on_sa_menu(self, mapper, action, *pars):
		""" Called when 'menu' action is used """
		p = [ action.MENU_TYPE ]
		if mapper.get_controller():
			p += [ "--controller", mapper.get_controller().get_id() ]
		if "." in action.menu_id:
			path = find_menu(action.menu_id)
			if not path:
				log.error("Cannot show menu: Menu '%s' not found", action.menu_id)
				return
			p += [ "--from-file", path ]
		else:
			p += [ "--from-profile", mapper.profile.get_filename(), action.menu_id ]
		p += list(pars)
		
		with self.lock:
			self._osd(*p)
	
	on_sa_gridmenu = on_sa_menu
	
	
	def on_sa_dialog(self, mapper, action, *pars):
		# Replace actions with id, title pairs
		data = []
		self.osd_ids = {}
		for x in pars:
			if isinstance(x, Action):
				id = str(hash(x))
				self.osd_ids[id] = x.strip()
				data += [ id, x.describe(Action.AC_MENU) ]
			else:
				data.append(x)
		
		with self.lock:
			self._osd("dialog", *data)
	
	
	def on_sa_profile(self, mapper, action):
		""" Called when 'profile' action is used """
		name = action.profile
		if "/" in name:
			# Small sanity check
			log.error("Cannot load profile: Profile '%s' not found", name)
			return
		path = find_profile(name)
		if path:
			with self.lock:
				try:
					self._set_profile(mapper, path)
					log.info("Loaded profile '%s'", name)
				except Exception, e:
					log.exception(e)
			return
		log.error("Cannot load profile: Profile '%s' not found", name)
	
	
	def on_start(self):
		os.chdir(self.cwd)
	
	
	def on_controller_status(self, sc, onoff):
		if onoff:
			log.debug("Controller turned ON")
		else:
			log.debug("Controller turned OFF")
	
	
	def sigterm(self, *a):
		self.exiting = True
		for fn in self.on_exit_cbs:
			fn(self)
		for d in (self.osd_daemon, self.autoswitch_daemon):
			if d: d.wfile.close()
		self.osd_daemon, self.autoswitch_daemon = None, None
		for p in self.subprocs:
			p.kill()
		self.subprocs = []
		sys.exit(0)
	
	
	def connect_x(self):
		""" Creates connection to X Server """
		if "WAYLAND_DISPLAY" in os.environ:
			log.warning("Wayland detected. Disabling X11 support, some functionality will be unavailable")
			self.xdisplay = None
			return
		if "DISPLAY" not in os.environ:
			log.warning("DISPLAY env variable not set. Some functionality will be unavailable")
			self.xdisplay = None
			return
		
		self.xdisplay = X.open_display(os.environ["DISPLAY"])
		if self.xdisplay:
			log.debug("Connected to XServer %s", os.environ["DISPLAY"])
			
			for c in self.controllers:
				if c.get_mapper():
					c.get_mapper().set_xdisplay(self.xdisplay)
			for m in self.free_mappers:
				m.set_xdisplay(self.xdisplay)
			if not self.alone:
				self.subprocs.append(Subprocess("scc-osd-daemon", True))
				if len(Config()["autoswitch"]):
					# Start scc-autoswitch-daemon only if there are some switch rules defined
					self.subprocs.append(Subprocess("scc-autoswitch-daemon", True))
		else:
			log.warning("Failed to connect to XServer. Some functionality will be unavailable")
			self.xdisplay = None
	
	
	def init_mapper(self):
		"""
		Setups new mapper instance.
		"""
		try:
			mapper = Mapper(Profile(TalkingActionParser()),
					self.scheduler, poller=self.poller)
		except CannotCreateUInputException, e:
			# Most likely UInput is not available
			# Create mapper with all virtual devices set to Dummies.
			log.exception(e)
			self.add_error("uinput", str(e))
			mapper = Mapper(Profile(TalkingActionParser()),
				self.scheduler, keyboard=None, mouse=None, gamepad=False)
		
		mapper.set_special_actions_handler(self)
		mapper.set_xdisplay(self.xdisplay)
		mapper.schedule(1.0, self.fix_xinput)
		return mapper
	
	
	def fix_xinput(self, mapper):
		name = mapper.get_gamepad_name()
		if self.xdisplay and Config()["fix_xinput"] and name:
			# Three conditions: X has to be available, 'fix_xinput' must
			# be enabled in config and controller should not be dummy
			# (should have a name)
			try:
				for d in xinput.get_devices():
					if d.get_name() == name:
						if d.is_pointer() and d.is_slave():
							d.float()
			except OSError, e:
				# Most likely 'xinput' executable not found
				log.warn("Failed to deatach gamepad from xinput master: %s", e)
	
	
	def load_default_profile(self, mapper=None):
		mapper = mapper or self.default_mapper
		if self.default_profile == None:
			try:
				self.default_profile = find_profile(Config()["recent_profiles"][0])
			except:
				# Broken config is not reason to fail here
				pass
		try:
			mapper.profile.load(self.default_profile).compress()
		except Exception, e:
			log.warning("Failed to load profile. Starting with no mappings.")
			log.warning("Reason: %s", e)
	
	
	def add_controller(self, c):
		if len(self.free_mappers) > 0:
			# Reuse already created mapper, so SCC will not spam system
			# with fake devices
			mapper, self.free_mappers = self.free_mappers[0], self.free_mappers[1:]
			if mapper != self.default_mapper:
				log.debug("Reused mapper %s for %s", mapper, c)
		else:
			# New controller, but no mapper created
			mapper = self.init_mapper()
			self.load_default_profile(mapper)
		mapper.set_controller(c)
		c.set_mapper(mapper)
		if mapper == self.default_mapper:
			log.debug("Assigned default_mapper to %s", c)
		if mapper.profile.gyro:
			log.debug("Turning gyrosensor ON")
			c.set_gyro_enabled(True)
		
		c.apply_config(Config().get_controller_config(c.get_id()))
		self.controllers.append(c)
		log.debug("Controller added: %s", c)
		with self.lock:
			self.send_controller_list(self._send_to_all)
			self.send_all_profiles(self._send_to_all)
	
	
	def remove_controller(self, c):
		mapper = c.mapper
		if mapper:
			mapper.release_virtual_buttons()
		c.disconnected()
		
		with self.lock:
			while c in self.controllers:
				self.controllers.remove(c)
			log.debug("Controller removed: %s", c)
			
			if mapper == self.default_mapper and len(self.controllers) > 0:
				# Special case, default_mapper should be always
				# assigned to something, so if controller with default_mapper
				# is disconnected, it's reassigned to next available controller
				swap_c = self.controllers[0]
				swap_mapper = swap_c.get_mapper()
				swap_mapper.set_controller(None)
				swap_c.set_mapper(mapper)
				mapper.set_controller(swap_c)
				self.free_mappers.append(swap_mapper)
				log.debug("Reassigned default_mapper to %s", swap_c)
			else:
				c.set_mapper(None)
				if mapper:
					mapper.set_controller(None)
					self.free_mappers.append(mapper)
			self.send_controller_list(self._send_to_all)
	
	
	def get_active_ids(self):
		""" Returns iterable with IDs of all active controllers """
		return [ x.get_id() for x in self.controllers ]
	
	
	def add_error(self, id, error):
		"""
		Adds error (string) to report. Used when USB driver reports that device
		cannot be accessed or when UInput is not available.
		
		Every error has id that can be later used to remove it from list to
		indicate that error has been resolved.
		"""
		with self.lock:
			self.errors.append(( id, error ))
			self._send_to_all(("Error: %s\n" % (error,)).encode("utf-8"))
	
	
	def remove_error(self, id):
		"""
		Removes error added with 'add_error'. If such error cannot be found,
		does nothing.
		
		When last error is removed, this method automatically sends "Ready."
		message to indicate that daemon is ready to serve clients.
		"""
		with self.lock:
			self.errors = [ (_id, error) for (_id, error) in self.errors if _id != id ]
			if len(self.errors) == 0:
				self._send_to_all(b"Ready.\n")
	
	
	def send_controller_list(self, method):
		"""
		Sends controller count and list of controllers using provided method
		"""
		for c in self.controllers:
			method(("Controller: %s %s %s %s\n" % (
				c.get_id(), c.get_type(), c.flags, c.get_gui_config_file()
			)).encode("utf-8"))
		method(("Controller Count: %s\n" % (len(self.controllers),)).encode("utf-8"))
	
	
	def send_profile_info(self, controller, method, mapper=None):
		"""
		Sends info about current profile using provided method.
		Returns True if mapper is default_mapper.
		"""
		mapper = mapper if mapper else controller.mapper
		if controller:
			method(("Controller profile: %s %s\n" % (
				controller.get_id(),
				mapper.profile.get_filename()
			)).encode("utf-8"))
		if mapper == self.default_mapper:
			method(("Current profile: %s\n" % (
				mapper.profile.get_filename(),
			)).encode("utf-8"))
			return True
		return False
	
	
	def send_all_profiles(self, method):
		"""
		Sends info about all profiles assigned to all
		controllers using provided method.
		"""
		# As special case, at least default_mapper profile has to be sent always
		default_sent = False
		for c in self.controllers:
			default_sent = self.send_profile_info(c, method) or default_sent
		if not default_sent:
			self.send_profile_info(None, method, mapper=self.default_mapper)
	
	
	def run(self):
		log.debug("Starting SCCDaemon...")
		signal.signal(signal.SIGTERM, self.sigterm)
		self.init_drivers()
		self.dev_monitor.start()
		load_custom_module(log)
		self.default_mapper = self.init_default_mapper()
		self.free_mappers.append(self.default_mapper)
		self.load_default_profile()
		self.lock.acquire()
		self.start_listening()
		self.connect_x()
		self.lock.release()
		self.start_drivers()
		self.dev_monitor.rescan()
		
		while True:
			for fn in self.mainloops:
				fn()
	
	
	def start_listening(self):
		if os.path.exists(self.socket_file):
			os.unlink(self.socket_file)
		instance = self
		
		class SSHandler(StreamRequestHandler):
			def handle(self):
				instance._sshandler(self.connection, self.rfile, self.wfile)
		
		self.sserver = ThreadingUnixStreamServer(self.socket_file, SSHandler)
		t = threading.Thread(target=self.sserver.serve_forever)
		t.daemon = True
		t.start()
		os.chmod(self.socket_file, 0600)
		log.debug("Created control socket %s", self.socket_file)
	
	
	def _start_gesture(self, mapper, what, up_angle, callback):
		"""
		Starts gesture detection on specified pad.
		Calls callback with gesture string when finished.
		
		Should be called with lock held.
		"""
		gd = None
		
		def cb(detector, gesture):
			# This callback is expected to be called with lock held
			with self.lock:
				self._apply(mapper, what, lambda a : a.original_action)
			log.debug("Gesture detected on %s: %s", what, gesture)
			callback(gesture)
		
		def set(action):
			# ObservingAction should be above GestureDetector
			if isinstance(action, ObservingAction):
				gd.original_action = action.original_action
				action.original_action = gd
				return action
			else:
				gd.original_action = action
				return gd
		
		gd = GestureDetector(up_angle, cb)
		self._apply(mapper, what, set)
		return gd	
	
	
	def _sshandler(self, connection, rfile, wfile):
		with self.lock:
			client = Client(connection, self.default_mapper, rfile, wfile)
			self.clients.add(client)
			wfile.write(b"SCCDaemon\n")
			wfile.write(("Version: %s\n" % (DAEMON_VERSION,)).encode("utf-8"))
			wfile.write(("PID: %s\n" % (os.getpid(),)).encode("utf-8"))
			self.send_controller_list(wfile.write)
			self.send_all_profiles(wfile.write)
			if len(self.errors) == 0:
				wfile.write(b"Ready.\n")
			else:
				for id, error in self.errors:
					wfile.write(("Error: %s\n" % (error,)).encode("utf-8"))
		
		while True:
			try:
				line = rfile.readline()
			except Exception:
				# Connection terminated
				break
			if len(line) == 0: break
			if len(line.strip("\t\n ")) > 0:
				self._handle_message(client, line.strip("\n"))
		
		with self.lock:
			client.unlock_actions(self)
			if self.osd_daemon == client:
				log.info("scc-osd-daemon lost")
				self.osd_daemon = None
			if self.autoswitch_daemon == client:
				log.info("scc-autoswitch-daemon lost")
				self.autoswitch_daemon = None
			self.clients.remove(client)
	
	
	def _handle_message(self, client, message):
		"""
		Handles message recieved from client.
		"""
		if message.startswith("Profile:"):
			with self.lock:
				try:
					filename = message[8:].decode("utf-8").strip("\t ")
					self._set_profile(client.mapper, filename)
					log.info("Loaded profile '%s'", filename)
					client.wfile.write(b"OK.\n")
				except Exception, e:
					exc = traceback.format_exc()
					log.exception(e)
					tb = unicode(exc).encode("utf-8").encode('string_escape')
					client.wfile.write(b"Fail: " + tb + b"\n")
		elif message.startswith("OSD:"):
			if not self.osd_daemon:
				client.wfile.write(b"Fail: Cannot show OSD; there is no scc-osd-daemon registered\n")
			else:
				try:
					text = message[5:].decode("utf-8").strip("\t ")
					with self.lock:
						if not self._osd("message", text):
							raise Exception()
					client.wfile.write(b"OK.\n")
				except Exception:
					client.wfile.write(b"Fail: cannot display OSD\n")
		elif message.startswith("Feedback:"):
			try:
				position, amplitude = message[9:].strip().split(" ", 2)
				data = HapticData(
					getattr(HapticPos, position.strip(" \t\r")),
					int(amplitude)
				)
				if client.mapper.get_controller():
					client.mapper.get_controller().feedback(data)
				client.wfile.write(b"OK.\n")
			except Exception, e:
				log.exception(e)
				client.wfile.write(b"Fail: %s\n" % (e,))
		elif message.startswith("Controller."):
			with self.lock:
				client.mapper = self.default_mapper
				client.wfile.write(b"OK.\n")
		elif message.startswith("Controller:"):
			with self.lock:
				try:
					controller_id = message[11:].strip()
					for c in self.controllers:
						if c.get_id() == controller_id:
							client.mapper = c.get_mapper()
							client.wfile.write(b"OK.\n")
							break
					else:
						raise Exception("goto fail")
				except Exception, e:
					client.wfile.write(b"Fail: no such controller\n")
		elif message.startswith("State."):
			if Config()["enable_sniffing"]:
				client.wfile.write(b"State: %s\n" % (str(client.mapper.state), ))
			else:
				log.warning("Refused 'State' request: Sniffing disabled")
				client.wfile.write(b"Fail: Sniffing disabled.\n")
		elif message.startswith("Led:"):
			try:
				number = int(message[4:])
				number = clamp(0, number, 100)
			except Exception, e:
				client.wfile.write(b"Fail: %s\n" % (e,))
				return
			if client.mapper.get_controller():
				client.mapper.get_controller().set_led_level(number)
		elif message.startswith("Observe:"):
			if Config()["enable_sniffing"]:
				to_observe = [ x for x in message.split(":", 1)[1].strip(" \t\r").split(" ") ]
				with self.lock:
					for l in to_observe:
						client.observe_action(self, SCCDaemon.source_to_constant(l))
					client.wfile.write(b"OK.\n")
			else:
				log.warning("Refused 'Observe' request: Sniffing disabled")
				client.wfile.write(b"Fail: Sniffing disabled.\n")
		elif message.startswith("Replace:"):
			try:
				l, actionstr = message.split(":", 1)[1].strip(" \t\r").split(" ", 1)
				action = TalkingActionParser().restart(actionstr).parse().compress()
			except Exception, e:
				e = unicode(e).encode("utf-8").encode('string_escape')
				client.wfile.write(b"Fail: failed to parse: " + e + "\n")
				return
			with self.lock:
				try:
					if not self._can_lock_action(client.mapper, SCCDaemon.source_to_constant(l)):
						client.wfile.write(b"Fail: Cannot lock " + l.encode("utf-8") + b"\n")
						return
				except ValueError, e:
					tb = unicode(traceback.format_exc()).encode("utf-8").encode('string_escape')
					client.wfile.write(b"Fail: " + tb + b"\n")
					return
				client.replace_action(self, SCCDaemon.source_to_constant(l), action)
				client.wfile.write(b"OK.\n")
		elif message.startswith("Lock:"):
			to_lock = [ x for x in message.split(":", 1)[1].strip(" \t\r").split(" ") ]
			with self.lock:
				try:
					for l in to_lock:
						if not self._can_lock_action(client.mapper, SCCDaemon.source_to_constant(l)):
							client.wfile.write(b"Fail: Cannot lock " + l.encode("utf-8") + b"\n")
							return
				except ValueError, e:
					tb = unicode(traceback.format_exc()).encode("utf-8").encode('string_escape')
					client.wfile.write(b"Fail: " + tb + b"\n")
					return
				for l in to_lock:
					client.lock_action(self, SCCDaemon.source_to_constant(l))
				client.wfile.write(b"OK.\n")
		elif message.startswith("Unlock."):
			with self.lock:
				client.unlock_actions(self)
				client.wfile.write(b"OK.\n")
		elif message.startswith("Reconfigure."):
			with self.lock:
				# Load config
				cfg = Config()
				# Reconfigure connected controllers
				for c in self.controllers:
					c.apply_config(cfg.get_controller_config(c.get_id()))
				# Start or stop scc-autoswitch-daemon as needed
				need_autoswitch_daemon = len(cfg["autoswitch"]) > 0
				if need_autoswitch_daemon and self.xdisplay and not self.autoswitch_daemon:
					self.subprocs.append(Subprocess("scc-autoswitch-daemon", True))
				elif not need_autoswitch_daemon and self.autoswitch_daemon:
					self._remove_subproccess("scc-autoswitch-daemon")
					self.autoswitch_daemon.close()
					self.autoswitch_daemon = None
				# Respond
				try:
					client.wfile.write(b"OK.\n")
					self._send_to_all("Reconfigured.\n".encode("utf-8"))
				except:
					pass
		elif message.startswith("Rescan."):
			cbs = []
			with self.lock:
				cbs += self.rescan_cbs
				# Respond first
				try:
					client.wfile.write(b"OK.\n")
				except:
					pass
			# Do stuff later
			# (this cannot be done while self.lock is held, as creating new
			# controller would create race condition)
			for cb in self.rescan_cbs:
				try:
					cb()
				except Exception, e:
					log.exception(e)
			# dev_monitor rescan has to be last to run
			try:
				self.dev_monitor.rescan()
			except Exception, e:
				log.exception(e)

		elif message.startswith("Turnoff."):
			with self.lock:
				if client.mapper.get_controller():
					client.mapper.get_controller().turnoff()
				else:
					for c in self.controllers:
						c.turnoff()
				client.wfile.write(b"OK.\n")
		elif message.startswith("Gesture:"):
			try:
				what, up_angle = message[8:].strip().split(" ", 2)
				up_angle = int(up_angle)
			except Exception, e:
				tb = unicode(traceback.format_exc()).encode("utf-8").encode('string_escape')
				client.wfile.write(b"Fail: " + tb + b"\n")
				return
			with self.lock:
				client.request_gesture(self, what, up_angle)
				client.wfile.write(b"OK.\n")
		elif message.startswith("Restart."):
			self.on_sa_restart()
		elif message.startswith("Gestured:"):
			gstr = message[9:].strip()
			client.gesture_action.gesture(client.mapper, gstr)
			with self.lock:
				client.wfile.write(b"OK.\n")
		elif message.startswith("Selected:"):
			menuaction = None
			def press(mapper):
				try:
					menuaction.button_press(mapper)
					client.mapper.schedule(0.1, release)
				except Exception, e:
					log.error("Error while processing menu action")
					log.exception(e)
			def release(mapper):
				try:
					menuaction.button_release(mapper)
				except Exception, e:
					log.error("Error while processing menu action")
					log.exception(e)
			
			with self.lock:
				try:
					menu_id, item_id = shsplit(message)[1:]
					menuaction = None
					if menu_id in (None, "None"):
						menuaction = self.osd_ids[item_id]
					elif "." in menu_id:
						# TODO: Move this common place
						data = json.loads(open(menu_id, "r").read())
						menudata = MenuData.from_json_data(data, TalkingActionParser())
						menuaction = menudata.get_by_id(item_id).action
					else:
						menuaction = client.mapper.profile.menus[menu_id].get_by_id(item_id).action
					client.wfile.write(b"OK.\n")
				except:
					log.warning("Selected menu item is no longer valid.")
					client.wfile.write(b"Fail: Selected menu item is no longer valid\n")
				if menuaction:
					client.mapper.schedule(0, press)
		elif message.startswith("Register:"):
			with self.lock:
				if message.strip().endswith("osd"):
					if self.osd_daemon: self.osd_daemon.close()
					self.osd_daemon = client
					log.info("Registered scc-osd-daemon")
				elif message.strip().endswith("autoswitch"):
					if self.autoswitch_daemon: self.autoswitch_daemon.close()
					self.autoswitch_daemon = client
					log.info("Registered scc-autoswitch-daemon")
				client.wfile.write(b"OK.\n")
		else:
			client.wfile.write(b"Fail: Unknown command\n")
	
	
	def _remove_subproccess(self, binary_name):
		"""
		Removes subproccess started with specified binary name from list of
		managed subproccesses, effectively preventing daemon from
		auto-restarting it.
		
		Should be called while lock is acquired
		"""
		n = []
		for i in self.subprocs:
			if i.binary_name == binary_name:
				i.mark_killed()
			else:
				n.append(i)
		self.subprocs = n
	
	
	def _can_lock_action(self, mapper, what):
		"""
		Returns True if action assigned to axis,
		pad or button is not yet locked.
		
		Should be called while self.lock is acquired.
		"""
		# TODO: Probably move to mapper
		is_locked = (lambda a: isinstance(a, LockedAction) or
			(isinstance(a, ObservingAction) and isinstance(a.original_action, LockedAction)))
		
		if what == STICK:
			if is_locked(mapper.profile.buttons[SCButtons.STICKPRESS]):
				return False
			if is_locked(mapper.profile.stick):
				return False
			return True
		if what == SCButtons.LT:
			return not is_locked(mapper.profile.triggers[LEFT])
		if what == SCButtons.RT:
			return not is_locked(mapper.profile.triggers[RIGHT])
		if what in SCButtons:
			return not is_locked(mapper.profile.buttons[what])
		if what in (LEFT, RIGHT, CPAD):
			return not is_locked(mapper.profile.pads[what])
		return False
	
	
	def _apply(self, mapper, what, callback, *args):
		"""
		Applies callback on action that is currently set to input specified
		by 'what'. Raises ValueError if what is not known.
		
		For example, if what == STICK, executes
			mapper.profile.stick = callback(mapper.profile.stick, *args)
		"""
		if what == STICK:
			mapper.profile.stick = callback(mapper.profile.stick, *args)
		elif what == SCButtons.LT:
			mapper.profile.triggers[LEFT] = callback(mapper.profile.triggers[LEFT], *args)
		elif what == SCButtons.RT:
			mapper.profile.triggers[RIGHT] = callback(mapper.profile.triggers[RIGHT], *args)
		elif what in SCButtons:
			r = callback(mapper.profile.buttons[what], *args)
			mapper.profile.buttons[what] = r
		elif what in (LEFT, RIGHT):
			if what == LEFT:
				mapper.buttons &= ~SCButtons.LPADTOUCH
			else:
				mapper.buttons &= ~SCButtons.RPADTOUCH
			a = callback(mapper.profile.pads[what], *args)
			a.whole(mapper, 0, 0, what)
			mapper.profile.pads[what] = a
		elif what == CPAD:
			a = callback(mapper.profile.pads[what], *args)
			a.whole(mapper, 0, 0, what)
			mapper.profile.pads[what] = a
		else:
			raise ValueError("Unknown source: %s" % (what,))
	
	
	@staticmethod
	def source_to_constant(s):
		"""
		Turns string as 'A', 'LEFT' or 'ABS_X' into one of SCButtons.*,
		LEFT, RIGHT or STICK constants.
		
		Raises ValueError if passed string cannot be converted.
		
		Used when parsing `Lock: ...` message
		"""
		s = s.strip(" \t\r\n")
		if s in (STICK, LEFT, RIGHT, CPAD):
			return s
		if s == "STICKPRESS":
			# Special case, as that button is actually named STICK :(
			return SCButtons.STICKPRESS
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
		self.sigterm()


class Client(object):
	def __init__(self, connection, mapper, rfile, wfile):
		self.connection = connection
		self.rfile = rfile
		self.wfile = wfile
		self.mapper = mapper
		self.gesture_action = None
		self.locked_actions = {}
	
	
	def close(self):
		""" Closes connection to this client """
		try:
			self.connection.shutdown(True)
		except:
			pass
	
	
	def request_gesture(self, daemon, what, up_angle):
		"""
		Handler used when client requested gesture detection with
		"Gesture:" message.
		
		Should be called while daemon.lock is acquired.
		"""
		def cb(gesture):
			# Called while lock is being held
			try:
				self.wfile.write(b"Gesture: %s %s\n" % (what, gesture))
			except:
				pass
		
		gd = daemon._start_gesture(self.mapper, what, up_angle, cb)
		gd.enable()
		log.debug("Gesture detection requested on %s", what)
	
	
	def lock_action(self, daemon, what):
		"""
		Locks action so event can be send to client instead of handling it.
		
		Should be called while daemon.lock is acquired.
		"""
		def lock(action, what):
			# ObservingAction should be above LockedAction
			if isinstance(action, ObservingAction):
				action.original_action = LockedAction(what, self, action.original_action)
				return action
			return LockedAction(what, self, action)
		
		daemon._apply(self.mapper, what, lock, what)
	
	
	def observe_action(self, daemon, what):
		"""
		Enables observing of action so event is both sent to client and handled.
		
		Should be called while daemon.lock is acquired.
		"""
		daemon._apply(self.mapper, what,
				lambda a : ObservingAction(what, self, a))
	
	
	def replace_action(self, daemon, what, action):
		"""
		Temporally replaces action in way that allows reversing operation when
		client disconnects.
		
		Should be called while daemon.lock is acquired.
		"""
		daemon._apply(self.mapper, what,
				lambda a : ReplacedAction(what, self, action, a))
	
	
	def unlock_actions(self, daemon):
		""" Should be called while daemon.lock is acquired """
		locked, self.locked_actions = self.locked_actions, {}
		for mapper in locked:
			s = locked[mapper]
			for a in s:
				a.unlock(daemon)
	
	
	def reaply_locks(self, daemon, mapper):
		"""
		Called after profile is changed.
		Should be called while daemon.lock is acquired
		"""
		if mapper in self.locked_actions:
			s, self.locked_actions[mapper] = self.locked_actions[mapper], set()
			for a in s:
				a.reaply(self, daemon)


class ReportingAction(Action):
	"""
	Action used to send requested inputs to client.
	Base for LockedAction and ObservingAction
	"""
	MIN_DIFFERENCE = 300
	
	def __init__(self, what, client):
		self.what = what
		self.client = client
		self.mapper = client.mapper
		self.old_pos = 0, 0
	
	
	def _store_lock(self):
		if self.mapper not in self.client.locked_actions:
			self.client.locked_actions[self.mapper] = set()
		self.client.locked_actions[self.mapper].add(self)
	
	
	def __repr__(self):
		return "<%s of %x>" % (self.__class__.__name__, hash(self.client))
	__str__ = __repr__
	
	
	def _report(self, message):
		try:
			self.client.wfile.write(message.encode("utf-8"))
		except Exception, e:
			# May fail when client dies
			self.client.rfile.close()
			self.client.wfile.close()
	
	
	def trigger(self, mapper, position, old_position):
		if mapper.get_controller():
			self._report("Event: %s %s %s %s\n" % (
				mapper.get_controller().get_id(),
				nameof(self.what), position, old_position
			))
	
	
	def button_press(self, mapper, number=1):
		if mapper.get_controller():
			if self.what == SCButtons.STICKPRESS:
				self._report("Event: %s STICKPRESS %s\n" % (
					mapper.get_controller().get_id(),
					number
				))
			else:
				self._report("Event: %s %s %s\n" % (
					mapper.get_controller().get_id(),
					nameof(self.what),
					number
				))
	
	
	def button_release(self, mapper):
		ReportingAction.button_press(self, mapper, 0)
	
	
	def whole(self, mapper, x, y, what):
		if (x == 0 or y == 0 or abs(x - self.old_pos[0]) > self.MIN_DIFFERENCE
							or abs(y - self.old_pos[1] > self.MIN_DIFFERENCE)):
			self.old_pos = x, y
			if mapper.get_controller():
				self._report("Event: %s %s %s %s\n" % (
					mapper.get_controller().get_id(),
					what, x, y
				))


class LockedAction(ReportingAction):
	""" Temporal action used to send requested inputs to client """
	def __init__(self, what, client, original_action):
		ReportingAction.__init__(self, what, client)
		self.original_action = original_action
		original_action.cancel(self.mapper)
		self._store_lock()
		log.debug("%s locked by %s", self.what, self.client)
	
	
	def reaply(self, client, daemon):
		client.lock_action(daemon, self.what)
	
	
	def unlock(self, daemon):
		def _unlock(a):
			if isinstance(a, ObservingAction):
				# Needs to be handled specifically
				a.original_action = _unlock(a.original_action)
				return a
			if isinstance(a, LockedAction):
				return a.original_action
			return a
		daemon._apply(self.mapper, self.what, _unlock)
		log.debug("%s unlocked", self.what)


class ReplacedAction(LockedAction):
	def __init__(self, what, client, new_action, original_action):
		ReportingAction.__init__(self, what, client)
		self.original_action = original_action
		self.new_action = new_action.compress()
		original_action.cancel(self.mapper)
		self._store_lock()
		log.debug("%s replaced by %s", self.what, self.client)
	
	
	def reaply(self, client, daemon):
		client.replace_action(daemon, self.what, self.new_action)
	
	
	def trigger(self, mapper, position, old_position):
		self.new_action.trigger(mapper, position, old_position)
	
	
	def button_press(self, mapper, number=1):
		self.new_action.button_press(mapper, mapper)
	
	
	def button_release(self, mapper):
		self.new_action.button_release(mapper, mapper)
	
	
	def whole(self, mapper, x, y, what):
		self.new_action.whole(mapper, x, y, what)


class ObservingAction(ReportingAction):
	"""
	Similar to LockedAction, send inputs to client *and* executes actions.
	"""
	def __init__(self, what, client, original_action):
		ReportingAction.__init__(self, what, client)
		self.original_action = original_action
		self._store_lock()
		log.debug("%s on %s observed by %x", self.what,
			client.mapper.get_controller(), hash(self.client))
	
	
	def reaply(self, client, daemon):
		client.observe_action(daemon, self.what)
	
	
	def cancel(self, mapper):
		self.original_action.cancel(mapper)
	
	
	def unlock(self, daemon):
		def _unobserve(a):
			if isinstance(a, ObservingAction):
				if a.client == self.client:
					return a.original_action
				a.original_action = _unobserve(a.original_action)
				return a
			if isinstance(a, LockedAction):
				a.original_action = _unobserve(a.original_action)
				return a
			return a
		
		daemon._apply(self.mapper, self.what, _unobserve)
		log.debug("%s on %s no longer observed by %x", self.what,
			self.mapper.get_controller(), hash(self.client))
	
	
	def trigger(self, mapper, position, old_position):
		ReportingAction.trigger(self, mapper, position, old_position)
		self.original_action.trigger(mapper, position, old_position)
	
	
	def button_press(self, mapper, number=1):
		ReportingAction.button_press(self, mapper, number)
		self.original_action.button_press(mapper)
	
	
	def button_release(self, mapper):
		ReportingAction.button_release(self, mapper)
		self.original_action.button_release(mapper)
	
	
	def whole(self, mapper, x, y, what):
		ReportingAction.whole(self, mapper, x, y, what)
		self.original_action.whole(mapper, x, y, what)


class Subprocess(object):
	"""
	Part of scc-daemon executed as another process, killed along with scc-daemon.
	Currently scc-osd-daemon and scc-windowswitch-daemon.
	"""
	
	def __init__(self, binary_name, debug, restart_after=5):
		self.binary_name = binary_name
		self.restart_after = restart_after
		self.args = [ sys.executable, find_binary(binary_name) ]
		if debug:
			self.args.append('debug')
		self._killed = False
		self.p = None
		self.t = threading.Thread(target=self._threaded)
		self.t.daemon = True
		self.t.start()
	
	
	def _threaded(self, *a):
		while not self._killed:
			self.p = subprocess.Popen(self.args, stdin=None)
			self.p.communicate()
			if self.p and self.p.returncode == 8:
				log.warning("%s exited with code 8; not restarting",
					self.binary_name)
				self.p = None
				return
			self.p = None
			if not self._killed:
				log.warning("%s died; restarting after %ss",
					self.binary_name, self.restart_after)
				time.sleep(self.restart_after)
	
	
	def mark_killed(self):
		"""
		Prevents subprocess from being automatically restarted, but doesn't
		really kill it.
		"""
		self._killed = True
	
	
	def kill(self):
		self.mark_killed()
		if self.p:
			self.p.kill()
		self.p = None
