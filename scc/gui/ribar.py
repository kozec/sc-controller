#!/usr/bin/env python2
"""
SC-Controller - RIBar

Infobar wrapped in Revealer, looks better than sounds.
"""

from gi.repository import Gtk, GLib, GObject, Pango
import os


class RIBar(Gtk.Revealer):
	"""
	Infobar wrapped in Revealer
	
	Signals:
		Everything from Gtk.Revealer, plus:
		close()
			emitted when the user dismisses the info bar
		response(response_id)
			Emitted when an action widget (button) is clicked
	"""
	__gsignals__ = {
			b"response"	: (GObject.SignalFlags.RUN_FIRST, None, (int,)),
			b"close"	: (GObject.SignalFlags.RUN_FIRST, None, ()),
		}
	
	### Initialization
	def __init__(self, label, message_type=Gtk.MessageType.INFO,
														infobar=None, *buttons):
		"""
		... where label can be Gtk.Widget or str and buttons are tuples
		of (Gtk.Button, response_id)
		"""
		# Init
		Gtk.Revealer.__init__(self)
		self._infobar = infobar or Gtk.InfoBar()
		self._values = {}
		self._label = None
		# Icon
		if infobar is None:
			icon_name = "dialog-information"
			if message_type == Gtk.MessageType.ERROR:
				icon_name = "dialog-error"
			elif message_type == Gtk.MessageType.WARNING:
				icon_name = "dialog-warning"
			icon = Gtk.Image()
			icon.set_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
			self._infobar.get_content_area().pack_start(icon, False, False, 1)
			# Label
			if isinstance(label, Gtk.Widget):
				self._infobar.get_content_area().pack_start(label, True, True, 0)
				self._label = label
			else:
				self._label = Gtk.Label()
				self._label.set_size_request(300, -1)
				self._label.set_markup(label)
				self._label.set_alignment(0, 0.5)
				self._label.set_line_wrap(True)
				self._infobar.get_content_area().add(self._label)
		# Buttons
		for button, response_id in buttons:
			self.add_button(button, response_id)
		# Signals
		self._infobar.connect("close", self._cb_close)
		self._infobar.connect("response", self._cb_response)
		# Settings
		self._infobar.set_message_type(message_type)
		if hasattr(self._infobar, "set_show_close_button"):
			# GTK >3.8
			self._infobar.set_show_close_button(True)
		else:
			self.add_button(Gtk.Button("X"), 0)
		self.set_reveal_child(False)
		# Packing
		self.add(self._infobar)
		self.show_all()
	
	def _cb_close(self, ib):
		self.emit("close")
	
	def _cb_response(self, ib, response_id):
		self.emit("response", response_id)
	
	def disable_close_button(self):
		if hasattr(self._infobar, "set_show_close_button"):
			self._infobar.set_show_close_button(False)
	
	def add_widget(self, widget, expand=False, fill=True):
		self._infobar.get_content_area().pack_start(widget, expand, fill, 1)
		widget.show()
	
	def add_button(self, button, response_id):
		self._infobar.add_action_widget(button, response_id)
		self._infobar.show_all()
	
	def get_label(self):
		""" Returns label widget """
		return self._label
	
	def close_on_close(self):
		"""
		Setups revealer so it will be automaticaly closed, removed and
		destroyed when user clicks to any button, including 'X'
		"""
		self.connect("close", self.close)
		self.connect("response", self.close)
	
	def close(self, *a):
		"""
		Closes revealer (with animation), removes it from parent and
		calls destroy()
		"""
		self.set_reveal_child(False)
		GLib.timeout_add(self.get_transition_duration() + 50, self._cb_destroy)
	
	def _cb_destroy(self, *a):
		""" Callback used by _cb_close method """
		if not self.get_parent() is None:
			self.get_parent().remove(self)
		self.destroy()
	
	def set_value(self, key, value):
		""" Stores some metadata """
		self._values[key] = value
	
	def get_value(self, key):
		""" Retrieves some metadata """
		return self._values[key]
	
	def __getitem__(self, key):
		""" Shortcut to get_value """
		return self._values[key]
	
	def __setitem__(self, key, value):
		""" Shortcut to set_value """
		self.set_value(key, value)
	
	@staticmethod
	def build_button(label, icon_name=None, icon_widget=None, use_stock=False):
		""" Builds button situable for action area """
		b = Gtk.Button.new_from_stock(label) if use_stock \
			else Gtk.Button.new_with_label(label)
		b.set_use_underline(True)
		if not icon_name is None:
			icon_widget = Gtk.Image()
			icon_widget.set_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
		if not icon_widget is None:
			b.set_image(icon_widget)
			b.set_always_show_image(True)
		return b
