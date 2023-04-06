#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Syncthing-GTK - StatusIcon

"""


import locale
import os
import sys
import logging

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk

from scc.gui.dwsnc import IS_UNITY, IS_GNOME
from scc.tools import _ # gettext function

log = logging.getLogger("StatusIcon")

# Taken from Syncthing-GTK, but got all KDE stuff removed, since it doesn't
# work in latest KDE anymore.


#                | MATE      | Unity      | Cinnamon   | Cairo-Dock (classic) | Cairo-Dock (modern) |
#----------------+-----------+------------+------------+----------------------+---------------------+
# StatusIconAppI | none      | excellent  | none       | none                 | excellent           |
# StatusIconGTK3 | excellent | none       | very good¹ | very good¹           | none                |
#
# Notes:
#  - StatusIconAppIndicator does not implement any fallback (but the original libappindicator did)
#  - Markers:
#     ¹ Icon cropped


class StatusIcon(GObject.GObject):
	"""
	Base class for all status icon backends
	"""
	TRAY_TITLE     = _("SC-Controller")
	
	__gsignals__ = {
		b"clicked": (GObject.SignalFlags.RUN_FIRST, None, ()),
	}
	
	__gproperties__ = {
		b"active": (
			GObject.TYPE_BOOLEAN,
			"is the icon user-visible?",
			"does the icon back-end think that anything is might be shown to the user?",
			True,
			GObject.PARAM_READWRITE if hasattr(GObject, "PARAM_READWRITE") else GObject.ParamFlags.READWRITE
		)		
	}
	
	def __init__(self, icon_path, popupmenu, force=False):
		GObject.GObject.__init__(self)
		self.__icon_path = os.path.normpath(os.path.abspath(icon_path))
		self.__popupmenu = popupmenu
		self.__active    = True
		self.__visible   = False
		self.__hidden    = False
		self.__icon      = "scc-unknown"
		self.__text      = ""
		self.__force     = force
	
	def get_active(self):
		"""
		Return whether there is at least a chance that the icon might be shown to the user
		
		If this returns `False` then the icon will definetely not be shown, but if it returns `True` it doesn't have to
		be visible...
		
		<em>Note:</em> This value is not directly influenced by calling `hide()` and `show()`.
		
		@return {bool}
		"""
		return self.get_property("active")
	
	def set(self, icon=None, text=None):
		"""
		Set the status icon image and descriptive text
		
		If either of these are `None` their previous value will be used.
		
		@param {String} icon
		       The name of the icon to show (i.e. `si-syncthing-idle`)
		@param {String} text
		       Some text that indicates what the application is currently doing (generally this be used for the tooltip)
		"""
		if not icon.endswith("-0"): # si-syncthing-0
			# Ignore first syncing icon state to prevent the icon from flickering
			# into the main notification bar during initialization
			self.__visible = True
		
		if self.__hidden:
			self._set_visible(False)
		else:
			self._set_visible(self.__visible)
	
	def hide(self):
		"""
		Hide the icon
		
		This method tries its best to ensure the icon is hidden, but there are no guarantees as to how use well its
		going to work.
		"""
		self.__hidden = True
		self._set_visible(False)
	
	def show(self):
		"""
		Show a previously hidden icon
		
		This method tries its best to ensure the icon is hidden, but there are no guarantees as to how use well its
		going to work.
		"""
		self.__hidden = False
		self._set_visible(self.__visible)
	
	def is_clickable(self):
		""" Basically, returns False is appindicator is used """
		return True
	
	def _is_forced(self):
		return self.__force
	
	def _on_click(self, *a):
		self.emit("clicked")
	
	def _get_icon(self, icon=None):
		"""
		@internal
		
		Use `set()` instead.
		"""
		if icon:
			self.__icon = icon
		return self.__icon
	
	def _get_text(self, text=None):
		"""
		@internal
		
		Use `set()` instead.
		"""
		if text:
			self.__text = text
		return self.__text
	
	def _get_popupmenu(self):
		"""
		@internal
		"""
		return self.__popupmenu
	
	def _set_visible(self, visible):
		"""
		@internal
		"""
		pass

	def do_get_property(self, property):
		if property.name == "active":
			return self.__active
		else:
			raise AttributeError("Unknown property %s" % property.name)
	
	def do_set_property(self, property, value):
		if property.name == "active":
			self.__active = value
		else:
			raise AttributeError("unknown property %s" % property.name)


class StatusIconDummy(StatusIcon):
	"""
	Dummy status icon implementation that does nothing
	"""
	def __init__(self, *args, **kwargs):
		StatusIcon.__init__(self, *args, **kwargs)
		
		# Pretty unlikely that this will be visible...
		self.set_property("active", False)
	
	def set(self, icon=None, text=None):
		StatusIcon.set(self, icon, text)
		
		self._get_icon(icon)
		self._get_text(text)


class StatusIconGTK3(StatusIcon):
	"""
	Gtk.StatusIcon based status icon backend
	"""
	def __init__(self, *args, **kwargs):
		StatusIcon.__init__(self, *args, **kwargs)
		
		if not self._is_forced():
			if IS_UNITY:
				# Unity fakes SysTray support but actually hides all icons...
				raise NotImplementedError
			if IS_GNOME:
				# Gnome got broken as well
				raise NotImplementedError
		
		self._tray = Gtk.StatusIcon()
		
		self._tray.connect("activate", self._on_click)
		self._tray.connect("popup-menu", self._on_rclick)
		self._tray.connect("notify::embedded", self._on_embedded_change)
		
		self._tray.set_visible(True)
		self._tray.set_name("sc-controller")
		self._tray.set_title(self.TRAY_TITLE)
		
		# self._tray.is_embedded() must be called asynchronously
		# See: http://stackoverflow.com/a/6365904/277882
		GLib.idle_add(self._on_embedded_change)
	
	def destroy(self):
		self.hide()
		self._tray = None
	
	def set(self, icon=None, text=None):
		StatusIcon.set(self, icon, text)
		
		self._tray.set_from_icon_name(self._get_icon(icon))
		self._tray.set_tooltip_text(self._get_text(text))
	
	def _on_embedded_change(self, *args):
		# Without an icon update at this point GTK might consider the icon embedded and visible even through
		# it can't actually be seen...
		self._tray.set_from_file(self._get_icon())
		
		# An invisible tray icon will never be embedded but it also should not be replaced
		# by a fallback icon
		is_embedded = self._tray.is_embedded() or not self._tray.get_visible()
		if is_embedded != self.get_property("active"):
			self.set_property("active", is_embedded)
	
	def _on_rclick(self, si, button, time):
		self._get_popupmenu().popup(None, None, None, None, button, time)
	
	def _set_visible(self, active):
		StatusIcon._set_visible(self, active)
		
		self._tray.set_visible(active)


class StatusIconDBus(StatusIcon):
	pass


class StatusIconAppIndicator(StatusIconDBus):
	"""
	Unity's AppIndicator3.Indicator based status icon backend
	"""
	def __init__(self, *args, **kwargs):
		StatusIcon.__init__(self, *args, **kwargs)
		
		try:
			from gi.repository import AppIndicator3 as appindicator
			
			self._status_active  = appindicator.IndicatorStatus.ACTIVE
			self._status_passive = appindicator.IndicatorStatus.PASSIVE
		except ImportError:
			log.warning("Failed to import AppIndicator3")
			raise NotImplementedError
		
		category = appindicator.IndicatorCategory.APPLICATION_STATUS
		# Whatever icon is set here will be used as a tooltip icon during the entire time to icon is shown
		self._tray = appindicator.Indicator.new("sc-controller", self._get_icon(), category)
		self._tray.set_menu(self._get_popupmenu())
		self._tray.set_title(self.TRAY_TITLE)
	
	def _set_visible(self, active):
		StatusIcon._set_visible(self, active)
		
		self._tray.set_status(self._status_active if active else self._status_passive)
	
	def is_clickable(self):
		return False
	
	def destroy(self):
		self.hide()
		self._tray = None
	
	def set(self, icon=None, text=None):
		StatusIcon.set(self, icon, text)
		
		self._tray.set_icon_full(self._get_icon(icon), self._get_text(text))


class StatusIconProxy(StatusIcon):
	
	def __init__(self, *args, **kwargs):
		StatusIcon.__init__(self, *args, **kwargs)
		
		self._arguments  = (args, kwargs)
		self._status_fb  = None
		self._status_gtk = None
		self.set("scc-unknown", "")
		
		# Do not ever force-show indicators when they do not think they'll work
		if "force" in self._arguments[1]:
			del self._arguments[1]["force"]
		
		try:
			# Try loading GTK native status icon
			self._status_gtk = StatusIconGTK3(*args, **kwargs)
			self._status_gtk.connect(b"clicked",        self._on_click)
			self._status_gtk.connect(b"notify::active", self._on_notify_active_gtk)
			self._on_notify_active_gtk()
			
			log.info("Using backend StatusIconGTK3 (primary)")
		except NotImplementedError:
			# Directly load fallback implementation
			self._load_fallback()
	
	def _on_click(self, *args):
		self.emit(b"clicked")
	
	def _on_notify_active_gtk(self, *args):
		if self._status_fb:
			# Hide fallback icon if GTK icon is active and vice-versa
			if self._status_gtk.get_active():
				self._status_fb.hide()
			else:
				self._status_fb.show()
		elif not self._status_gtk.get_active():
			# Load fallback implementation
			self._load_fallback()
	
	def _on_notify_active_fb(self, *args):
		active = False
		if self._status_gtk and self._status_gtk.get_active():
			active = True
		if self._status_fb and self._status_fb.get_active():
			active = True
		self.set_property("active", active)
	
	def _load_fallback(self):
		status_icon_backends = [StatusIconAppIndicator, StatusIconDummy]
		
		if not self._status_fb:
			for StatusIconBackend in status_icon_backends:
				try:
					self._status_fb = StatusIconBackend(*self._arguments[0], **self._arguments[1])
					self._status_fb.connect(b"clicked",        self._on_click)
					self._status_fb.connect(b"notify::active", self._on_notify_active_fb)
					self._on_notify_active_fb()
					
					log.warning("StatusIcon: Using backend %s (fallback)" % StatusIconBackend.__name__)
					break
				except NotImplementedError:
					continue
		
			# At least the dummy backend should have been loaded at this point...
			assert self._status_fb
		
		# Update fallback icon
		self.set(self._icon, self._text)
	
	def is_clickable(self):
		if self._status_gtk:
			return self._status_gtk.is_clickable()
		if self._status_fb:
			return self._status_fb.is_clickable()
		return False
	
	def set(self, icon=None, text=None):
		self._icon = icon
		self._text = text
		
		if self._status_gtk:
			self._status_gtk.set(icon, text)
		if self._status_fb:
			self._status_fb.set(icon, text)
	
	def hide(self):
		if self._status_gtk:
			self._status_gtk.hide()
		if self._status_fb:
			self._status_fb.hide()
	
	def destroy(self):
		if self._status_gtk:
			self._status_gtk.destroy()
		if self._status_fb:
			self._status_fb.destroy()
	
	def show(self):
		if self._status_gtk:
			self._status_gtk.show()
		if self._status_fb:
			self._status_fb.show()

def get_status_icon(*args, **kwargs):
	# Try selecting backend based on environment variable
	if "STATUS_BACKEND" in os.environ:
		kwargs["force"] = True
		
		status_icon_backend_name = "StatusIcon%s" % (os.environ.get("STATUS_BACKEND"))
		if status_icon_backend_name in globals():
			try:
				status_icon = globals()[status_icon_backend_name](*args, **kwargs)
				log.info("StatusIcon: Using requested backend %s" % (status_icon_backend_name))
				return status_icon
			except NotImplementedError:
				log.error("StatusIcon: Requested backend %s is not supported" % (status_icon_backend_name))
		else:
			log.error("StatusIcon: Requested backend %s does not exist" % (status_icon_backend_name))
		
		return StatusIconDummy(*args, **kwargs)
	
	# Use proxy backend to determine the correct backend while the application is running
	return StatusIconProxy(*args, **kwargs)

