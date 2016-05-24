#!/usr/bin/env python2

"""
SC-Controller - OSD Daemon

Controls stuff displayed as OSD.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Rsvg', '2.0')
gi.require_version('GdkX11', '3.0')

from gi.repository import Gtk, GLib
from scc.gui.daemon_manager import DaemonManager
from scc.osd import OSDWindow
from scc.osd.grid_menu import GridMenu
from scc.osd.keyboard import Keyboard
from scc.osd.message import Message
from scc.osd.menu import Menu

import os, sys, shlex, logging
log = logging.getLogger("osd.daemon")

class OSDDaemon(object):
	def __init__(self):
		self.exit_code = -1
		self.mainloop = GLib.MainLoop()
		self._window = None
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
		self._window = None
		if m.get_exit_code() == 0:
			# 0 means that user selected item and confirmed selection
			self.daemon.request(
				'Selected: %s %s' % (m.get_menuid(), m.get_selected_item_id()),
				lambda *a : False, lambda *a : False)
	
	
	def on_keyboard_closed(self, *a):
		""" Called after on-screen keyboard is hidden from the screen """
		self._window = None
	
	
	def on_unknown_message(self, daemon, message):
		if not message.startswith("OSD:"):
			return
		if message.startswith("OSD: message"):
			args = split(message)[1:]
			m = Message()
			m.parse_argumets(args)
			m.show()
		elif message.startswith("OSD: keyboard"):
			if self._window:
				log.warning("Another OSD is already visible - refusing to show keyboard")
			else:
				args = split(message)[1:]
				self._window = Keyboard()
				self._window.connect('destroy', self.on_keyboard_closed)
				# self._window.parse_argumets(args) # TODO: No arguments so far
				self._window.show()
				self._window.use_daemon(self.daemon)
		elif message.startswith("OSD: menu") or message.startswith("OSD: gridmenu"):
			args = split(message)[1:]
			if self._window:
				log.warning("Another OSD is already visible - refusing to show menu")
			else:
				self._window = GridMenu() if "gridmenu" in message else Menu()
				self._window.connect('destroy', self.on_menu_closed)
				if self._window.parse_argumets(args):
					self._window.show()
					self._window.use_daemon(self.daemon)
				else:
					log.error("Failed to show menu")
					self._window = None
		else:
			log.warning("Unknown command from daemon: '%s'", message)
	
	
	def run(self):
		self.daemon = DaemonManager()
		self.daemon.connect('dead', self.on_daemon_died)
		self.daemon.connect('alive', self.on_daemon_connected)
		self.daemon.connect('unknown-msg', self.on_unknown_message)
		self.mainloop.run()


def split(s):
	lex = shlex.shlex(s, posix=True)
	lex.escapedquotes = '"\''
	lex.whitespace_split = True
	return list(lex)


if __name__ == "__main__":
	from scc.tools import init_logging, set_logging_level
	from scc.paths import get_share_path
	init_logging()
	set_logging_level('debug' in sys.argv, 'debug' in sys.argv)
	
	d = OSDDaemon()
	d.run()
	sys.exit(d.get_exit_code())
