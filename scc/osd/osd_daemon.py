"""
SC-Controller - OSD Daemon

Controls stuff displayed as OSD.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, GLib
from scc.gui.daemon_manager import DaemonManager
from scc.osd import OSDWindow
from scc.osd.message import Message
from scc.osd.menu import Menu

import os, sys, shlex, logging
log = logging.getLogger("osd.daemon")

class OSDDaemon(object):
	def __init__(self):
		self.exit_code = -1
		self.mainloop = GLib.MainLoop()
		self._registered = False
		OSDWindow._apply_css()
	
	
	def quit(self, code=-1):
		self.exit_code = code
		self.mainloop.quit()
	
	
	def get_exit_code(self):
		return self.exit_code
	
	
	def on_daemon_died(self, *a):
		log.error("Daemon died")
		self.quit(2)
	
	
	def on_daemon_connected(self, *a):
		def success(*a):
			log.info("Sucessfully registered as scc-osd-daemon")
			self._registered = True
		def failure(why):
			log.error("Failed to registered as scc-osd-daemon: %s", why)
			self.quit(1)
		
		if not self._registered:
			self.daemon.request('Register: osd', success, failure)
	
	
	def on_menu_closed(self, m):
		""" Called after OSD menu is hidden from screen """
		if m.get_exit_code() == 0:
			# 0 means that user selected item and confirmed selection
			self.daemon.request(
				'Selected: %s %s' % (m.get_menuid(), m.get_selected_item_id()),
				lambda *a : False, lambda *a : False)
	
	
	def on_unknown_message(self, daemon, message):
		if message.startswith("OSD: message"):
			args = shlex.split(message)[1:]
			m = Message()
			m.parse_argumets(args)
			m.show()
		elif message.startswith("OSD: menu"):
			args = shlex.split(message)[1:]
			m = Menu()
			m.connect('destroy', self.on_menu_closed)
			if m.parse_argumets(args):
				m.show()
				m.use_daemon(self.daemon)
			else:
				log.error("Failed to show menu")
		else:
			log.warning("Unknown command from daemon: '%s'", message)
	
	
	def run(self):
		self.daemon = DaemonManager()
		self.daemon.connect('dead', self.on_daemon_died)
		self.daemon.connect('alive', self.on_daemon_connected)
		self.daemon.connect('unknown-msg', self.on_unknown_message)
		self.mainloop.run()
