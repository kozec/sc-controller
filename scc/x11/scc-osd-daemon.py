#!/usr/bin/env python2

"""
SC-Controller - OSD Daemon

Controls stuff displayed as OSD.
"""

from scc.tools import _, set_logging_level

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Rsvg', '2.0')
gi.require_version('GdkX11', '3.0')

from gi.repository import Gtk, Gdk, GdkX11, GLib
from scc.gui.daemon_manager import DaemonManager
from scc.osd.gesture_display import GestureDisplay
from scc.osd.radial_menu import RadialMenu
from scc.osd.hmenu import HorizontalMenu
from scc.osd.quick_menu import QuickMenu
from scc.osd.grid_menu import GridMenu
from scc.osd.keyboard import Keyboard
from scc.osd.message import Message
from scc.osd.dialog import Dialog
from scc.osd import OSDWindow
from scc.osd.menu import Menu
from scc.osd.area import Area
from scc.special_actions import OSDAction
from scc.tools import shsplit, shjoin
from scc.config import Config

import os, sys, logging, time, traceback
log = logging.getLogger("osd.daemon")

class OSDDaemon(object):
	def __init__(self):
		self.exit_code = -1
		self.mainloop = GLib.MainLoop()
		self.config = None
		# hash_of_colors is used to determine if css needs to be reapplied
		# after configuration change
		self._hash_of_colors = -1
		self._visible_messages = {}
		self._window = None
		self._registered = False
		self._last_profile_change = 0
		self._recent_profiles_undo = None
	
	
	def quit(self, code=-1):
		self.exit_code = code
		self.mainloop.quit()
	
	
	def get_exit_code(self):
		return self.exit_code
	
	
	def on_daemon_reconfigured(self, *a):
		log.debug("Reloading config...")
		self.config.reload()
		self._check_colorconfig_change()
	
	
	def on_profile_changed(self, daemon, profile):
		name = os.path.split(profile)[-1]
		if name.endswith(".sccprofile") and not name.startswith("."):
			# Ignore .mod and hidden files
			name = name[0:-11]
			recents = self.config['recent_profiles']
			if len(recents) and recents[0] == name:
				# Already first in recent list
				return
			
			if time.time() - self._last_profile_change < 2.0:
				# Profiles are changing too fast, probably because user
				# is using scroll wheel over profile combobox
				if self._recent_profiles_undo:
					recents = [] + self._recent_profiles_undo
			self._last_profile_change = time.time()
			self._recent_profiles_undo = [] + recents
			
			while name in recents:
				recents.remove(name)
			recents.insert(0, name)
			if len(recents) > self.config['recent_max']:
				recents = recents[0:self.config['recent_max']]
			self.config['recent_profiles'] = recents
			self.config.save()
			log.debug("Updated recent profile list")
			self.clear_messages()
	
	
	def on_daemon_died(self, *a):
		log.error("Connection to daemon lost")
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
				'Selected: %s' % ( shjoin([
					m.get_menuid(), m.get_selected_item_id()
				])),
				lambda *a : False, lambda *a : False)
	
	
	def on_message_closed(self, m):
		hsh = m.hash()
		if hsh in self._visible_messages:
			del self._visible_messages[hsh]
	
	
	def on_keyboard_closed(self, *a):
		""" Called after on-screen keyboard is hidden from the screen """
		self._window = None
	
	
	def on_gesture_recognized(self, gd):
		""" Called after on-screen keyboard is hidden from the screen """
		self._window = None
		if gd.get_exit_code() == 0:
			self.daemon.request('Gestured: %s' % ( gd.get_gesture(), ),
				lambda *a : False, lambda *a : False)
		else:
			self.daemon.request('Gestured: x', lambda *a : False, lambda *a : False)
	
	
	@staticmethod
	def _is_menu_message(m):
		"""
		Returns True if m starts with 'OSD: [grid|radial]menu'
		or "OSD: dialog"
		"""
		return (
			m.startswith("OSD: menu")
			or m.startswith("OSD: radialmenu")
			or m.startswith("OSD: quickmenu")
			or m.startswith("OSD: gridmenu")
			or m.startswith("OSD: dialog")
			or m.startswith("OSD: hmenu")
		)
	
	
	def on_unknown_message(self, daemon, message):
		if not message.startswith("OSD:"):
			return
		if message.startswith("OSD: message"):
			args = shsplit(message)[1:]
			m = Message()
			m.parse_argumets(args)
			hsh = m.hash()
			if hsh in self._visible_messages:
				self._visible_messages[hsh].extend()
				m.destroy()
			else:
				# TODO: Do this only for default position once changing
				# TODO: is allowed
				if len(self._visible_messages):
					height = list(self._visible_messages.values())[0].get_size().height
					x, y = m.position
					while y in [ i.position[1] for i in list(self._visible_messages.values()) ]:
						y -= height + 5
					m.position = x, y
				m.show()
				self._visible_messages[hsh] = m
				m.connect("destroy", self.on_message_closed)
		elif message.startswith("OSD: keyboard"):
			if self._window:
				log.warning("Another OSD is already visible - refusing to show keyboard")
			else:
				args = shsplit(message)[1:]
				self._window = Keyboard(self.config)
				self._window.connect('destroy', self.on_keyboard_closed)
				self._window.parse_argumets(args)
				self._window.show()
				self._window.use_daemon(self.daemon)
		elif message.startswith("OSD: gesture"):
			if self._window:
				log.warning("Another OSD is already visible - refusing to show keyboard")
			else:
				args = shsplit(message)[1:]
				self._window = GestureDisplay(self.config)
				self._window.parse_argumets(args)
				self._window.use_daemon(self.daemon)
				self._window.show()
				self._window.connect('destroy', self.on_gesture_recognized)
		elif self._is_menu_message(message):
			args = shsplit(message)[1:]
			if self._window:
				log.warning("Another OSD is already visible - refusing to show menu")
			else:
				if message.startswith("OSD: hmenu"):
					self._window = HorizontalMenu()
				elif message.startswith("OSD: radialmenu"):
					self._window = RadialMenu()
				elif message.startswith("OSD: quickmenu"):
					self._window = QuickMenu()
				elif message.startswith("OSD: gridmenu"):
					self._window = GridMenu()
				elif message.startswith("OSD: dialog"):
					self._window = Dialog()
				else:
					self._window = Menu()
				self._window.connect('destroy', self.on_menu_closed)
				self._window.use_config(self.config)
				try:
					if self._window.parse_argumets(args):
						self._window.show()
						self._window.use_daemon(self.daemon)
					else:
						log.error("Failed to show menu")
						self._window = None
				except:
					log.error(traceback.format_exc())
					log.error("Failed to show menu")
					self._window = None
		elif message.startswith("OSD: area"):
			args = shsplit(message)[1:]
			if self._window:
				log.warning("Another OSD is already visible - refusing to show area")
			else:
				args = shsplit(message)[1:]
				self._window = Area()
				self._window.connect('destroy', self.on_keyboard_closed)
				if self._window.parse_argumets(args):
					self._window.show()
				else:
					self._window.quit()
					self._window = None
		elif message.startswith("OSD: clear"):
			# Clears active OSD windows
			self.clear_windows()
		else:
			log.warning("Unknown command from daemon: '%s'", message)
	
	
	def clear_windows(self):
		if self._window:
			self._window.quit()
			self._window = None
		self.clear_messages(only_long_lasting=False)
	
	
	def clear_messages(self, only_long_lasting=True):
		"""
		Clears all OSD messages from screen.
		If only_long_lasting is True, which is default behaviour on profile
		change, only messages set to last more than 10s are hidden.
		"""
		to_destroy = [] + list(self._visible_messages.values())
		for m in to_destroy:
			if not only_long_lasting or m.timeout <= 0 or m.timeout > OSDAction.DEFAULT_TIMEOUT * 2:
				m.destroy()
	
	
	def _check_colorconfig_change(self):
		"""
		Checks if OSD color configuration is changed and re-applies CSS
		if needed.
		"""
		h = sum([ hash(self.config['osd_colors'][x]) for x in self.config['osd_colors'] ])
		h += sum([ hash(self.config['osk_colors'][x]) for x in self.config['osk_colors'] ])
		h += hash(self.config['osd_style'])
		if self._hash_of_colors != h:
			self._hash_of_colors = h
			OSDWindow._apply_css(self.config)
			if self._window and isinstance(self._window, Keyboard):
				self._window.recolor()
				self._window.update_labels()
				self._window.redraw_background()
	
	
	def run(self):
		on_wayland = "WAYLAND_DISPLAY" in os.environ or not isinstance(Gdk.Display.get_default(), GdkX11.X11Display)
		if on_wayland:
			log.error("Cannot run on Wayland")
			self.exit_code = 8
			return
		self.daemon = DaemonManager()
		self.config = Config()
		self._check_colorconfig_change()
		self.daemon.connect('alive', self.on_daemon_connected)
		self.daemon.connect('dead', self.on_daemon_died)
		self.daemon.connect('profile-changed', self.on_profile_changed)
		self.daemon.connect('reconfigured', self.on_daemon_reconfigured)
		self.daemon.connect('unknown-msg', self.on_unknown_message)
		self.mainloop.run()


if __name__ == "__main__":
	from scc.tools import init_logging, set_logging_level
	from scc.paths import get_share_path
	init_logging(suffix=" OSD")
	set_logging_level('debug' in sys.argv, 'debug' in sys.argv)
	
	d = OSDDaemon()
	d.run()
	sys.exit(d.get_exit_code())
