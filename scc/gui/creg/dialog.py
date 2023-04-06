#!/usr/bin/env python2
"""
SC-Controller - Controller Registration 

Dialog that asks a lot of question to create configuration node in config file.
Most "interesting" thing here may be that this works 100% independently from
daemon.
"""

from scc.tools import _

from gi.repository import Gtk, GLib, GdkPixbuf
from scc.gui.creg.constants import SDL_TO_SCC_NAMES, STICK_PAD_AREAS
from scc.gui.creg.constants import AXIS_ORDER, SDL_AXES, SDL_DPAD
from scc.gui.creg.constants import BUTTON_ORDER, TRIGGER_AREAS
from scc.gui.creg.grabs import InputGrabber, TriggerGrabber, StickGrabber
from scc.gui.creg.data import AxisData, DPadEmuData
from scc.gui.creg.tester import Tester
from scc.gui.controller_image import ControllerImage
from scc.gui.editor import Editor
from scc.gui.app import App
from scc.constants import SCButtons, STICK_PAD_MAX, STICK_PAD_MIN
from scc.paths import get_config_path, get_share_path
from scc.tools import nameof, clamp
from scc.config import Config

import evdev
import os, logging, json, re
log = logging.getLogger("CRegistration")


class ControllerRegistration(Editor):
	GLADE = "creg.glade"
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
		self._controller_image = None
		self._evdevice = None
		self._tester = None
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
		self.builder.get_object("cbInvert_1").set_active(True)
		self.builder.get_object("cbInvert_3").set_active(True)
		self.builder.get_object("cbInvert_5").set_active(True)
	
	
	@staticmethod
	def does_he_looks_like_a_gamepad(dev):
		"""
		Examines device capabilities and decides if it passes for gamepad.
		Device is considered gamepad-like if has at least one button with
		keycode in gamepad range and at least two axes.
		"""

		# Strip special symbols
		name = re.sub( r"[^a-zA-Z0-9.]+", ' ', dev.name.lower() )

		# ... but some cheating first
		if "keyboard" in name:
			return False
		if "touchpad" in name:
			return False
		if "mouse" in name:
			return False
		if "gamepad" in name:
			return True
		caps = dev.capabilities(verbose=False)
		if evdev.ecodes.EV_ABS in caps: # Has axes
			if evdev.ecodes.EV_KEY in caps: # Has buttons
				for button in caps[evdev.ecodes.EV_KEY]:
					if button >= evdev.ecodes.BTN_0 and button <= evdev.ecodes.BTN_GEAR_UP:
						return True
		return False
	
	
	def load_sdl_mappings(self):
		"""
		Attempts to load mappings from gamecontrollerdb.txt.
		
		Return True on success.
		"""
		# Build list of button and axes
		buttons = self._tester.buttons
		axes = self._tester.axes
		
		# Generate database ID
		wordswap = lambda i: ((i & 0xFF) << 8) | ((i & 0xFF00) >> 8)
		# TODO: version?
		weird_id = "%.4x%.8x%.8x%.8x0000" % (
				wordswap(self._evdevice.info.bustype),
				wordswap(self._evdevice.info.vendor),
				wordswap(self._evdevice.info.product),
				wordswap(self._evdevice.info.version)
		)
		
		# Search in database
		try:
			db = open(os.path.join(get_share_path(), "gamecontrollerdb.txt"), "r")
		except Exception as e:
			log.error('Failed to load gamecontrollerdb')
			log.exception(e)
			return False
		
		for line in db.readlines():
			if line.startswith(weird_id):
				log.info("Loading mappings for '%s' from gamecontrollerdb", weird_id)
				log.debug("Buttons: %s", buttons)
				log.debug("Axes: %s", axes)
				for token in line.strip().split(","):
					if ":" in token:
						k, v = token.split(":", 1)
						k = SDL_TO_SCC_NAMES.get(k, k)
						if v.startswith("b") and hasattr(SCButtons, k.upper()):
							try:
								keycode = buttons[int(v.strip("b"))]
							except IndexError:
								log.warning("Skipping unknown gamecontrollerdb button->button mapping: '%s'", v)
								continue
							button  = getattr(SCButtons, k.upper())
							self._mappings[keycode] = button
						elif v.startswith("b") and k in SDL_AXES:
							try:
								keycode = buttons[int(v.strip("b"))]
							except IndexError:
								log.warning("Skipping unknown gamecontrollerdb button->axis mapping: '%s'", v)
								continue
							log.info("Adding button -> axis mapping for %s", k)
							self._mappings[keycode] = self._axis_data[SDL_AXES.index(k)]
							self._mappings[keycode].min = STICK_PAD_MIN
							self._mappings[keycode].max = STICK_PAD_MAX
						elif v.startswith("h") and 16 in axes and 17 in axes:
							# Special case for evdev hatswitch
							if v == "h0.1" and k == "dpup":
								self._mappings[16] = self._axis_data[SDL_AXES.index("dpadx")]
								self._mappings[17] = self._axis_data[SDL_AXES.index("dpady")]
						elif k in SDL_AXES: 
							try:
								code = axes[int(v.strip("a"))]
							except IndexError:
								log.warning("Skipping unknown gamecontrollerdb axis: '%s'", v)
								continue
							self._mappings[code] = self._axis_data[SDL_AXES.index(k)]
						elif k in SDL_DPAD and v.startswith("b"):
							try:
								keycode = buttons[int(v.strip("b"))]
							except IndexError:
								log.warning("Skipping unknown gamecontrollerdb button->dpad mapping: %s", v)
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
		else:
			log.debug("Mappings for '%s' not found in gamecontrollerdb", weird_id)
		
		return False
	
	
	def generate_mappings(self):
		"""
		Generates initial mappings, just to have some preset to show.
		"""
		buttons = list(BUTTON_ORDER)
		axes = list(self._axis_data)
		log.info("Generating default mappings")
		log.debug("Buttons: %s", self._tester.buttons)
		log.debug("Axes: %s", self._tester.axes)
		for axis in self._tester.axes:
			self._mappings[axis], axes = axes[0], axes[1:]
			if len(axes) == 0: break
		for button in self._tester.buttons:
			self._mappings[button], buttons = buttons[0], buttons[1:]
			if len(buttons) == 0: break
	
	
	def generate_unassigned(self):
		unassigned = set()
		unassigned.clear()
		assigned_axes = set([ x for x in list(self._mappings.values())
							if isinstance(x, AxisData) ])
		assigned_axes.update([ x.axis_data for x in list(self._mappings.values())
							if isinstance(x, DPadEmuData) ])
		assigned_buttons = set([ x for x in list(self._mappings.values())
							if x in list(SCButtons.__members__.values()) ])
		assigned_buttons.update([ x.button for x in list(self._mappings.values())
							if isinstance(x, DPadEmuData) ])
		for a in BUTTON_ORDER:
			if a not in assigned_buttons:
				if a not in (SCButtons.RGRIP, SCButtons.LGRIP):
					# Grips are not colored red as most of controllers doesn't
					# have them anyway
					unassigned.add(nameof(a))
		for a in TRIGGER_AREAS:
			axis = self._axis_data[TRIGGER_AREAS[a]]
			if axis in assigned_axes and a in unassigned:
				unassigned.remove(a)
			elif axis not in assigned_axes:
				unassigned.add(a)
		for a in STICK_PAD_AREAS:
			area_name, axes = STICK_PAD_AREAS[a]
			has_mapping = bool(sum([
				self._axis_data[index] in assigned_axes for index in axes ]))
			if not has_mapping:
				unassigned.add(area_name)
		
		hilight = unassigned - self._unassigned
		unhilight = self._unassigned - unassigned
		self._unassigned = unassigned
		for a in hilight:   self.hilight(a, self.UNASSIGNED_COLOR)
		for a in unhilight: self.unhilight(a)
	
	
	def generate_raw_data(self):
		cbControllerButtons = self.builder.get_object("cbControllerButtons")
		cbControllerType = self.builder.get_object("cbControllerType")
		buffRawData = self.builder.get_object("buffRawData")
		config = dict(
			buttons = {},
			axes = {},
			dpads = {},
		)
		
		
		def axis_to_json(axisdata):
			index = self._axis_data.index(axisdata)
			target_axis, xy = AXIS_ORDER[index]
			min, max = axisdata.min, axisdata.max
			if axisdata.invert:
				min, max = max, min
			
			rv = dict(
				axis = target_axis,
				min = min,
				max = max
			)
			if target_axis not in ("ltrig", "rtrig"):
				# Deadzone is generated with assumption that all sticks are left
				# in center position before 'Save' is pressed.
				center = axisdata.min + (axisdata.max - axisdata.min) / 2
				deadzone = abs(axisdata.pos - center) * 2 + 2
				if abs(axisdata.max) < 2:
					# DPADs
					deadzone = 0
				rv["deadzone"] = deadzone
			
			return rv
		
		for code, target in self._mappings.items():
			if target in SCButtons:
				config['buttons'][code] = nameof(target)
			elif isinstance(target, DPadEmuData):
				config['dpads'][code] = axis_to_json(target.axis_data)
				config['dpads'][code]["positive"] = target.positive
				config['dpads'][code]["button"] = nameof(target.button)
			elif isinstance(target, AxisData):
				config['axes'][code] = axis_to_json(target)
		
		group = cbControllerButtons.get_model()[cbControllerButtons.get_active()][0]
		controller = cbControllerType.get_model()[cbControllerType.get_active()][0]
		config['gui'] = {
			'background' : controller,
			'buttons': self._groups[group]
		}
		
		buffRawData.set_text(json.dumps(config, sort_keys=True,
						indent=4, separators=(',', ': ')))
	
	
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
		self.generate_raw_data()
		buffRawData = self.builder.get_object("buffRawData")
		jsondata = buffRawData.get_text(buffRawData.get_start_iter(),
			buffRawData.get_end_iter(), True)
		try:
			os.makedirs(os.path.join(get_config_path(), "devices"))
		except: pass
		
		filename = self._evdevice.name.decode("utf-8").strip().replace("/","")
		if self._tester.driver == "hid":
			filename = "%.4x:%.4x-%s" % (self._evdevice.info.vendor,
				self._evdevice.info.product, filename)
		
		config_file = os.path.join(get_config_path(), "devices",
				"%s-%s.json" % (self._tester.driver, filename,))
		
		open(config_file, "w").write(jsondata)
		log.debug("Controller configuration '%s' written", config_file)
		
		self.kill_tester()
		self.window.destroy()
		GLib.timeout_add_seconds(1, self.app.dm.rescan)
	
	
	def on_buffRawData_changed(self, buffRawData, *a):
		btNext = self.builder.get_object("btNext")
		jsondata = buffRawData.get_text(buffRawData.get_start_iter(),
			buffRawData.get_end_iter(), True)
		try:
			json.loads(jsondata)
			btNext.set_sensitive(True)
		except Exception as e:
			# User can modify generated json code before hitting save,
			# but if he writes something unparsable, save button is disabled
			btNext.set_sensitive(False)
	
	
	def on_ibHIDWarning_response(self, *a):
		rvHIDWarning = self.builder.get_object("rvHIDWarning")
		rvHIDWarning.set_reveal_child(False)
	
	
	def on_btNext_clicked(self, *a):
		rvController = self.builder.get_object("rvController")
		tvDevices = self.builder.get_object("tvDevices")
		stDialog = self.builder.get_object("stDialog")
		btBack = self.builder.get_object("btBack")
		btNext = self.builder.get_object("btNext")
		pages = stDialog.get_children()
		index = pages.index(stDialog.get_visible_child())
		if index == 0:
			model, iter = tvDevices.get_selection().get_selected()
			dev = evdev.InputDevice(model[iter][0])
			if (dev.info.vendor, dev.info.product) == (0x054c, 0x09cc):
				# Special case for PS4 controller
				cbDS4 = self.builder.get_object("cbDS4")
				imgDS4 = self.builder.get_object("imgDS4")
				imgDS4.set_from_file(os.path.join(
						self.app.imagepath, "ds4-small.svg"))
				cbDS4.set_active(Config()['drivers']['ds4drv'])
				stDialog.set_visible_child(pages[3])
				btBack.set_sensitive(True)
				btNext.set_label("_Restart Emulation")
				return
			stDialog.set_visible_child(pages[1])
			self.load_buttons()
			self.refresh_controller_image()
			rvController.set_reveal_child(True)
			self.load_buttons()
			self.refresh_controller_image()
			btBack.set_sensitive(True)
		elif index == 1:
			# Disable Next button and determine which driver should be used
			btNext.set_sensitive(False)
			model, iter = tvDevices.get_selection().get_selected()
			dev = evdev.InputDevice(model[iter][0])
			self.prepare_registration(dev)
		elif index == 2:
			self.save_registration()
		elif index == 3:
			# Next pressed on DS4 info page
			# where it means 'Restart Emulation and close'
			self.app.dm.stop()
			GLib.timeout_add_seconds(1, self.app.dm.start)
			self.kill_tester()
			self.window.destroy()
	
	
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
			self._controller_image.get_parent().remove(self._controller_image)
			rvController.add(self._controller_image)
			btNext.set_label("_Next")
		elif index == 3:
			stDialog.set_visible_child(pages[0])
			btNext.set_label("_Next")
			btBack.set_sensitive(False)
			btNext.set_sensitive(True)
	
	
	def on_cbDS4_toggled(self, button):
		config = Config()
		config['drivers']['ds4drv'] = button.get_active()
		config.save()
	
	
	def prepare_registration(self, dev):
		self._evdevice = dev
		self.set_hid_enabled(True)
		
		def retry_with_evdev(tester, code):
			if tester:
				for s in tester.__signals: tester.disconnect(s)
				tester.stop()
			self.set_hid_enabled(False)
			if code != 0:
				log.error("HID driver test failed (code %s)", code)
			if code == 2:
				# Special case, device may be usable, but there is no access
				rvHIDWarning = self.builder.get_object("rvHIDWarning")
				rvHIDWarning.set_reveal_child(False)
			log.debug("Trying to use '%s' with evdev driver...", dev.fn)
			self._tester = Tester("evdev", dev.fn)
			self._tester.__signals = [
				self._tester.connect('ready', self.on_registration_ready),
				self._tester.connect('error', self.on_device_open_failed)
			]
			self._tester.start()
		
		if dev.info.vendor == 0 and dev.info.product == 0:
			# Not an USB device, skip HID test altogether
			retry_with_evdev(None, 0)
		else:
			log.debug("Trying to use %.4x:%.4x with HID driver...",
					dev.info.vendor, dev.info.product)
			self._tester = Tester("hid", "%.4x:%.4x" % (dev.info.vendor, dev.info.product))
			self._tester.__signals = [
				self._tester.connect('ready', self.on_registration_ready),
				self._tester.connect('error', retry_with_evdev),
			]
			self._tester.start()
	
	
	def on_registration_ready(self, tester):
		cbAccessMode = self.builder.get_object("cbAccessMode")
		fxController = self.builder.get_object("fxController")
		cbEmulateC = self.builder.get_object("cbEmulateC")
		stDialog = self.builder.get_object("stDialog")
		btNext = self.builder.get_object("btNext")
		
		self.set_cb(cbAccessMode, tester.driver)
		cbAccessMode.set_sensitive(True)
		
		if not self._mappings:
			self._mappings = {}
			if not self.load_sdl_mappings():
				self.generate_mappings()
			self.generate_unassigned()
			self.generate_raw_data()
		
		for s in tester.__signals: tester.disconnect(s)
		tester.__signals = [
			tester.connect('axis', self.on_tester_axis),
			tester.connect('button', self.on_tester_button),
		]
		
		self._controller_image.get_parent().remove(self._controller_image)
		fxController.add(self._controller_image)
		pages = stDialog.get_children()
		stDialog.set_visible_child(pages[2])
		cbEmulateC.grab_focus()
		btNext.set_label("_Save")
		btNext.set_sensitive(True)
	
	
	def on_device_open_failed(self, *a):
		"""
		Called when all (or user-selected) driver fails
		to communicate with controller.
		
		Shoudln't be really possible, but something
		_has_ to happen in such case.
		"""
		d = Gtk.MessageDialog(parent=self.window,
			flags = Gtk.DialogFlags.MODAL,
			type = Gtk.MessageType.ERROR,
			buttons = Gtk.ButtonsType.OK,
			message_format = _("Failed to open device")
		)
		d.run()
		d.destroy()
		self.window.destroy()
	
	
	def kill_tester(self, *a):
		""" Called when window is closed """
		if self._tester:
			tester, self._tester = self._tester, None
			for s in tester.__signals: tester.disconnect(s)
			tester.stop()
	
	
	def set_hid_enabled(self, enabled):
		""" Enables or disables option to use HID driver """
		cbAccessMode = self.builder.get_object("cbAccessMode")
		for x in cbAccessMode.get_model():
			if x[0] == "hid":
				x[1] = _("USB HID (recommended)") if enabled else _("USB HID")
				x[2] = enabled
	
	
	def on_cbAccessMode_changed(self, cb):
		if self._tester:
			btNext = self.builder.get_object("btNext")
			target = cb.get_model().get_value(cb.get_active_iter(), 0)
			if self._tester.driver != target:
				# User changed driver that should be used, a lot of stuff has
				# to be restarted
				log.debug("User-requested driver change")
				self.kill_tester()
				cb.set_sensitive(False)
				btNext.set_sensitive(False)
				if target == "hid":
					self._tester = Tester("hid", "%.4x:%.4x" % (
						self._evdevice.info.vendor, self._evdevice.info.product))
				else:
					self._tester = Tester("evdev", self._evdevice.fn)
				self._tester.__signals = [
					self._tester.connect('ready', self.on_registration_ready),
					self._tester.connect('error', self.on_device_open_failed),
				]
				GLib.timeout_add_seconds(1, self._tester.start)
	
	
	def cbInvert_toggled_cb(self, cb, *a):
		index = int(cb.get_name().split("_")[-1])
		self._axis_data[index].invert = cb.get_active()
	
	
	def on_tester_button(self, tester, keycode, pressed):
		if self._grabber:
			return self._grabber.on_button(keycode, pressed)
		
		what = self._mappings.get(keycode)
		if isinstance(what, AxisData):
			if pressed:
				self.hilight_axis(what, STICK_PAD_MAX)
			else:
				self.hilight_axis(what, STICK_PAD_MIN)
		if isinstance(what, DPadEmuData):
			if pressed:
				self.hilight(nameof(what.button))
				if what.positive:
					self.hilight_axis(what.axis_data, STICK_PAD_MAX)
				else:
					self.hilight_axis(what.axis_data, STICK_PAD_MIN)
			else:
				self.unhilight(nameof(what.button))
				self.hilight_axis(what.axis_data, 0)
		elif what is not None:
			if pressed:
				self.hilight(nameof(what))
			else:
				self.unhilight(nameof(what))
	
	
	def on_tester_axis(self, tester, number, value):
		self._input_axes[number] = value
		if self._grabber:
			return self._grabber.on_axis(number, value)
		
		axis = self._mappings.get(number)
		if axis:
			self.hilight_axis(axis, value)
	
	
	def hilight_axis(self, axis, value):
		cursor = axis.cursor
		if cursor is None:
			changed, value = axis.set_position(value)
			value = clamp(STICK_PAD_MIN, value, STICK_PAD_MAX)
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
			# Update raw data if needed
			if changed:
				self.generate_raw_data()
		else:
			parent = cursor.get_parent()
			if parent is None:
				parent = self._controller_image.get_parent()
				parent.add(cursor)
				cursor.show()
			# Make position
			changed, value = axis.set_position(value)
			cursor.position[axis.xy] = clamp(STICK_PAD_MIN, value, STICK_PAD_MAX)
			px, py = cursor.position
			# Grab values
			try:
				trash, ay, trash, ah = self._controller_image.get_area_position(axis.area)
				ax, trash, aw, trash = self._controller_image.get_area_position(axis.area + "TEST")
			except ValueError:
				# Area not found
				cursor.set_visible(False)
				return
			cw = cursor.get_allocation().width
			# Compute center
			x, y = ax + aw * 0.5 - cw * 0.5, ay + aw * 0.5 - cw * 0.5
			# Add pad position
			x += px * aw / STICK_PAD_MAX * 0.5
			y -= py * aw / STICK_PAD_MAX * 0.5
			# Move circle
			parent.move(cursor, x, y)
			cursor.set_visible(True)
			# Update raw data if needed
			if changed:
				self.generate_raw_data()

	
	
	def hilight(self, what, color=None):
		self._hilights[what] = color or self.OBSERVE_COLORS[0]
		self._controller_image.hilight(self._hilights)
	
	
	def unhilight(self, what):
		if what in self._hilights:
			del self._hilights[what]
		if what in self._unassigned:
			self._hilights[what] = self.UNASSIGNED_COLOR
		self._controller_image.hilight(self._hilights)
	
	
	def on_exAdditionalOptions_activate(self, ex):
		rv = self.builder.get_object("rvAdditionalOptions")
		rv.set_reveal_child(not ex.get_expanded())
	
	
	def on_exRawData_activate(self, ex):
		rv = self.builder.get_object("rvRawData")
		dialog = self.builder.get_object("Dialog")
		rv.set_reveal_child(not ex.get_expanded())
		if not ex.get_expanded():
			dialog.set_resizable(True)
	
	
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
				mnuStick._what = "STICKPRESS" if what == "STICK" else what 
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
	
	
	def refresh_controller_image(self, *a):
		cbControllerButtons = self.builder.get_object("cbControllerButtons")
		cbControllerType = self.builder.get_object("cbControllerType")
		rvController = self.builder.get_object("rvController")
		group = cbControllerButtons.get_model()[cbControllerButtons.get_active()][0]
		controller = cbControllerType.get_model()[cbControllerType.get_active()][0]
		config = { 'gui' : { 'background' : controller, 'buttons': self._groups[group] }}
		
		if self._controller_image:
			self._controller_image.use_config(config)
		else:
			self._controller_image = ControllerImage(self.app)
			self._controller_image.connect('hover', self.on_area_hover)
			self._controller_image.connect('leave', self.on_area_leave)
			self._controller_image.connect('click', self.on_area_click)
			rvController.add(self._controller_image)
