#!/usr/bin/env python2
"""
SC-Controller - Controller Registration 

Dialog that asks a lot of question to create configuration node in config file.
Most "interesting" thing here may be that this works 100% independently from
daemon.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, GLib, GdkPixbuf
from scc.gui.controller_registration.constants import X, Y, BUTTONS_WITH_IMAGES
from scc.gui.controller_registration.constants import BUTTON_ORDER, AXIS_ORDER
from scc.gui.controller_registration.constants import SDL_AXES, SDL_DPAD
from scc.gui.controller_registration.constants import SDL_TO_SCC_NAMES
from scc.gui.controller_registration.constants import STICK_PAD_AREAS
from scc.gui.controller_registration.constants import TRIGGER_AREAS
from scc.gui.controller_registration.constants import AXIS_TO_BUTTON
from scc.gui.controller_registration.grabs import InputGrabber, TriggerGrabber
from scc.gui.controller_registration.data import AxisData, DPadEmuData
from scc.gui.controller_registration.grabs import StickGrabber
from scc.gui.svg_widget import SVGWidget, SVGEditor
from scc.gui.editor import Editor
from scc.gui.app import App
from scc.constants import SCButtons, STICK_PAD_MAX, STICK_PAD_MIN
from scc.constants import STICK, LEFT, RIGHT
from scc.paths import get_config_path, get_share_path
from scc.tools import nameof, clamp

import evdev
import sys, os, logging, json, traceback
log = logging.getLogger("CRegistration")


class ControllerRegistration(Editor):
	GLADE = "controller_registration.glade"
	UNASSIGNED_COLOR = "#FFFF0000"		# ARGB
	OBSERVE_COLORS = (
		App.OBSERVE_COLOR,
		# Following just replaces 'full alpha' in ARGB with various alpha values
		App.OBSERVE_COLOR.replace("#FF", "#DF"),
		App.OBSERVE_COLOR.replace("#FF", "#BF"),
		App.OBSERVE_COLOR.replace("#FF", "#9F"),
		App.OBSERVE_COLOR.replace("#FF", "#7F"),
	)
	
	def __init__(self, app):
		Editor.__init__(self)
		self.app = app
		self._gamepad_icon = GdkPixbuf.Pixbuf.new_from_file(
				os.path.join(self.app.imagepath, "controller-icons", "evdev-0.svg"))
		self._other_icon = GdkPixbuf.Pixbuf.new_from_file(
				os.path.join(self.app.imagepath, "controller-icons", "unknown.svg"))
		self._axis_data = [ AxisData(name, xy) for (name, xy) in AXIS_ORDER ]
		self.setup_widgets()
		self._controller = None
		self._evdevice = None
		self._grabber = None
		self._input_axes = {}
		self._mappings = {}
		self._hilights = {}
		self._unassigned = set()
		self._hilighted_area = None
		self.refresh_devices()
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		cursors = {}
		for axis in self._axis_data:
			if "trig" in axis.name:
				continue
			axis.cursor = cursors[axis.area] = ( cursors.get(axis.area) or
				Gtk.Image.new_from_file(os.path.join(
				self.app.imagepath, "test-cursor.svg")) )
			axis.cursor.position = [ 0, 0 ]
	
	
	@staticmethod
	def does_he_looks_like_a_gamepad(dev):
		"""
		Examines device capabilities and decides if it passes for gamepad.
		Device is considered gamepad-like if has at least one button with
		keycode in gamepad range and at least two axes.
		"""
		# ... but some cheating first
		if "keyboard" in dev.name.lower():
			return False
		if "mouse" in dev.name.lower():
			return False
		if "gamepad" in dev.name.lower():
			return True
		caps = dev.capabilities(verbose=False)
		if evdev.ecodes.EV_ABS in caps: # Has axes
			if evdev.ecodes.EV_KEY in caps: # Has buttons
				for button in caps[evdev.ecodes.EV_KEY]:
					if button >= evdev.ecodes.BTN_0 and button <= evdev.ecodes.BTN_GEAR_UP:
						return True
		return False
	
	
	def load_sdl_mappings(self, dev):
		"""
		Attempts to load mappings from gamecontrollerdb.txt.
		
		Return True on success.
		"""
		# Build list of button and axes
		caps = dev.capabilities(verbose=False)
		buttons = caps.get(evdev.ecodes.EV_KEY, [])
		axes = ([ axis for (axis, trash) in caps[evdev.ecodes.EV_ABS] ]
			if evdev.ecodes.EV_ABS in caps else [] )
		
		# Generate database ID
		wordswap = lambda i: ((i & 0xFF) << 8) | ((i & 0xFF00) >> 8)
		# TODO: version?
		weird_id = "%.4x%.8x%.8x%.8x0000" % (
				wordswap(dev.info.bustype),
				wordswap(dev.info.vendor),
				wordswap(dev.info.product),
				wordswap(dev.info.version)
		)
		
		# Search in database
		try:
			db = open(os.path.join(get_share_path(), "gamecontrollerdb.txt"), "r")
		except Exception, e:
			log.error('Failed to load gamecontrollerdb')
			log.exception(e)
			return False
		
		for line in db.readlines():
			if line.startswith(weird_id):
				log.info("Loading mappings for '%s' from gamecontrollerdb", weird_id)
				log.debug("Buttons: %s", buttons)
				log.debug("Axes: %s", buttons)
				for token in line.strip().split(","):
					if ":" in token:
						k, v = token.split(":", 1)
						k = SDL_TO_SCC_NAMES.get(k, k)
						if v.startswith("b") and hasattr(SCButtons, k.upper()):
							try:
								keycode = buttons[int(v.strip("b"))]
							except IndexError:
								log.warning("Skipping unknown gamecontrollerdb button: %s", v)
								continue
							button  = getattr(SCButtons, k.upper())
							self._mappings[keycode] = button
						if v.startswith("b") and k in SDL_AXES:
							try:
								keycode = buttons[int(v.strip("b"))]
							except IndexError:
								log.warning("Skipping unknown gamecontrollerdb button: %s", v)
								continue
							log.warning("Adding button -> axis mapping for %s", k)
							self._mappings[keycode] = self._axis_data[SDL_AXES.index(k)]
						elif k in SDL_AXES: 
							try:
								code = axes[int(v.strip("a"))]
							except IndexError:
								log.warning("Skipping unknown gamecontrollerdb axis: %s", v)
								continue
							self._mappings[code] = self._axis_data[SDL_AXES.index(k)]
						elif k in SDL_DPAD and v.startswith("b"):
							try:
								keycode = buttons[int(v.strip("b"))]
							except IndexError:
								log.warning("Skipping unknown gamecontrollerdb button: %s", v)
								continue
							index, positive = SDL_DPAD[k]
							data = DPadEmuData(self._axis_data[index], positive)
							self._mappings[keycode] = data
						elif k == "platform":
							# Not interesting
							pass
						else:
							log.warning("Skipping unknown gamecontrollerdb mapping %s:%s", k, v)
				return True
		return False
	
	
	def generate_mappings(self, dev):
		"""
		Generates initial mappings, just to have some preset to show.
		"""
		caps = dev.capabilities(verbose=False)
		buttons = list(BUTTON_ORDER)
		axes = list(self._axis_data)
		if evdev.ecodes.EV_ABS in caps: # Has axes
			for axis, info in caps[evdev.ecodes.EV_ABS]:
				self._mappings[axis], axes = axes[0], axes[1:]
				if len(axes) == 0: break
		if evdev.ecodes.EV_KEY in caps: # Has buttons
			for button in caps[evdev.ecodes.EV_KEY]:
				self._mappings[button], buttons = buttons[0], buttons[1:]
				if len(buttons) == 0: break
	
	
	def generate_unassigned(self):
		unassigned = set()
		unassigned.clear()
		for a in BUTTON_ORDER:
			if a not in self._mappings.values():
				unassigned.add(nameof(a))
		assignex_axes = set([ x for x in self._mappings.values()
							if isinstance(x, AxisData) ])
		assignex_axes.update([ x.axis_data for x in self._mappings.values()
							if isinstance(x, DPadEmuData) ])
		for a in TRIGGER_AREAS:
			axis = self._axis_data[TRIGGER_AREAS[a]]
			if not axis in assignex_axes:
				unassigned.add(a)
		for a in STICK_PAD_AREAS:
			area_name, axes = STICK_PAD_AREAS[a]
			has_mapping = bool(sum([
				self._axis_data[index] in assignex_axes for index in axes ]))
			if not has_mapping:
				unassigned.add(area_name)
		
		hilight = unassigned - self._unassigned
		unhilight = self._unassigned - unassigned
		self._unassigned = unassigned
		for a in hilight:   self.hilight(a, self.UNASSIGNED_COLOR)
		for a in unhilight: self.unhilight(a)
	
	
	def load_buttons(self):
		cbControllerButtons = self.builder.get_object("cbControllerButtons")
		self._groups = {}
		model = cbControllerButtons.get_model()
		groups = json.loads(open(os.path.join(self.app.imagepath,
			"button-images", "groups.json"), "r").read())
		for group in groups:
			images = [ GdkPixbuf.Pixbuf.new_from_file(os.path.join(
				self.app.imagepath, "button-images", "%s.svg" % (b, )))
				for b in group['buttons'][0:4] ]
			model.append( [group['key']] + images )
			self._groups[group['key']] = group['buttons']
		cbControllerButtons.set_active(0)
	
	
	def save_registration(self):
		config = dict(
			buttons = {},
			axes = {},
		)
		for code, target in self._mappings.iteritems():
			if target in SCButtons:
				config['buttons'][code] = nameof(target)
			elif isinstance(target, AxisData):
				index = self._axis_data.index(target)
				target_axis, xy = AXIS_ORDER[index]
				min, max = target.min, target.max
				if target.invert:
					min, max = max, min
				# Center is choosen with assumption that all sticks are left
				# in center position before 'Save' is pressed.
				center = target.pos
				if center > 0 : center += 1
				if center < 0 : center -= 1
				config['axes'][code] = dict(
					axis = target_axis,
					min = min,
					max = max,
					center = center,
				)
		try:
			os.makedirs(os.path.join(get_config_path(), "devices"))
		except: pass
		config_file = os.path.join(get_config_path(), "devices",
			"%s.json" % (self._evdevice.name.strip(),))
		
		open(config_file, "w").write(json.dumps(config))
		log.debug("Evdev controller configuration '%s' written", config_file)
	
	
	def on_btNext_clicked(self, *a):
		stDialog = self.builder.get_object("stDialog")
		cbEmulateC = self.builder.get_object("cbEmulateC")
		btBack = self.builder.get_object("btBack")
		btNext = self.builder.get_object("btNext")
		pages = stDialog.get_children()
		index = pages.index(stDialog.get_visible_child())
		if index == 0:
			stDialog.set_visible_child(pages[1])
			self.load_buttons()
			self.refresh_controller_image()
			btBack.set_sensitive(True)
		elif index == 1:
			fxController = self.builder.get_object("fxController")
			self._controller.get_parent().remove(self._controller)
			fxController.add(self._controller)
			self.start_evdev_read()
			stDialog.set_visible_child(pages[2])
			cbEmulateC.grab_focus()
			btNext.set_label("_Save")
		elif index == 2:
			self.save_registration()
	
	
	def on_btBack_clicked(self, *a):
		stDialog = self.builder.get_object("stDialog")
		btBack = self.builder.get_object("btBack")
		btNext = self.builder.get_object("btNext")
		pages = stDialog.get_children()
		index = pages.index(stDialog.get_visible_child())
		if index == 1:
			stDialog.set_visible_child(pages[0])
			btBack.set_sensitive(False)
			btNext.set_sensitive(True)
		elif index == 2:
			stDialog.set_visible_child(pages[1])
			rvController = self.builder.get_object("rvController")
			self._controller.get_parent().remove(self._controller)
			rvController.add(self._controller)
			btNext.set_label("_Next")
	
	
	def cbInvert_toggled_cb(self, cb, *a):
		index = int(cb.get_name().split("_")[-1])
		self._axis_data[index].invert = cb.get_active()
	
	
	def start_evdev_read(self):
		tvDevices = self.builder.get_object("tvDevices")
		model, iter = tvDevices.get_selection().get_selected()
		self._evdevice = evdev.InputDevice(model[iter][0])
		if not self._mappings:
			self._mappings = {}
			if not self.load_sdl_mappings(self._evdevice):
				self.generate_mappings(self._evdevice)
			self.generate_unassigned()
		GLib.idle_add(self._evdev_read)
	
	
	def stop_evdev_read(self, *a):
		self._evdevice = None
	
	
	def _evdev_read(self):
		if self._evdevice:
			event = self._evdevice.read_one()
			if event:
				if event.type == evdev.ecodes.EV_KEY:
					self.evdev_button(event)
				if event.type == evdev.ecodes.EV_ABS:
					self.evdev_abs(event)
			return True
		return False
	
	
	def evdev_button(self, event):
		if self._grabber:
			return self._grabber.evdev_button(event)
		
		what = self._mappings.get(event.code)
		if isinstance(what, AxisData):
			if event.value:
				self.hilight_axis(what, STICK_PAD_MAX)
			else:
				self.hilight_axis(what, STICK_PAD_MIN)
		if isinstance(what, DPadEmuData):
			if event.value:
				if what.positive:
					self.hilight_axis(what.axis_data, STICK_PAD_MAX)
				else:
					self.hilight_axis(what.axis_data, STICK_PAD_MIN)
			else:
				self.hilight_axis(what.axis_data, 0)
		elif what is not None:
			if event.value:
				self.hilight(nameof(what))
			else:
				self.unhilight(nameof(what))
	
	
	def evdev_abs(self, event):
		self._input_axes[event.code] = event.value
		if self._grabber:
			return self._grabber.evdev_abs(event)
		
		axis = self._mappings.get(event.code)
		if axis:
			self.hilight_axis(axis, event.value)
	
	
	def hilight_axis(self, axis, value):
		cursor = axis.cursor
		if cursor is None:
			value = clamp(STICK_PAD_MIN,
					axis.set_position(value), STICK_PAD_MAX)
			# In this very specific case, trigger uses same min/max as stick
			if value > STICK_PAD_MAX * 2 / 3:
				self.hilight(axis.area, self.OBSERVE_COLORS[0])
			elif value > STICK_PAD_MAX * 1 / 3:
				self.hilight(axis.area, self.OBSERVE_COLORS[1])
			elif value > 0:
				self.hilight(axis.area, self.OBSERVE_COLORS[2])
			elif value > STICK_PAD_MIN * 1 / 3:
				self.hilight(axis.area, self.OBSERVE_COLORS[3])
			elif value > STICK_PAD_MIN * 2 / 3:
				self.hilight(axis.area, self.OBSERVE_COLORS[4])
			else:
				self.unhilight(axis.area)
		else:
			parent = cursor.get_parent()
			if parent is None:
				parent = self._controller.get_parent()
				parent.add(cursor)
				cursor.show()
			# Make position
			cursor.position[axis.xy] = clamp(STICK_PAD_MIN,
					axis.set_position(value), STICK_PAD_MAX)
			px, py = cursor.position
			# Grab values
			ax, ay, aw, trash = self._controller.get_area_position(axis.area)
			cw = cursor.get_allocation().width
			# Compute center
			x, y = ax + aw * 0.5 - cw * 0.5, ay + aw * 0.5 - cw * 0.5
			# Add pad position
			x += px * aw / STICK_PAD_MAX * 0.5
			y += py * aw / STICK_PAD_MAX * 0.5
			# Move circle
			parent.move(cursor, x, y)
	
	
	def hilight(self, what, color=None):
		self._hilights[what] = color or self.OBSERVE_COLORS[0]
		self._controller.hilight(self._hilights)
	
	
	def unhilight(self, what):
		if what in self._hilights:
			del self._hilights[what]
		if what in self._unassigned:
			self._hilights[what] = self.UNASSIGNED_COLOR
		self._controller.hilight(self._hilights)
	
	
	def on_area_hover(self, trash, what):
		self.on_area_leave()
		self._hilighted_area = what
		self.hilight(what, self.app.HILIGHT_COLOR)
	
	
	def on_area_leave(self, *a):
		if self._hilighted_area:
			self.unhilight(self._hilighted_area)
			self._hilighted_area = None
	
	
	def on_area_click(self, trash, what):
		stDialog = self.builder.get_object("stDialog")
		pages = stDialog.get_children()
		index = pages.index(stDialog.get_visible_child())
		if index == 2:
			if what in STICK_PAD_AREAS:
				area_name, axes = STICK_PAD_AREAS[what]
				mnuStick = self.builder.get_object("mnuStick")
				mnuStick._what = what
				mnuStick._axes = [ self._axis_data[index] for index in axes ]
				mnuStick.popup(None, None, None, None, 1, Gtk.get_current_event_time())
			elif what in TRIGGER_AREAS:
				self._grabber = TriggerGrabber(self, self._axis_data[TRIGGER_AREAS[what]])
			elif hasattr(SCButtons, what):
				self._grabber = InputGrabber(self, getattr(SCButtons, what))
	
	
	def on_mnuStickPress_activate(self, *a):
		mnuStick = self.builder.get_object("mnuStick")
		self._grabber = InputGrabber(self, getattr(SCButtons, mnuStick._what),
				text=_("Press stick or button..."))
	
	
	def on_mnuStickmove_activate(self, *a):
		mnuStick = self.builder.get_object("mnuStick")
		self._grabber = StickGrabber(self, mnuStick._axes)
	
	
	def on_btCancelInput_clicked(self, *a):
		if self._grabber:
			self._grabber.cancel()
	
	
	def refresh_devices(self, *a):
		log.debug("Refreshing device list")
		lstDevices = self.builder.get_object("lstDevices")
		cbShowAllDevices = self.builder.get_object("cbShowAllDevices")
		lstDevices.clear()
		for fname in evdev.list_devices():
			dev = evdev.InputDevice(fname)
			is_gamepad = ControllerRegistration.does_he_looks_like_a_gamepad(dev)
			if not dev.phys:
				# Skipping over virtual devices so list doesn't show
				# gamepads emulated by SCC
				continue
			if is_gamepad or cbShowAllDevices.get_active():
				lstDevices.append(( fname, dev.name,
					self._gamepad_icon if is_gamepad else self._other_icon ))
	
	
	def fill_button_images(self, image, buttons):
		e = image.edit()
		SVGEditor.update_parents(e)
		target = SVGEditor.get_element(e, "controller")
		for i in xrange(len(BUTTONS_WITH_IMAGES)):
			b = nameof(BUTTONS_WITH_IMAGES[i])
			try:
				elm = SVGEditor.get_element(e, "AREA_%s" % (b,))
				if elm is None:
					log.warning("Area for button %s not found", b)
					continue
				x, y = SVGEditor.get_translation(elm)
				path = os.path.join(self.app.imagepath, "button-images",
					"%s.svg" % (buttons[i], ))
				img = SVGEditor.get_element(SVGEditor.load_from_file(path), "button")
				img.attrib["transform"] = "translate(%s, %s)" % (x, y)
				img.attrib["id"] = b
				SVGEditor.add_element(target, img)
			except Exception, err:
				log.warning("Failed to add image for button %s", b)
				log.exception(err)
		e.commit()
	
	
	def refresh_controller_image(self, *a):
		cbControllerButtons = self.builder.get_object("cbControllerButtons")
		imgControllerType = self.builder.get_object("imgControllerType")
		cbControllerType = self.builder.get_object("cbControllerType")
		rvController = self.builder.get_object("rvController")
		
		group = cbControllerButtons.get_model()[cbControllerButtons.get_active()][0]
		controller = cbControllerType.get_model()[cbControllerType.get_active()][0]
		
		image = os.path.join(self.app.imagepath,
			"controller-images/%s.svg" % (controller, ))
		if self._controller:
			self._controller.set_image(image)
			self.fill_button_images(self._controller, self._groups[group])
			self._controller.hilight({})
		else:
			self._controller = SVGWidget(self.app, image)
			self._controller.connect('hover', self.on_area_hover)
			self._controller.connect('leave', self.on_area_leave)
			self._controller.connect('click', self.on_area_click)
			rvController.add(self._controller)
		rvController.set_reveal_child(True)


class AxisData(object):
	"""
	(Almost) dumb container.
	Stores position, center and limits for single axis.
	"""
	
	def __init__(self, name, xy, min=STICK_PAD_MAX, max=STICK_PAD_MIN):
		self.name = name
		self.area = name.split("_")[0].upper()
		if self.area.endswith("TRIG"): self.area = self.area[0:-3]
		self.xy = xy
		self.pos = 0
		self.center = 0
		self.min = min
		self.max = max
		self.invert = False
		self.cursor = None
	
	
	def reset(self):
		"""
		Resets min and max value so axis can (has to be) recalibrated again
		"""
		self.min = STICK_PAD_MAX
		self.max = STICK_PAD_MIN
	
	
	def __repr__(self):
		return "<Axis data '%s'>" % (self.name, )
	
	
	def set_position(self, value):
		"""
		Returns current position
		translated to range of (STICK_PAD_MIN, STICK_PAD_MAX)
		"""
		self.min = min(self.min, value)
		self.max = max(self.max, value)
		self.pos = value
		try:
			r = (STICK_PAD_MAX - STICK_PAD_MIN) / (self.max - self.min)
			v = (self.pos - self.min) * r
			if self.invert:
				return STICK_PAD_MAX - v
			else:
				return v + STICK_PAD_MIN
		except ZeroDivisionError:
			return 0


class DPadEmuData(object):
	"""
	Dumb container that stores dpad emulation data.
	DPAd emulation is used, for example, on PS3 controller, where dpad does not
	inputs as 2 axes, but as 4 buttons.
	
	This class stores mapping of one button to one half of axis.
	"""
	
	def __init__(self, axis_data, positive):
		self.axis_data = axis_data
		self.positive  = positive


class InputGrabber(object):
	"""
	Base class for input grabbing. Waits for physical button being pressed
	by default.
	"""
	
	def __init__(self, parent, what, text=_("Press a button...")):
		self.parent = parent
		self.what = what
		self.set_message(text)
		self.dlgPressButton = parent.builder.get_object("dlgPressButton")
		self.dlgPressButton.show()
	
	
	def set_message(self, text):
		self.parent.builder.get_object("lblPressButton").set_text(text)
	
	
	def cancel(self):
		self.dlgPressButton.hide()
		self.parent._grabber = None
	
	
	def evdev_button(self, event):
		if event.value != 0:
			return
		self.set_mapping(event.code, self.what)
	
	
	def set_mapping(self, keycode, what):
		parent = self.parent
		
		parent._mappings[keycode] = what
		log.debug("Reassigned %s to %s", keycode, what)
		
		if nameof(what) in parent._unassigned:
			parent._unassigned.remove(nameof(what))
			parent.unhilight(nameof(what))
		
		self.parent.generate_unassigned()
		self.cancel()
	
	
	def evdev_abs(self, event):
		pass


class TriggerGrabber(InputGrabber):
	"""
	InputGrabber modified to grab trigger bindings.
	That may be button or axis with at least 0-250 range is accepted.
	"""
	def __init__(self, parent, what, text=_("Pull a trigger...")):
		InputGrabber.__init__(self, parent, what, text)
		self.orig_pos = { k: parent._input_axes[k] for k in parent._input_axes }
		self.new_pos  = { k: parent._input_axes[k] for k in parent._input_axes }
	
	
	def evdev_abs(self, event):
		if event.code > 50:
			# TODO: Remove this condition
			return
		self.new_pos[event.code] = event.value
		if event.code not in self.orig_pos:
			self.orig_pos[event.code] = 0
		
		# Get avgerage absolute change for all axes
		avg = float(sum([
				abs( self.orig_pos[k] - self.new_pos[k] )
				for k in self.new_pos
			])) / float(len(self.new_pos))
		
		# Get absolute change for _this_ axis
		change = abs( self.orig_pos[event.code] - self.new_pos[event.code] )
		if change > 2 and change > avg * 0.5:
			# TODO: change > 2 may be too strict
			# if there is pad going from -1 to 1 somewhere around
			self.abs_change(event, change)
	
	
	def abs_change(self, event, change):
		if event.value > 250:
			self.what.reset()
			self.set_mapping(event.code, self.what)
			self.parent.generate_unassigned()
			self.cancel()


class StickGrabber(TriggerGrabber):
	"""
	InputGrabber modified to grab stick or pad bindings, in two phases for
	both X and Y axis.
	"""
	
	def __init__(self, parent, what):
		TriggerGrabber.__init__(self, parent, what,
				text=_("Move stick left and right..."))
		self.xy = X
		self.grabbed = [ None, None ]
	
	
	def evdev_button(self, event):
		#if len(self.grabbed) == 2 and self.grabbed[X] != None:
		#	# Already grabbed one axis, don't grab buttons
		#	return
		if event.code in self.grabbed:
			# Don't allow same button to be used twice
			return
		if event.value == 0:
			if len(self.grabbed) < 4:
				self.grabbed = [ None ] * 4
			if self.grabbed[0] is None:
				self.grabbed[0] = event.code
				self.set_message(_("Move DPAD to right"))
			elif self.grabbed[1] is None:
				self.grabbed[1] = event.code
				self.set_message(_("Move DPAD up"))
			elif self.grabbed[2] is None:
				self.grabbed[2] = event.code
				self.set_message(_("Move DPAD down"))
			elif self.grabbed[3] is None:
				self.grabbed[3] = event.code
				self.set_message(str(self.grabbed))
				grabbed = [] + self.grabbed
				for w in self.what:
					for negative in (False, True):
						keycode, grabbed = grabbed[0], grabbed[1:]
						w.reset()
						self.set_mapping(keycode, DPadEmuData(w, negative))
				self.parent.generate_unassigned()
				self.cancel()
	
	
	def abs_change(self, event, change):
		if len(self.grabbed) > 2:
			# Already started grabbing 4 buttons, don't grab axes now
			return
		if self.xy == X:
			self.grabbed[X] = event.code
			self.xy = Y
			self.set_message(_("Move stick up and down..."))
		else:
			if event.code != self.grabbed[X]:
				self.grabbed[Y] = event.code
				for i in xrange(len(self.grabbed)):
					self.what[i].reset()
					self.set_mapping(self.grabbed[i], self.what[i])
				self.parent.generate_unassigned()
				self.cancel()
