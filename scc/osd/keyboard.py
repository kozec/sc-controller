#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
SC-Controller - OSD Menu

Display menu that user can navigate through and print chosen item id to stdout
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GdkX11, GObject, GLib, cairo
from xml.etree import ElementTree as ET
from scc.constants import LEFT, RIGHT, STICK, STICK_PAD_MIN, STICK_PAD_MAX
from scc.constants import STICK_PAD_MIN_HALF, STICK_PAD_MAX_HALF
from scc.constants import SCButtons
from scc.tools import point_in_gtkrect, circle_to_square, find_profile, clamp
from scc.paths import get_share_path, get_config_path
from scc.parser import TalkingActionParser
from scc.menu_data import MenuData
from scc.actions import Action
from scc.profile import Profile
from scc.config import Config
from scc.uinput import Keys
from scc.lib import xwrappers as X
from scc.gui.svg_widget import SVGWidget, SVGEditor
from scc.gui.keycode_to_key import KEY_TO_KEYCODE
from scc.gui.daemon_manager import DaemonManager
from scc.gui.gdk_to_key import KEY_TO_GDK
from scc.osd.timermanager import TimerManager
from scc.osd.slave_mapper import SlaveMapper
from scc.osd import OSDWindow
import scc.osd.osk_actions


import os, sys, json, logging
log = logging.getLogger("osd.keyboard")


class KeyboardImage(Gtk.DrawingArea):
	LINE_WIDTH = 2
	
	__gsignals__ = {}
	
	
	def __init__(self, image):
		Gtk.DrawingArea.__init__(self)
		self.connect('size-allocate', self.on_size_allocate)
		self.connect('draw', self.on_draw)
		
		areas = []
		self.color_button1 = 0.8, 0, 0, 1			# Just random mess,
		self.color_button1_border = 1, 0, 0, 1		# config overrides it anyway
		self.color_button2 = 0.8, 0.8, 0, 1
		self.color_button2_border = 1, 1, 0, 1
		self.color_hilight = 0, 1, 1, 1
		self.color_pressed = 1, 1, 1, 1
		self.color_text = 1, 1, 1, 1
		
		self._hilight = ()
		self._pressed = ()
		self._labels = {}
		self.tree = ET.fromstring(open(image, "rb").read())
		SVGWidget.find_areas(self.tree, None, areas)
		self.font_face = Gtk.Label(label="X").get_style().font_desc.get_family()
		
		self.buttons = [ (area, area.x, area.y, area.w, area.h)
			for area in areas ]
		
		background = SVGEditor.find_by_id(self.tree, "BACKGROUND")
		self.set_size_request(*SVGEditor.get_size(background))
	
	
	def hilight(self, hilight, pressed):
		self._hilight = hilight
		self._pressed = pressed
		self.queue_draw()
	
	
	def set_labels(self, labels):
		self._labels = labels
		self.queue_draw()
	
	
	def get_limit(self, id):
		a = SVGEditor.find_by_id(self.tree, id)
		width, height = 0, 0
		if not hasattr(a, "parent"): a.parent = None
		x, y = SVGEditor.get_translation(a, absolute=True)
		if 'width' in a.attrib:  width = float(a.attrib['width'])
		if 'height' in a.attrib: height = float(a.attrib['height'])
		return x, y, width, height
	
	
	def on_draw(self, self2, ctx):
		ctx.select_font_face(self.font_face, 0, 0)
		
		ctx.set_line_width(self.LINE_WIDTH)
		for (area, x, y, w, h) in self.buttons:
			if area in self._pressed:
				ctx.set_source_rgba(*self.color_pressed)
			elif area in self._hilight:
				ctx.set_source_rgba(*self.color_hilight)
			else:
				ctx.set_source_rgba(*self.color_button1)
			# if area in self._hilights:
			# 	b, color = Gdk.Color.parse(self._hilights[area])
			# 	if b:
			# 		ctx.set_source_rgba(color.red_float, color.green_float, color.blue_float, 1)
			ctx.move_to(x, y)
			ctx.line_to(x + w, y)
			ctx.line_to(x + w, y + h)
			ctx.line_to(x, y + h)
			ctx.line_to(x, y)
			ctx.fill()
			
			ctx.set_source_rgba(*self.color_button1_border)
			ctx.move_to(x, y)
			ctx.line_to(x + w, y)
			ctx.line_to(x + w, y + h)
			ctx.line_to(x, y + h)
			ctx.line_to(x, y)
			ctx.stroke()
			
			label = self._labels.get(area, "")
			extents = ctx.text_extents(label)
			ctx.set_source_rgba(*self.color_text)
			ctx.set_font_size(48)
			ctx.move_to(x + (w/2) - (extents[2] / 2) - extents[0], y + (h/2) - (extents[3]/2) - extents[1])
			ctx.show_text(label)
	
	
	def on_size_allocate(self, *a):
		pass


class Keyboard(OSDWindow, TimerManager):
	EPILOG="""Exit codes:
   0  - clean exit, user closed keyboard
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon, sc-daemon reported error or died while keyboard is displayed.
   3  - erorr, failed to lock input stick, pad or button(s)
	"""
	OSK_PROF_NAME = ".scc-osd.keyboard"
	
	BUTTON_MAP = {
		SCButtons.A.name : Keys.KEY_ENTER,
		SCButtons.B.name : Keys.KEY_ESC,
		SCButtons.LB.name : Keys.KEY_BACKSPACE,
		SCButtons.RB.name : Keys.KEY_SPACE,
		SCButtons.LGRIP.name : Keys.KEY_LEFTSHIFT,
		SCButtons.RGRIP.name : Keys.KEY_RIGHTALT,
	}
	
	def __init__(self, config=None):
		self.kbimage = os.path.join(get_config_path(), 'keyboard.svg')
		if not os.path.exists(self.kbimage):
			# Prefer image in ~/.config/scc, but load default one as fallback
			self.kbimage = os.path.join(get_share_path(), "images", 'keyboard.svg')
		
		TimerManager.__init__(self)
		OSDWindow.__init__(self, "osd-keyboard")
		self.daemon = None
		self.mapper = None
		self.keymap = Gdk.Keymap.get_default()
		self.keymap.connect('state-changed', self.on_keymap_state_changed)
		Action.register_all(sys.modules['scc.osd.osk_actions'], prefix="OSK")
		self.profile = Profile(TalkingActionParser())
		self.config = config or Config()
		self.dpy = X.Display(hash(GdkX11.x11_get_default_xdisplay()))
		self.group = None
		self.limits = {}
		self.background = None
		
		cursor = os.path.join(get_share_path(), "images", 'menu-cursor.svg')
		self.cursors = {}
		self.cursors[LEFT] = Gtk.Image.new_from_file(cursor)
		self.cursors[LEFT].set_name("osd-keyboard-cursor")
		self.cursors[RIGHT] = Gtk.Image.new_from_file(cursor)
		self.cursors[RIGHT].set_name("osd-keyboard-cursor")
		
		self._eh_ids = []
		self._stick = 0, 0
		self._hovers = { self.cursors[LEFT] : None, self.cursors[RIGHT] : None }
		self._pressed = { self.cursors[LEFT] : None, self.cursors[RIGHT] : None }
		self._pressed_areas = {}
		
		self.c = Gtk.Box()
		self.c.set_name("osd-keyboard-container")
		
		self.f = Gtk.Fixed()
	
	
	def _create_background(self):
		self.background = KeyboardImage(self.args.image)
		self.recolor()
		
		self.limits = {}
		self.limits[LEFT]  = self.background.get_limit("LIMIT_LEFT")
		self.limits[RIGHT] = self.background.get_limit("LIMIT_RIGHT")
		self._pack()
	
	
	def _pack(self):
		self.f.add(self.background)
		self.f.add(self.cursors[LEFT])
		self.f.add(self.cursors[RIGHT])
		self.c.add(self.f)
		self.add(self.c)
	
	
	@staticmethod
	def color_to_float(colorstr):
		"""
		Parses color expressed as RRGGBB (as in config) and returns
		three floats of r, g, b, a (range 0 to 1)
		"""
		b, color = Gdk.Color.parse("#" + colorstr)
		if b:
			return color.red_float, color.green_float, color.blue_float, 1
		return 1, 0, 1, 1	# uggly purple
	
	
	def recolor(self):
		# TODO: keyboard description is probably not needed anymore
		_get = lambda a: Keyboard.color_to_float(self.config['osk_colors'].get(a, ""))
		self.background.color_button1 = _get("button1")
		self.background.color_button1_border = _get("button1_border")
		self.background.color_button2 = _get("button2")
		self.background.color_button2_border = _get("button2_border")
		self.background.color_hilight = _get("hilight")
		self.background.color_pressed = _get("pressed")
		self.background.color_text = _get("text")
	
	
	def use_daemon(self, d):
		"""
		Allows (re)using already existing DaemonManager instance in same process
		"""
		self.daemon = d
		self._cononect_handlers()
		self.on_daemon_connected(self.daemon)
	
	
	def on_keymap_state_changed(self, x11keymap):
		if not self.timer_active('labels'):
			self.timer('labels', 0.1, self.update_labels)
	
	
	def update_labels(self):
		""" Updates keyboard labels based on active X keymap """
		
		labels = {}
		# Get current layout group
		self.group = X.get_xkb_state(self.dpy).group
		# Get state of shift/alt/ctrl key
		mt = Gdk.ModifierType(self.keymap.get_modifier_state())
		for a in self.background.buttons:
			a = a[0]
			if hasattr(Keys, a.name) and getattr(Keys, a.name) in KEY_TO_KEYCODE:
				keycode = KEY_TO_KEYCODE[getattr(Keys, a.name)]
				translation = self.keymap.translate_keyboard_state(keycode, mt, self.group)
				if hasattr(translation, "keyval"):
					code = Gdk.keyval_to_unicode(translation.keyval)
				else:
					code = Gdk.keyval_to_unicode(translation[1])
				if code >= 32: # Printable chars
					labels[a] = unichr(code)
				elif code == 13: # Return
					labels[a] = "↵"
		self.background.set_labels(labels)
	
	
	def _add_arguments(self):
		OSDWindow._add_arguments(self)
		self.argparser.add_argument('image', type=str, nargs="?",
			default = self.kbimage, help="keyboard image to use")
	
	
	def parse_argumets(self, argv):
		if not OSDWindow.parse_argumets(self, argv):
			return False
		return True
	
	
	def _cononect_handlers(self):
		self._eh_ids += [
			( self.daemon, self.daemon.connect('dead', self.on_daemon_died) ),
			( self.daemon, self.daemon.connect('error', self.on_daemon_died) ),
			( self.daemon, self.daemon.connect('reconfigured', self.on_reconfigured) ),
			( self.daemon, self.daemon.connect('alive', self.on_daemon_connected) ),
		]
	
	
	def run(self):
		self.daemon = DaemonManager()
		self._cononect_handlers()
		OSDWindow.run(self)
	
	
	def on_reconfigured(self, *a):
		self.profile.load(find_profile(Keyboard.OSK_PROF_NAME)).compress()
		log.debug("Reloaded profile")
	
	
	def on_daemon_connected(self, *a):
		def success(*a):
			log.info("Sucessfully locked input")
			pass
		
		c = self.choose_controller(self.daemon)
		if c is None or not c.is_connected():
			# There is no controller connected to daemon
			self.on_failed_to_lock("Controller not connected")
			return
		
		self._eh_ids += [
			(c, c.connect('event', self.on_event)),
			(c, c.connect('lost', self.on_controller_lost)),
		]
		
		# Lock everything
		locks = [ LEFT, RIGHT, STICK, "STICKPRESS" ] + [ b.name for b in SCButtons ]
		c.lock(success, self.on_failed_to_lock, *locks)
	
	
	def quit(self, code=-1):
		if self.get_controller():
			self.get_controller().unlock_all()
		for source, eid in self._eh_ids:
			source.disconnect(eid)
		self._eh_ids = []
		del self.mapper
		OSDWindow.quit(self, code)
	
	
	def show(self, *a):
		if self.background is None:
			self._create_background()
		OSDWindow.show(self, *a)
		self.profile.load(find_profile(Keyboard.OSK_PROF_NAME)).compress()
		self.mapper = SlaveMapper(self.profile, None,
			keyboard=b"SCC OSD Keyboard", mouse=b"SCC OSD Mouse")
		self.mapper.set_special_actions_handler(self)
		self.set_cursor_position(0, 0, self.cursors[LEFT], self.limits[LEFT])
		self.set_cursor_position(0, 0, self.cursors[RIGHT], self.limits[RIGHT])
		self.timer('labels', 0.1, self.update_labels)
	
	
	def on_event(self, daemon, what, data):
		"""
		Called when button press, button release or stick / pad update is
		send by daemon.
		"""
		group = X.get_xkb_state(self.dpy).group
		if self.group != group:
			self.group = group
			self.timer('labels', 0.1, self.update_labels)
		self.mapper.handle_event(daemon, what, data)
	
	
	def on_sa_close(self, *a):
		""" Called by CloseOSDKeyboardAction """
		self.quit(0)
	
	
	def on_sa_cursor(self, mapper, action, x, y):
		self.set_cursor_position(
			x * action.speed[0],
			y * action.speed[1],
			self.cursors[action.side], self.limits[action.side])
	
	
	def on_sa_move(self, mapper, action, x, y):
		self._stick = x, y
		if not self.timer_active('stick'):
			self.timer("stick", 0.05, self._move_window)
	
	
	def on_sa_press(self, mapper, action, pressed):
		self.key_from_cursor(self.cursors[action.side], pressed)
	
	
	def set_cursor_position(self, x, y, cursor, limit):
		"""
		Moves cursor image.
		"""
		w = limit[2] - (cursor.get_allocation().width * 0.5)
		h = limit[3] - (cursor.get_allocation().height * 0.5)
		x = x / float(STICK_PAD_MAX)
		y = y / float(STICK_PAD_MAX) * -1.0
		
		x, y = circle_to_square(x, y)
		
		x = clamp(
			cursor.get_allocation().width * 0.5,
			(limit[0] + w * 0.5) + x * w * 0.5,
			self.get_allocation().width - cursor.get_allocation().width
			)
		
		y = clamp(
			cursor.get_allocation().height * 0.5,
			(limit[1] + h * 0.5) + y * h * 0.5,
			self.get_allocation().height - cursor.get_allocation().height
			)
		
		cursor.position = int(x), int(y)
		self.f.move(cursor,
			x - cursor.get_allocation().width * 0.5,
			y - cursor.get_allocation().height * 0.5)
		for a in self.background.buttons:
			a = a[0]
			if a.contains(x, y):
				if a != self._hovers[cursor]:
					self._hovers[cursor] = a
					if self._pressed[cursor] is not None:
						self.mapper.keyboard.releaseEvent([ self._pressed[cursor] ])
						self.key_from_cursor(cursor, True)
					if not self.timer_active('update'):
						self.timer('update', 0.01, self.update_background)
					break
	
	
	def update_background(self, *whatever):
		"""
		Updates hilighted keys on bacgkround image.
		"""
		self.background.hilight(
			set([ a for a in self._hovers.values() if a ]),
			set([ a for a in self._pressed_areas.values() if a ])
		)
	
	
	def _move_window(self, *a):
		"""
		Called by timer while stick is tilted to move window around the screen.
		"""
		x, y = self._stick
		x = x * 50.0 / STICK_PAD_MAX
		y = y * -50.0 / STICK_PAD_MAX
		rx, ry = self.get_position()
		self.move(rx + x, ry + y)
		if abs(self._stick[0]) > 100 or abs(self._stick[1]) > 100:
			self.timer("stick", 0.05, self._move_window)
	
	
	def key_from_cursor(self, cursor, pressed):
		"""
		Sends keypress/keyrelease event to emulated keyboard, based on
		position of cursor on OSD keyboard.
		"""
		x, y = cursor.position
		
		if pressed:
			for a in self.background.buttons:
				a = a[0]
				if a.contains(x, y):
					if a.name.startswith("KEY_") and hasattr(Keys, a.name):
						key = getattr(Keys, a.name)
						if self._pressed[cursor] is not None:
							self.mapper.keyboard.releaseEvent([ self._pressed[cursor] ])
						self.mapper.keyboard.pressEvent([ key ])
						self._pressed[cursor] = key
						self._pressed_areas[cursor] = a
					break
		elif self._pressed[cursor] is not None:
			self.mapper.keyboard.releaseEvent([ self._pressed[cursor] ])
			self._pressed[cursor] = None
			del self._pressed_areas[cursor]
		if not self.timer_active('update'):
			self.timer('update', 0.01, self.update_background)


def main():
	import gi
	gi.require_version('Gtk', '3.0')
	gi.require_version('Rsvg', '2.0')
	gi.require_version('GdkX11', '3.0')
	
	from scc.tools import init_logging
	init_logging()
	
	k = Keyboard()
	if not k.parse_argumets(sys.argv):
		sys.exit(1)
	k.run()


if __name__ == "__main__":
	import signal
	
	def sigint(*a):
		print("\n*break*")
		sys.exit(-1)
	
	signal.signal(signal.SIGINT, sigint)
	main()
