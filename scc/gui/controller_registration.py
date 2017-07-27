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
from scc.gui.svg_widget import SVGWidget, SVGEditor
from scc.gui.editor import Editor
from scc.constants import SCButtons, STICK_PAD_MAX, STICK_PAD_MIN
from scc.constants import STICK, LEFT, RIGHT
from scc.paths import get_config_path
from scc.tools import nameof

import evdev
import sys, os, logging, json, traceback
log = logging.getLogger("CR")

X = 0
Y = 1

# TODO: SCButtons.STICK is missing from BUTTON_ORDER, it conflicts with STICK in
#       AXIS_ORDER. I really have to rename it...
BUTTON_ORDER = ( SCButtons.A, SCButtons.B, SCButtons.X, SCButtons.Y,
	SCButtons.C, SCButtons.LB, SCButtons.RB, SCButtons.BACK, SCButtons.START,
	SCButtons.RPAD, SCButtons.LPAD, SCButtons.RGRIP,
	SCButtons.LGRIP )
AXIS_ORDER = (
	("stick_x", X), ("stick_y", Y),
	("rpad_x", X),  ("rpad_y", Y),
	("lpad_x", X),  ("lpad_x", Y),
	("ltrig", X),
	("rtrig", X)
)
BUTTONS_WITH_IMAGES = ( SCButtons.A, SCButtons.B, SCButtons.X, SCButtons.Y,
	SCButtons.BACK, SCButtons.C, SCButtons.START )

class ControllerRegistration(Editor):
	GLADE = "controller_registration.glade"
	UNASSIGNED_COLOR = "#FFFF0000"		# ARGB
	
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
		self._waits_for_input = None
		self._mappings = {}
		self._hilights = {}
		self._unassigned = set()
		self._hilighted_area = None
		self.refresh_devices()
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		cursors = {}
		for axis in self._axis_data:
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
	
	
	def generate_mappings(self, dev):
		"""
		Generates initial mappings, just to have some preset to show.
		"""
		caps = dev.capabilities(verbose=False)
		self._mappings = {}
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
		self._unassigned.clear()
		for a in BUTTON_ORDER:
			if a not in self._mappings.values():
				self._unassigned.add(nameof(a))
		for a in self._axis_data:
			if a not in self._mappings.values():
				self._unassigned.add(nameof(a))
		
		for a in self._unassigned:
			self.hilight(a, self.UNASSIGNED_COLOR)
	
	
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
		what = self._mappings.get(event.code)
		if self._waits_for_input:
			self._input(event.code)
		elif what is not None and event.value:
			self.hilight(nameof(what))
		elif what is not None:
			self.unhilight(nameof(what))
	
	
	def evdev_abs(self, event):
		axis = self._mappings.get(event.code)
		if axis:
			cursor = axis.cursor
			parent = cursor.get_parent()
			if parent is None:
				parent = self._controller.get_parent()
				parent.add(cursor)
				cursor.show()
			# Make position
			cursor.position[axis.xy] = axis.set_position(event.value)
			px, py = cursor.position
			# Grab values
			ax, ay, aw, trash = self._controller.get_area_position(axis.area)
			cw = cursor.get_allocation().width
			# Compute center
			x, y = ax + aw * 0.5 - cw * 0.5, ay + aw * 0.5 - cw * 0.5
			# Add pad position
			x += px * aw / STICK_PAD_MAX * 0.5
			y -= py * aw / STICK_PAD_MAX * 0.5
			# Move circle
			parent.move(cursor, x, y)
	
	
	def hilight(self, what, color=None):
		self._hilights[what] = color or self.app.OBSERVE_COLOR
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
			if hasattr(SCButtons, what):
				self._waits_for_input = getattr(SCButtons, what)
				dlgPressButton = self.builder.get_object("dlgPressButton")
				dlgPressButton.show()
	
	
	def _input(self, keycode):
		if self._waits_for_input:
			what, self._waits_for_input = self._waits_for_input, None
			old = self._mappings.get(keycode)
			
			self._mappings[keycode] = what
			log.debug("Reassigned %s to %s", keycode, what)
			
			if nameof(what) in self._unassigned:
				self._unassigned.remove(nameof(what))
				self.unhilight(nameof(what))
			
			if old is not None and old not in self._mappings.values():
				log.debug("Nothing now maps to %s", old)
				self._unassigned.add(nameof(old))
				self.unhilight(nameof(old))
			
			self.on_btCancelInput_clicked()
	
	
	def on_btCancelInput_clicked(self, *a):
		self._waits_for_input = None
		dlgPressButton = self.builder.get_object("dlgPressButton")
		dlgPressButton.hide()
	
	
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


class AxisData:
	"""
	(Almost) dumb container.
	Stores position, center and limits for single axis.
	"""
	
	def __init__(self, name, xy, min=STICK_PAD_MAX, max=-STICK_PAD_MAX):
		self.name = name
		self.area = name.split("_")[0].upper()
		self.xy = xy
		self.pos = 0
		self.center = 0
		self.min = min
		self.max = max
		self.invert = False
		self.cursor = None
	
	
	def set_position(self, value):
		"""
		Returns current position
		translated to range of (STICK_PAD_MIN, STICK_PAD_MAX)
		"""
		self.min = min(self.min, value)
		self.max = max(self.max, value)
		self.pos = value
		try:
			if self.invert:
				return ( STICK_PAD_MAX - self.pos
					* (STICK_PAD_MAX - STICK_PAD_MIN) / (self.max - self.min) )
			else:
				return ( STICK_PAD_MIN + self.pos
					* (STICK_PAD_MAX - STICK_PAD_MIN) / (self.max - self.min) )
		except ZeroDivisionError:
			return 0
