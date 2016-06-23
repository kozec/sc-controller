#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Axis Component

Assigns emulated axis to trigger
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GdkX11, GLib
from ctypes import c_void_p, byref, cast, c_ulong, POINTER
from scc.actions import Action, NoAction, AxisAction, MouseAction, XYAction
from scc.actions import TrackballAction, TrackpadAction, CircularAction
from scc.actions import AreaAction, WinAreaAction, RelAreaAction, RelWinAreaAction
from scc.actions import ButtonAction
from scc.special_actions import OSDAction
from scc.uinput import Keys, Axes, Rels
from scc.constants import SCButtons
from scc.lib import xwrappers as X
from scc.osd.timermanager import TimerManager
from scc.osd.area import Area
from scc.gui.parser import GuiActionParser, InvalidAction
from scc.gui.ae import AEComponent

import os, logging
log = logging.getLogger("AE.AxisAction")

__all__ = [ 'AxisActionComponent' ]


class AxisActionComponent(AEComponent, TimerManager):
	GLADE = "ae/axis_action.glade"
	NAME = "axis_action"
	CTXS = Action.AC_STICK, Action.AC_PAD
	PRIORITY = 3
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		TimerManager.__init__(self)
		self._recursing = False
		self.relative_area = False
		self.osd_area_instance = None
		self.parser = GuiActionParser()
	
	
	def load(self):
		if self.loaded : return
		AEComponent.load(self)
		cbAreaType = self.builder.get_object("cbAreaType")
		cbAreaType.set_row_separator_func( lambda model, iter : model.get_value(iter, 0) == "-" )
	
	
	def hidden(self):
		self.update_osd_area(None)
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			cb = self.builder.get_object("cbAxisOutput")
			if isinstance(action, AreaAction):
				self.load_area_action(action)
				self.set_cb(cb, "area", 2)
				self.update_osd_area(action)
				return
			self.update_osd_area(None)
			if isinstance(action, TrackpadAction):
				self.set_cb(cb, "trackpad", 2)
			elif isinstance(action, TrackballAction):
				self.set_cb(cb, "trackball", 2)
			elif isinstance(action, CircularAction):
				self.set_cb(cb, "circular", 2)
			elif isinstance(action, XYAction):
				p = [ None, None ]
				for x in (0, 1):
					if len(action.actions[0].strip().parameters) >= x:
						if len(action.actions[x].strip().parameters) > 0:
							p[x] = action.actions[x].strip().parameters[0]
				if p[0] == Axes.ABS_X and p[1] == Axes.ABS_Y:
					self.set_cb(cb, "lstick", 2)
				elif p[0] == Axes.ABS_RX and p[1] == Axes.ABS_RY:
					self.set_cb(cb, "rstick", 2)
				elif p[0] == Axes.ABS_HAT0X and p[1] == Axes.ABS_HAT0Y:
					self.set_cb(cb, "dpad", 2)
				elif p[0] == Rels.REL_HWHEEL and p[1] == Rels.REL_WHEEL:
					self.set_cb(cb, "wheel", 2)
			else:
				self.set_cb(cb, "none", 2)
	
	
	def update_osd_area(self, action):
		""" Updates preview area displayed on screen """
		if action:
			if self.osd_area_instance is None:
				self.osd_area_instance = Area()
				self.osd_area_instance.show()
			action.update_osd_area(self.osd_area_instance, FakeMapper(self.editor))
			self.timer("area", 0.5, self.update_osd_area, action)
		elif self.osd_area_instance:
			self.osd_area_instance.quit()
			self.osd_area_instance = None
			self.cancel_timer("area")
	
	
	def load_area_action(self, action):
		"""
		Load AreaAction values into UI.
		"""
		cbAreaType = self.builder.get_object("cbAreaType")
		
		x1, y1, x2, y2 = action.coords
		self.relative_area = False
		if isinstance(action, RelAreaAction):
			key = "screensize"
			self.relative_area = True
			x1, y1, x2, y2 = x1 * 100.0, y1 * 100.0, x2 * 100.0, y2 * 100.0
		elif isinstance(action, RelWinAreaAction):
			key = "windowsize"
			self.relative_area = True
			x1, y1, x2, y2 = x1 * 100.0, y1 * 100.0, x2 * 100.0, y2 * 100.0
		else:
			t1 = "1" if x1 < 0 and x2 < 0 else "0"
			t2 = "1" if y1 < 0 and y2 < 0 else "0"
			x1, y1, x2, y2 = abs(x1), abs(y1), abs(x2), abs(y2)
			if x2 < x1 : x1, x2 = x2, x1
			if y2 < y1 : y1, y2 = y2, y1
			if isinstance(action, WinAreaAction):
				key = "window-%s%s" % (t1, t2)
			else:
				key = "screen-%s%s" % (t1, t2)
		
		self._recursing = True
		self.builder.get_object("sbAreaX1").set_value(x1)
		self.builder.get_object("sbAreaY1").set_value(y1)
		self.builder.get_object("sbAreaX2").set_value(x2)
		self.builder.get_object("sbAreaY2").set_value(y2)
		self.builder.get_object("cbAreaOSDEnabled").set_active(self.editor.osd)
		self.builder.get_object("cbAreaClickEnabled").set_active(self.pressing_pad_clicks())
		for row in cbAreaType.get_model():
			if key == row[1]:
				cbAreaType.set_active_iter(row.iter)
				break
		self._recursing = False
	
	
	def on_cbAreaOSDEnabled_toggled(self, *a):
		self.editor.builder.get_object("cbOSD").set_active(
			self.builder.get_object("cbAreaOSDEnabled").get_active())
	
	
	def pressing_pad_clicks(self):
		"""
		Returns True if currently edited pad is set to press left mouse
		button when pressed.
		(yes, this is used somewhere)
		"""
		side = getattr(SCButtons, self.editor.get_id())
		c_action = self.app.current.buttons[side]
		if isinstance(c_action, ButtonAction):
			return c_action.button == Keys.BTN_LEFT
		return False
	
	
	def on_ok(self, action):
		if isinstance(action.strip(), AreaAction):
			# Kinda hacky way to set action on LPAD press or RPAD press
			# when user selects Mouse Area as ouput and checks
			# 'Pressing the Pad Clicks' checkbox
			side = getattr(SCButtons, self.editor.get_id())
			clicks = self.pressing_pad_clicks()
			
			if self.builder.get_object("cbAreaClickEnabled").get_active():
				if not clicks:
					# Turn pad press into mouse clicks
					self.app.set_action(self.app.current, side, ButtonAction(Keys.BTN_LEFT))
			else:
				if clicks:
					# Clear action created above if checkbox is uncheck
					self.app.set_action(self.app.current, side, NoAction())
	
	
	def make_area_action(self):
		"""
		Loads values from UI into new AreaAction or subclass.
		"""
		# Prepare
		cbAreaType = self.builder.get_object("cbAreaType")
		# Read numbers
		x1 = self.builder.get_object("sbAreaX1").get_value()
		y1 = self.builder.get_object("sbAreaY1").get_value()
		x2 = self.builder.get_object("sbAreaX2").get_value()
		y2 = self.builder.get_object("sbAreaY2").get_value()
		# Determine exact action type by looking into Area Type checkbox
		# (this part may seem little crazy)
		# ... numbers
		key = cbAreaType.get_model().get_value(cbAreaType.get_active_iter(), 1)
		if "-" in key:
			if key[-2] == "1":
				# Before-last character ius "1", that means that X coords are
				# counted from other side and has to be negated
				x1, x2 = -x1, -x2
			if key[-1] == "1":
				# Key ends with "1". Same thing as above but for Y coordinate
				y1, y2 = -y1, -y2
		if "size" in key:
			x1, y1, x2, y2 = x1 / 100.0, y1 / 100.0, x2 / 100.0, y2 / 100.0
		# ... class 
		if "window-" in key:
			cls = WinAreaAction
			self.relative_area = False
		elif "screensize" == key:
			cls = RelAreaAction
			self.relative_area = True
		elif "windowsize" == key:
			cls = RelWinAreaAction
			self.relative_area = True
		else: # "screen" in key
			cls = AreaAction
			self.relative_area = False
		if not self.relative_area:
			x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
			
		return cls(x1, y1, x2, y2)
	
	
	def get_button_title(self):
		return _("Joystick or Mouse")
	
	
	def handles(self, mode, action):
		if isinstance(action, (NoAction, TrackballAction, CircularAction,
					InvalidAction, AreaAction)):
			return True
		if isinstance(action, XYAction):
			p = [ None, None ]
			for x in (0, 1):
				if len(action.actions[0].strip().parameters) >= x:
					if len(action.actions[x].strip().parameters) > 0:
						p[x] = action.actions[x].strip().parameters[0]
			if p[0] == Axes.ABS_X and p[1] == Axes.ABS_Y:
				return True
			elif p[0] == Axes.ABS_RX and p[1] == Axes.ABS_RY:
				return True
			elif p[0] == Axes.ABS_HAT0X and p[1] == Axes.ABS_HAT0Y:
				return True
			elif p[0] == Rels.REL_HWHEEL and p[1] == Rels.REL_WHEEL:
				return True
		return False
	
	
	def on_area_options_changed(self, *a):
		if self._recursing : return
		action = self.make_area_action()
		self.editor.set_action(action)
		self.update_osd_area(action)
		for x in ('sbAreaX1', 'sbAreaX2', 'sbAreaY1', 'sbAreaY2'):
			spin = self.builder.get_object(x)
			if self.relative_area:
				spin.get_adjustment().set_upper(100)
			else:
				spin.get_adjustment().set_upper(1000)
			self.on_sbArea_output(spin)
	
	
	def on_sbArea_output(self, button, *a):
		if self.relative_area:
			button.set_text("%s %%" % (button.get_value()))
		else:
			button.set_text("%s px" % (int(button.get_value())))
	
	
	def on_sbArea_focus_out_event(self, button, *a):
		GLib.idle_add(self.on_sbArea_output, button)
	
	
	def on_sbArea_changed(self, button, *a):
		self.on_sbArea_output(button)
		self.on_area_options_changed(button)
	
	
	def on_cbAxisOutput_changed(self, *a):
		cbAxisOutput = self.builder.get_object("cbAxisOutput")
		stActionData = self.builder.get_object("stActionData")
		key = cbAxisOutput.get_model().get_value(cbAxisOutput.get_active_iter(), 2)
		if key == 'area':
			stActionData.set_visible_child(self.builder.get_object("grArea"))
			action = self.make_area_action()
			self.update_osd_area(action)
		else:
			stActionData.set_visible_child(self.builder.get_object("nothing"))
			action = cbAxisOutput.get_model().get_value(cbAxisOutput.get_active_iter(), 0)
			action = self.parser.restart(action).parse()
			self.update_osd_area(None)
		
		self.editor.set_action(action)


class FakeMapper(object):
	"""
	Class that pretends to be mapper used when calling update_osd_area.
	It has two purposes: To provide get_xdisplay() method that does what it says
	and get_active_window() that returns any other window but window that
	belongs to SC-Controller gui application.
	"""
	def __init__(self, editor):
		self._xdisplay = X.Display(hash(GdkX11.x11_get_default_xdisplay()))
		self.editor = editor
	
	def get_xdisplay(self):
		return self._xdisplay
	
	def get_current_window(self):
		"""
		Gets last active window that was not part of SC-Controller.
		Uses _NET_CLIENT_LIST_STACKING property of root window, value provided
		by window manager. If that fail (because of no or not ICCM compilant WM),
		simply returns root window.
		"""
		root = X.get_default_root_window(self._xdisplay)
		NET_WM_WINDOW_TYPE_NORMAL = X.intern_atom(self._xdisplay,
				"_NET_WM_WINDOW_TYPE_NORMAL" , False)
		my_windows = [ x.get_xid() for x
				in Gdk.Screen.get_default().get_toplevel_windows() ]
		nitems, prop = X.get_window_prop(self._xdisplay,
				root, "_NET_CLIENT_LIST_STACKING", max_size=0x8000)
		
		if nitems > 0:
			for i in reversed(xrange(0, nitems)):
				window = cast(prop, POINTER(X.XID))[i]
				if window in my_windows:
					# skip over my own windows
					continue
				if not X.is_window_visible(self._xdisplay, window):
					# skip minimized and invisible windows
					continue
				tp = X.get_window_prop(self._xdisplay, window,
						"_NET_WM_WINDOW_TYPE")[-1]
				if tp is not None:
					tpval = cast(tp, POINTER(X.Atom)).contents.value
					X.free(tp)
					if tpval != NET_WM_WINDOW_TYPE_NORMAL:
						# skip over non-normal windows
						continue
				X.free(prop)
				return window
		if prop is not None:
			X.free(prop)
		
		# Failed to get property or there is not any usable window
		return root
