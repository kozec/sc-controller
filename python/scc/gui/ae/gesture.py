#!/usr/bin/env python2
# coding=utf-8
"""
SC-Controller - Action Editor - Gesture Component

Handles gesture recognition settings.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib, GObject
from scc.gui.ae import AEComponent, describe_action
from scc.gui.area_to_action import action_to_area
from scc.gui.simple_chooser import SimpleChooser
from scc.gui.action_editor import ActionEditor
from scc.gui.parser import GuiActionParser
# from scc.osd.gesture_display import GestureDisplay
from scc.actions import GesturesAction, OSDAction
from scc.actions import Action, NoAction, XYAction
from scc.tools import strip_gesture

import os, logging, platform
log = logging.getLogger("AE.PerAxis")

__all__ = [ 'GestureComponent' ]


class GestureComponent(AEComponent):
	GLADE = "ae/gesture.glade"
	NAME = "gesture"
	CTXS = Action.AC_STICK | Action.AC_PAD
	PRIORITY = 1
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self.on_wayland = False
		self._edited_gesture = None
		self._grabber = None
	
	
	def load(self):
		if AEComponent.load(self):
			# Unlike mose region, gesutres kinda work with XWayland
			if platform.system() == "Windows":
				self.on_wayland = False
			else:
				from gi.repository import GdkX11
				self.on_wayland = "WAYLAND_DISPLAY" in os.environ or not isinstance(Gdk.Display.get_default(), GdkX11.X11Display)
			if self.on_wayland:
				self.builder.get_object("lblGestureMessage").set_text(_("Note: Gestures are not available with Wayland-based display server"))
				self.builder.get_object("lblGestureMessage").set_visible(True)
				self.builder.get_object("gesture").set_sensitive(False)
			else:
				self._grabber = GestureGrabber(self.editor, self.builder)
			return True
	
	
	def set_action(self, mode, action):
		lstGestures = self.builder.get_object("lstGestures")
		lstGestures.clear()
		if isinstance(action, GesturesAction):
			for gstr in action.gestures:
				self._add_gesture(gstr, action.gestures[gstr])
	
	
	def _add_gesture(self, gstr, action, select=False):
		lstGestures = self.builder.get_object("lstGestures")
		o = GObject.GObject()
		o.gstr = gstr
		o.action = action
		iter = lstGestures.append( (
			GestureComponent.nice_gstr(gstr),
			action.describe(Action.AC_MENU),
			o
		) )
		if select:
			tvGestures = self.builder.get_object("tvGestures")
			tvGestures.get_selection().select_iter(iter)
			self.on_tvGestures_cursor_changed()
			self.on_btEditAction_clicked()
	
	
	ARROWS = { 'U' : '↑', 'D' : '↓', 'L' : '←', 'R' : '→', }
	@staticmethod
	def nice_gstr(gstr):
		"""
		Replaces characters UDLR in gesture string with unicode arrows.
		← → ↑ ↓
		"""
		if "i" in gstr:
			gstr = strip_gesture(gstr)
		l = lambda x : GestureComponent.ARROWS[x] if x in GestureComponent.ARROWS else ""
		return "".join(map(l, gstr))
	
	
	def get_button_title(self):
		return _("Gestures")
	
	
	def handles(self, mode, action):
		return isinstance(action, GesturesAction)
	
	
	def on_tvGestures_cursor_changed(self, *a):
		tvGestures = self.builder.get_object("tvGestures")
		btEditAction = self.builder.get_object("btEditAction")
		btRemove = self.builder.get_object("btRemove")
		model, iter = tvGestures.get_selection().get_selected()
		if iter is None:
			btEditAction.set_sensitive(False)
			btRemove.set_sensitive(False)
		else:
			btEditAction.set_sensitive(True)
			btRemove.set_sensitive(True)
	
	
	def on_btEditAction_clicked(self, *a):
		""" Handler for "Edit Action" button """
		tvGestures = self.builder.get_object("tvGestures")
		txGesture = self.builder.get_object("txGesture")
		cbIgnoreStroke = self.builder.get_object("cbIgnoreStroke")
		gesture_editor = self.builder.get_object("gesture_editor")
		
		model, iter = tvGestures.get_selection().get_selected()
		item = model.get_value(iter, 2)
		self._edited_gesture = item.gstr
		cbIgnoreStroke.set_active("i" in self._edited_gesture)
		txGesture.set_text(GestureComponent.nice_gstr(self._edited_gesture))
		# Setup editor
		e = ActionEditor(self.app, self.on_action_chosen)
		e.set_title(_("Edit Gesture Action"))
		e.set_input("ID", item.action, mode = Action.AC_BUTTON)
		e.add_widget(_("Gesture"), gesture_editor)
		e.hide_modeshift()
		# Display editor
		e.show(self.editor.window)
	
	
	def on_btChangeGesture_clicked(self, *a):
		txGesture = self.builder.get_object("txGesture")
		def grabbed(gesture):
			self._edited_gesture = gesture
			txGesture.set_text(GestureComponent.nice_gstr(self._edited_gesture))
		self._grabber.grab(grabbed)
	
	
	def on_cbIgnoreStroke_toggled(self, cb):
		txGesture = self.builder.get_object("txGesture")
		if cb.get_active() and "i" not in self._edited_gesture:
			self._edited_gesture = "i" + self._edited_gesture
			txGesture.set_text(GestureComponent.nice_gstr(self._edited_gesture))
		elif not cb.get_active() and "i" in self._edited_gesture:
			self._edited_gesture = self._edited_gesture.strip("i")
			txGesture.set_text(GestureComponent.nice_gstr(self._edited_gesture))
	
	
	def on_btRemove_clicked(self, *a):
		tvGestures = self.builder.get_object("tvGestures")
		model, iter = tvGestures.get_selection().get_selected()
		model.remove(iter)
		self.on_tvGestures_cursor_changed()
	
	
	def on_btAdd_clicked(self, *a):
		def grabbed(gesture):
			self._add_gesture(gesture, NoAction(), True)
		tvGestures = self.builder.get_object("tvGestures")
		if len(tvGestures.get_model()) == 0:
			# I believe user will not actually find this option, so OSD checkbox
			# is automatically enabled when first item is added
			self.editor.set_osd_enabled(True)
		self._grabber.grab(grabbed)
	
	
	def on_sclPrecision_format_value(self, scl, value):
		return "%s%%" % (int(value * 100.0),)
	
	
	def on_sclPrecision_value_changed(self, *a):
		self.update()
	
	
	def on_btClearTolerance_clicked(self, *a):
		self.builder.get_object("sclPrecision").set_value(GesturesAction.DEFAULT_PRECISION)
	
	
	def on_action_chosen(self, id, action, mark_changed=True):
		tvGestures = self.builder.get_object("tvGestures")
		model, iter = tvGestures.get_selection().get_selected()
		item = model.get_value(iter, 2)
		item.gstr = self._edited_gesture
		item.action = action
		model.set_value(iter, 0, GestureComponent.nice_gstr(item.gstr))
		model.set_value(iter, 1, action.describe(Action.AC_MENU))
		self.update()
	
	
	def update(self):
		a = GesturesAction()
		tvGestures = self.builder.get_object("tvGestures")
		model, iter = tvGestures.get_selection().get_selected()
		for row in model:
			item = row[2]
			a.gestures[item.gstr] = item.action
		a.precision = self.builder.get_object("sclPrecision").get_value()
		a = OSDAction(a)
		self.editor.set_action(a)


class GestureGrabber(object):
	def __init__(self, editor, builder):
		self.editor = editor
		self.builder = builder
		self._callback = None
		self._gd = None
		self._signals = None
		self._gesture = None
		self._repeats = 0
		self.gesture_grabber = self.builder.get_object("gesture_grabber")
		self.txGestureGrab = self.builder.get_object("txGestureGrab")
		self.lblGestureGrabberTitle = self.builder.get_object("lblGestureGrabberTitle")
		self.lblGestureStatus = self.builder.get_object("lblGestureStatus")
		self.rvGestureGrab = self.builder.get_object("rvGestureGrab")
		# Can't use autoconnect for this :(
		self.gesture_grabber.connect("delete-event", self.close)
		self.gesture_grabber.connect("destroy", self.close)
		self.builder.get_object("btnStartGestureOver").connect("clicked", self.start_over)
		self.builder.get_object("btnConfirmGesutre").connect("clicked", self.use)
	
	
	def fail(self, *a):
		"""
		Called when something goes bad, usually because there is
		no controller connected.
		"""
		log.error("Failed to grab gesture: %s", a)
	
	
	def disconnect_signals(self):
		"""
		Disconnects redundant signal handlers.
		Currently only one created in lock_buttons.
		"""
		if self._signals:
			for source, eid in self._signals:
				source.disconnect(eid)
			self._signals = []
	
	
	def lock_buttons(self):
		self.disconnect_signals()
		try:
			c = self.editor.app.dm.get_controllers()[0]
			c.lock(
				lambda *a: True,	# success_cb
				self.fail,			# error_cb
				'A', 'Y'
			)
			self._signals = [ (c, c.connect('event', self.on_event)) ]
		except IndexError, e:
			# No controllers
			self.fail()
	
	
	def on_event(self, c, button, data):
		if self.rvGestureGrab.get_reveal_child():
			if button == "A" and data[0] == 0:
				self.use()
			elif button == "Y" and data[0] == 0:
				self.start_over()
	
	
	def grab(self, callback):
		self._callback = callback
		self.start_over()
		self.gesture_grabber.set_transient_for(self.editor.window)
		self.gesture_grabber.show()
		self._create_gd()
	
	
	def use(self, *a):
		self._callback(self._gesture)
		self.close()
	
	
	def close(self, *a):
		if self._gd:
			self._gd.quit()
		self._gd = None
		self.gesture_grabber.hide()
		return True
	
	
	def start_over(self, *a):
		if self.editor.get_id() == "RPAD":
			self.lblGestureGrabberTitle.set_text(_("Draw gesture on RIGHT pad..."))
		else:
			self.lblGestureGrabberTitle.set_text(_("Draw gesture on LEFT pad..."))
		self.lblGestureStatus.set_label("")
		self.txGestureGrab.set_text("")
		self.rvGestureGrab.set_reveal_child(False)
		self._gesture = None
		self._repeats = 0
	
	
	def _create_gd(self):
		""" Creates GestureDisplay object """
		if self._gd:
			self._gd.quit()
		self._gd = GestureDisplay(self.editor.app.config)
		if self.editor.get_id() == "RPAD":
			self._gd.parse_argumets([ "GestureDisplay", "--control-with", "RIGHT" ])
		else:
			self._gd.parse_argumets([ "GestureDisplay", "--control-with", "LEFT" ])
		self._gd.use_daemon(self.editor.app.dm)
		self._gd.show()
		self._gd.connect('gesture-updated', self.on_gesture_updated)
		self._gd.connect('destroy', self.on_gesture_recognized)
		self.lock_buttons()
	
	
	def on_gesture_updated(self, gd, gstr):
		txt = GestureComponent.nice_gstr(gstr)
		self.txGestureGrab.set_text(txt)
		self.txGestureGrab.set_position(len(txt))
	
	
	def on_gesture_recognized(self, gd):
		self.disconnect_signals()
		if gd.get_exit_code() != 0:
			# Canceled or cannot grab controller
			return
		if gd.get_gesture():
			self.on_gesture_updated(gd, gd.get_gesture())
			if self._gesture == None:
				self.lblGestureGrabberTitle.set_text(_("Repeat same gesture or press A button to confirm..."))
				self.rvGestureGrab.set_reveal_child(True)
				self._gesture = gd.get_gesture()
			elif self._gesture == gd.get_gesture():
				self._repeats += 1
				self.lblGestureStatus.set_label(_("Repeated %s times") % (self._repeats,))
			else:
				self.lblGestureStatus.set_label(_("Gesture differs"))
		
		self._create_gd()
