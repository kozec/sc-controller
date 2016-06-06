#!/usr/bin/env python2
"""
SC-Controller - Autoswitch Daemon

Observes active window and commands scc-daemon to change profiles as needed.
"""
from __future__ import unicode_literals

from scc.lib import xwrappers as X
from scc.tools import set_logging_level, find_profile
from scc.paths import get_daemon_socket
from scc.config import Config

import os, sys, time, socket, threading, signal, logging
log = logging.getLogger("AutoSwitcher")

class AutoSwitcher(object):
	INTERVAL = 1
	
	def __init__(self):
		self.dpy = X.open_display(os.environ["DISPLAY"])
		self.lock = threading.Lock()
		self.thread = threading.Thread(target=self.connect_daemon)
		self.config = Config()
		self.socket = None
		self.connected = False
		self.exit_code = None
		self.current_profile = None
		self.conds = self.config['autoswitch']
	
	
	def connect_daemon(self, *a):
		try:
			self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			self.socket.connect(get_daemon_socket())
		except Exception:
			log.error("Failed to connect to scc-daemon")
			os._exit(1)
			return
		buffer = ""
		while self.exit_code is None:
			r = self.socket.recv(1024)
			self.lock.acquire()
			if len(r) == 0:
				self.lock.release()
				log.error("Connection to daemon lost")
				os._exit(2)
				return
			buffer += r
			while "\n" in buffer:
				line, buffer = buffer.split("\n", 1)
				if line.startswith("Version:"):
					version = line.split(":", 1)[-1].strip()
					log.debug("Connected to daemon, version %s", version)
				elif line.startswith("Current profile:"):
					profile = line.split(":", 1)[-1].strip()
					log.debug("Daemon reported profile change: %s", profile)
					self.current_profile = profile
					
			self.lock.release()
			
		
	
	
	def check(self, *a):
		w = X.get_current_window(self.dpy)
		pars = X.get_window_title(self.dpy, w), X.get_window_class(self.dpy, w)
		for c in self.conds:
			if c.matches(*pars):
				path = find_profile(self.conds[c])
				if path:
					self.lock.acquire()
					if path != self.current_profile and not self.current_profile.endswith(".mod"):
						# Switch only if target profile is not active
						# and active profile is not being editted.
						try:
						self.socket.send(b"Profile: " + path.encode('utf-8') + b"\n")
						except:
							self.lock.release()
							log.error("Socket write failed")
							os._exit(2)
							return
					self.lock.release()
				else:
					log.error("Cannot switch to profile '%s', profile file not found", self.conds[c])
	
	
	def sigint(self, *a):
		log.error("break")
		os._exit(0)
	
	
	def run(self):
		self.thread.start()
		log.debug("AutoSwitcher started")
		while self.exit_code is None:
			self.check()
			time.sleep(self.INTERVAL)
		return 1



if __name__ == "__main__":
	from scc.tools import init_logging, set_logging_level
	from scc.paths import get_share_path
	init_logging(suffix=" AutoSwitcher")
	set_logging_level('debug' in sys.argv, 'debug' in sys.argv)
	
	if "DISPLAY" not in os.environ:
		log.error("DISPLAY env variable not set.")
		sys.exit(1)
	
	d = AutoSwitcher()
	signal.signal(signal.SIGINT, d.sigint)
	d.run()
	sys.exit(d.exit_code)
