#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC-Controller - OSD Menu

Display menu that user can navigate through and print chosen item id to stdout
"""

from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GdkX11, GObject, GLib, GdkPixbuf, cairo
from xml.etree import ElementTree as ET
from scc.constants import LEFT, RIGHT, STICK, STICK_PAD_MIN, STICK_PAD_MAX
from scc.constants import STICK_PAD_MIN_HALF, STICK_PAD_MAX_HALF, CPAD
from scc.constants import SCButtons, ControllerFlags
from scc.tools import point_in_gtkrect, circle_to_square, clamp
from scc.tools import find_profile, find_button_image
from scc.paths import get_share_path, get_config_path
from scc.parser import TalkingActionParser
from scc.modifiers import ModeModifier
from scc.menu_data import MenuData
from scc.actions import Action
from scc.profile import Profile
from scc.config import Config
from scc.uinput import Keys
from scc.lib import xwrappers as X
from scc.gui.svg_widget import SVGWidget, SVGEditor
from scc.gui.keycode_to_key import KEY_TO_KEYCODE
from scc.gui.daemon_manager import DaemonManager, ControllerManager
from scc.gui.gdk_to_key import KEY_TO_GDK
from scc.osd.timermanager import TimerManager
from scc.osd.slave_mapper import SlaveMapper
from scc.osd import OSDWindow
import scc.osd.osk_actions

import os, sys, json, logging
log = logging.getLogger("osd.keyboard")

SPECIAL_KEYS = {
	# Maps keycode to unicode character representing some
	# very special keys
	8: "←",
	9: "⇥",
	13: "↲",
	27: "␛",
	32: "␣",
}


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
		
		self.overlay = SVGWidget(image, False)
		self.tree = ET.fromstring(self.overlay.current_svg.encode("utf-8"))
		SVGWidget.find_areas(self.tree, None, areas, get_colors=True)
		
		self._hilight = ()
		self._pressed = ()
		self._button_images = {}
		self._help_areas = [ self.get_limit("HELP_LEFT"), self.get_limit("HELP_RIGHT") ]
		self._help_lines = ( [], [] )
		
		# TODO: It would be cool to use user-set font here, but cairo doesn't
		# have glyph replacement and most of default fonts (Ubuntu, Cantarell,
		# similar shit) misses pretty-much everything but letters, notably ↲
		#
		# For that reason, DejaVu Sans is hardcoded for now. On systems
		# where DejaVu Sans is not available, Cairo will automatically fallback
		# to default font.
		self.font_face = "DejaVu Sans"
		# self.font_face = Gtk.Label(label="X").get_style().font_desc.get_family()
		log.debug("Using font %s", self.font_face)
		
		self.buttons = [ Button(self.tree, area) for area in areas ]
		background = SVGEditor.find_by_id(self.tree, "BACKGROUND")
		self.set_size_request(*SVGEditor.get_size(background))
		self.overlay.edit().keep("overlay").commit()
		self.overlay.hilight({})
		# open("/tmp/a.svg", "w").write(self.overlay.current_svg.encode("utf-8"))
	
	
	def hilight(self, hilight, pressed):
		self._hilight = hilight
		self._pressed = pressed
		self.queue_draw()
	
	
	def set_help(self, left, right):
		self._help_lines = ( left, right )
		self.queue_draw()
	
	
	def set_labels(self, labels):
		for b in self.buttons:
			label = labels.get(b)
			if type(label) in (int, int):
				pass
			elif label:
				b.label = label.encode("utf-8")
		self.queue_draw()
	
	
	def get_limit(self, id):
		a = SVGEditor.find_by_id(self.tree, id)
		width, height = 0, 0
		if not hasattr(a, "parent"): a.parent = None
		x, y = SVGEditor.get_translation(a, absolute=True)
		if 'width' in a.attrib:  width = float(a.attrib['width'])
		if 'height' in a.attrib: height = float(a.attrib['height'])
		return x, y, width, height
	
	
	@staticmethod
	def increase_contrast(buf):
		"""
		Takes input image, which is assumed to be grayscale RGBA and turns it
		into "symbolic" image by inverting colors of pixels where opacity is
		greater than threshold.
		"""
		pixels = [ ord(x) for x in buf.get_pixels() ]
		bpp = 4 if buf.get_has_alpha() else 3
		w, h = buf.get_width(), buf.get_height()
		stride = buf.get_rowstride()
		for i in range(0, len(pixels), bpp):
			if pixels[i + 3] > 64:
				pixels[i + 0] = 255 - pixels[i + 0]
				pixels[i + 1] = 255 - pixels[i + 1]
				pixels[i + 2] = 255 - pixels[i + 2]
		
		pixels = b"".join([ chr(x) for x in pixels])
		rv = GdkPixbuf.Pixbuf.new_from_data(
			pixels,
			buf.get_colorspace(),
			buf.get_has_alpha(),
			buf.get_bits_per_sample(),
			w, h, stride,
			None
		)
		rv.pixels = pixels	# Has to be kept in memory
		return rv
	
	
	def get_button_image(self, x, size):
		"""
		Loads and returns button image as pixbuf.
		Pixbufs are cached.
		"""
		if x not in self._button_images:
			path, bw = find_button_image(x, prefer_bw=True)
			if path is None:
				self._button_images[x] = None
				return None
			buf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
			buf = self.increase_contrast(buf)
			self._button_images[x] = buf
		i = self._button_images[x]
		return i
	
	
	def on_draw(self, self2, ctx):
		ctx.select_font_face(self.font_face, 0, 0)
		
		ctx.set_line_width(self.LINE_WIDTH)
		ctx.set_font_size(48)
		ascent, descent, height, max_x_advance, max_y_advance = ctx.font_extents()
		
		# Buttons
		for button in self.buttons:
			if button in self._pressed:
				ctx.set_source_rgba(*self.color_pressed)
			elif button in self._hilight:
				ctx.set_source_rgba(*self.color_hilight)
			elif button.dark:
				ctx.set_source_rgba(*self.color_button2)
			else:
				ctx.set_source_rgba(*self.color_button1)
			# filled rectangle
			x, y, w, h = button
			ctx.move_to(x, y)
			ctx.line_to(x + w, y)
			ctx.line_to(x + w, y + h)
			ctx.line_to(x, y + h)
			ctx.line_to(x, y)
			ctx.fill()
			
			# border
			ctx.set_source_rgba(*self.color_button1_border)
			ctx.move_to(x, y)
			ctx.line_to(x + w, y)
			ctx.line_to(x + w, y + h)
			ctx.line_to(x, y + h)
			ctx.line_to(x, y)
			ctx.stroke()
			
			# label
			if button.label:
				ctx.set_source_rgba(*self.color_text)
				extents = ctx.text_extents(button.label)
				x_bearing, y_bearing, width, trash, x_advance, y_advance = extents
				ctx.move_to(x + w * 0.5 - width * 0.5 - x_bearing, y + h * 0.5 + height * 0.3)
				ctx.show_text(button.label)
				ctx.stroke()
		
		# Overlay
		Gdk.cairo_set_source_pixbuf(ctx, self.overlay.get_pixbuf(), 0, 0)
		ctx.paint()
		
		# Help
		ctx.set_source_rgba(*self.color_text)
		ctx.set_font_size(16)
		ascent, descent, height, max_x_advance, max_y_advance = ctx.font_extents()
		for left_right in (0, 1):
			x, y, w, h = self._help_areas[left_right]
			lines = self._help_lines[left_right]
			xx = x if left_right == 0 else x + w
			yy = y
			for (icon, line) in lines:
				yy += height
				if yy > y + h:
					break
				image = self.get_button_image(icon, height * 0.9)
				if image is None: continue
				iw, ih = image.get_width(), image.get_height()
				
				if left_right == 1:	# Right align
					extents = ctx.text_extents(line)
					x_bearing, y_bearing, width, trash, x_advance, y_advance = extents
					ctx.save()
					ctx.translate(xx - height + (height - iw) * 0.5,
						1 + yy - (ascent + ih) * 0.5)
					Gdk.cairo_set_source_pixbuf(ctx, image, 0, 0)
					ctx.paint()
					ctx.restore()
					ctx.move_to(xx - x_bearing - width - 5 - height, yy)
				else:
					ctx.save()
					ctx.translate(1 + xx + (height - iw) * 0.5,
						1 + yy - (ascent + ih) * 0.5)
					Gdk.cairo_set_source_pixbuf(ctx, image, 0, 0)
					ctx.paint()
					ctx.restore()
					ctx.move_to(xx + 5 + height, yy)
					
				ctx.show_text(line)
				ctx.stroke()
	
	
	def on_size_allocate(self, *a):
		pass


class Button:
	
	def __init__(self, tree, area):
		self.contains = area.contains
		self.name = area.name
		self.label = None
		self.x, self.y = area.x, area.y
		self.w, self.h = area.w, area.h
		self.dark = area.color[2] < 0.5		# Dark button is less than 50% blue
	
	
	def __iter__(self):
		return iter(( self.x, self.y, self.w, self.h ))


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
		self.cursors[CPAD] = Gtk.Image.new_from_file(cursor)
		self.cursors[CPAD].set_name("osd-keyboard-cursor")
		
		self._eh_ids = []
		self._controller = None
		self._stick = 0, 0
		self._hovers = { self.cursors[LEFT]: None, self.cursors[RIGHT]: None }
		self._pressed = { self.cursors[LEFT]: None, self.cursors[RIGHT]: None }
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
		self.limits[CPAD] = self.background.get_limit("LIMIT_CPAD")
		self._pack()
	
	
	def _pack(self):
		self.f.add(self.background)
		self.f.add(self.cursors[LEFT])
		self.f.add(self.cursors[RIGHT])
		self.f.add(self.cursors[CPAD])
		self.c.add(self.f)
		self.add(self.c)
	
	
	def recolor(self):
		# TODO: keyboard description is probably not needed anymore
		_get = lambda a: SVGWidget.color_to_float(self.config['osk_colors'].get(a, ""))
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
	
	
	def set_help(self):
		"""
		Updates help shown on keyboard image.
		Keyboard bindings don't change on the fly, so this is done only
		right after start or when daemon is reconfigured.
		"""
		if self._controller is None:
			# Not yet connected
			return
		gui_config = self._controller.load_gui_config(os.path.join(get_share_path(), "images"))
		l_lines, r_lines, used = [], [], set()
		
		def add_action(side, button, a):
			if not a:
				return
			if isinstance(a, scc.osd.osk_actions.OSKCursorAction):
				if a.side != CPAD: return
			if isinstance(a, ModeModifier):
				for x in a.get_child_actions():
					add_action(side, button, x)
				return
			desc = a.describe(Action.AC_OSK)
			if desc in used:
				if isinstance(a, scc.osd.osk_actions.OSKPressAction):
					# Special case, both triggers are set to "press a key"
					pass
				else:
					return
			icon = self._controller.get_button_name(gui_config, button)
			side.append(( icon, desc ))
			used.add(desc)
		
		def add_button(side, b):
			add_action(side, b, self.profile.buttons[b])
		
		if self._controller.get_flags() & ControllerFlags.NO_GRIPS == 0:
			add_button(l_lines, SCButtons.LGRIP)
			add_button(r_lines, SCButtons.RGRIP)
		add_action(l_lines, SCButtons.LT, self.profile.triggers[LEFT])
		add_action(r_lines, SCButtons.RT, self.profile.triggers[RIGHT])
		for b in (SCButtons.LB, SCButtons.Y, SCButtons.X):
			add_button(l_lines, b)
		for b in (SCButtons.RB, SCButtons.B, SCButtons.A):
			add_button(r_lines, b)
		
		if self._controller.get_flags() & ControllerFlags.HAS_CPAD != 0:
			for lst in (l_lines, r_lines):
				while len(lst) > 3: lst.pop()
				while len(lst) < 3: lst.append((None, ""))
			add_action(r_lines, CPAD, self.profile.pads[CPAD])
		add_action(l_lines, SCButtons.STICKPRESS, self.profile.stick)
		
		self.background.set_help(l_lines, r_lines)
	
	
	def update_labels(self):
		""" Updates keyboard labels based on active X keymap """
		
		labels = {}
		# Get current layout group
		self.group = X.get_xkb_state(self.dpy).group
		# Get state of shift/alt/ctrl key
		mt = Gdk.ModifierType(self.keymap.get_modifier_state())
		for button in self.background.buttons:
			if getattr(Keys, button.name, None) in KEY_TO_KEYCODE:
				keycode = KEY_TO_KEYCODE[getattr(Keys, button.name)]
				translation = self.keymap.translate_keyboard_state(keycode, mt, self.group)
				if hasattr(translation, "keyval"):
					code = Gdk.keyval_to_unicode(translation.keyval)
				else:
					code = Gdk.keyval_to_unicode(translation[1])
				if code >= 33:			 		# Printable chars, w/out space
					labels[button] = chr(code).strip()
				else:
					labels[button] = SPECIAL_KEYS.get(code)
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
	
	
	def load_profile(self):
		self.profile.load(find_profile(Keyboard.OSK_PROF_NAME)).compress()
		self.set_help()
	
	
	def on_reconfigured(self, *a):
		self.load_profile()
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
		
		# TODO: Single-handed mode for PS4 posponed
		locks = [ LEFT, RIGHT, STICK, "STICKPRESS" ] + [ b.name for b in SCButtons ]
		if (c.get_flags() & ControllerFlags.HAS_CPAD) == 0:
			# Two pads, two hands
			locks = [ LEFT, RIGHT, STICK, "STICKPRESS" ] + [ b.name for b in SCButtons ]
			self.cursors[CPAD].hide()
		else:
			# Single-handed mode
			locks = [ CPAD, "CPADPRESS", STICK, "STICKPRESS" ] + [ b.name for b in SCButtons ]
			self._hovers[self.cursors[RIGHT]] = None
			self._hovers = { self.cursors[CPAD] : None }
			self._pressed = { self.cursors[CPAD] : None }
			self.cursors[LEFT].hide()
			self.cursors[RIGHT].hide()
			
			# There is no configurable nor default mapping for CPDAD,
			# so situable mappings are hardcoded here
			self.profile.pads[CPAD] = scc.osd.osk_actions.OSKCursorAction(CPAD)
			self.profile.pads[CPAD].speed = [ 0.85, 1.2 ]
			self.profile.buttons[SCButtons.CPADPRESS] = scc.osd.osk_actions.OSKPressAction(CPAD)
			
			for i in (LEFT, RIGHT):
				if isinstance(self.profile.triggers[i], scc.osd.osk_actions.OSKPressAction):
					self.profile.triggers[i] = scc.osd.osk_actions.OSKPressAction(CPAD)
		
		self._controller = c
		c.lock(success, self.on_failed_to_lock, *locks)
		self.set_help()
	
	
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
		self.load_profile()
		self.mapper = SlaveMapper(self.profile, None,
			keyboard=b"SCC OSD Keyboard", mouse=b"SCC OSD Mouse")
		self.mapper.set_special_actions_handler(self)
		self.set_cursor_position(0, 0, self.cursors[LEFT], self.limits[LEFT])
		self.set_cursor_position(0, 0, self.cursors[RIGHT], self.limits[RIGHT])
		self.set_cursor_position(0, 0, self.cursors[CPAD], self.limits[CPAD])
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
		if cursor not in self._hovers: return
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
		for button in self.background.buttons:
			if button.contains(x, y):
				if button != self._hovers[cursor]:
					self._hovers[cursor] = button
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
			set([ a for a in list(self._hovers.values()) if a ]),
			set([ a for a in list(self._pressed_areas.values()) if a ])
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
			for button in self.background.buttons:
				if button.contains(x, y):
					if button.name.startswith("KEY_") and hasattr(Keys, button.name):
						key = getattr(Keys, button.name)
						if self._pressed[cursor] is not None:
							self.mapper.keyboard.releaseEvent([ self._pressed[cursor] ])
						self.mapper.keyboard.pressEvent([ key ])
						self._pressed[cursor] = key
						self._pressed_areas[cursor] = button
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
