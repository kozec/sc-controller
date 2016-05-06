#!/usr/bin/env python2
""" ae - Action Editor components """
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.tools import strip_none, ensure_size
from scc.actions import Action, NoAction, XYAction

import os, logging
log = logging.getLogger("AE")

class AEComponent(object):
	GLADE = None
	NAME = None
	PRIORITY = 0
	# List of contexes (Action.AC_BUTTON, Action.AC_TRIGGER...) that this
	# compoment can handle. Set to Action.AC_ALL for compoment that handles
	# all modes.
	CTXS = ()
	
	def __init__(self, app, editor):
		self.app = app
		self.editor = editor
		self.loaded = False
	
	
	def get_button_title(self):
		raise Exception("Implement me!")
	
	
	def shown(self):
		""" Called after user switches TO page """
		pass
	
	
	def hidden(self):
		""" Called after user switches AWAY from page """
		pass
	
	
	def load(self):
		if self.loaded : return
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.widget = self.builder.get_object(self.NAME)
		self.builder.connect_signals(self)
		self.loaded = True
	
	
	def is_loaded(self):
		return self.loaded
	
	
	def handles(self, mode, action):
		"""
		Returns True if component can display and edit specified action.
		If more than one component returns True from 'handles',
		higher PRIORITY is used
		"""
		return False
	
	
	def set_action(self, mode, action):
		"""
		Setups component widgets to display currently set action.
		"""
		pass
	
	
	def get_widget(self):
		return self.widget


def describe_action(mode, cls, v):
	"""
	Returns action description with 'v' as parameter, unless unless v is None.
	Returns "not set" if v is None
	"""
	if v is None or type(v) in (int, float, str, unicode):
		return _('(not set)')
	elif isinstance(v, Action):
		dsc = v.describe(Action.AC_STICK if cls == XYAction else Action.AC_BUTTON)
		if "\n" in dsc:
			dsc = "<small>" + "\n".join(dsc.split("\n")[0:2]) + "</small>"
		return dsc
	else:
		return (cls(v)).describe(mode)
