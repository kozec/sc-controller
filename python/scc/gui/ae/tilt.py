#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Tilt

Setups DPAD emulation or menu display
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, TiltAction, ButtonAction, MenuAction
from scc.uinput import Keys
from scc.gui.ae import AEComponent, describe_action
from scc.gui.ae.menu_action import MenuActionCofC
from scc.gui.binding_editor import BindingEditor
from scc.gui.action_editor import ActionEditor


import os, logging
log = logging.getLogger("AE.Tilt")

__all__ = [ 'TiltComponent' ]


class TiltComponent(AEComponent, BindingEditor):
	GLADE = "ae/tilt.glade"
	NAME = "tilt"
	CTXS = Action.AC_GYRO
	PRIORITY = 2
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		BindingEditor.__init__(self, app)
		self._recursing = False
		self.actions = [ NoAction() ] * 6
	
	
	def set_action(self, mode, action):
		if isinstance(action, TiltAction):
			self.actions = list(action.actions)
			while len(self.actions) < 6:
				self.actions.append(NoAction())
			self.update_button_desc(action)
	
	
	def update_button_desc(self, action):
		for i in xrange(0, len(action.actions)):
			self.actions[i] = action.actions[i]
		for i in xrange(0, 6):
			self.set_button_desc(i)
	
	
	def set_button_desc(self, i):
		desc = describe_action(Action.AC_BUTTON, None, self.actions[i])
		print "SET", i, self.actions[i], desc
		l = self.builder.get_object("lblTilt%s" % (i,))
		if l is None:
			l = self.builder.get_object("btTilt%s" % (i,)).get_children()[0]
		l.set_markup(desc)
	
	
	def get_button_title(self):
		return _("Tilt")
	
	
	def handles(self, mode, action):
		return isinstance(action, TiltAction)
	
	
	def update(self):
		self.editor.set_action(TiltAction(*self.actions))
	
	
	def on_action_chosen(self, i, action, mark_changed=True):
		self.actions[i] = action
		self.set_button_desc(i)
		self.update()
	
	
	def on_btTilt_clicked(self, b):
		""" 'Select Tilt Action' handler """
		i = int(b.get_name())
		action = self.actions[i]
		ae = self.choose_editor(action, "")
		ae.set_title(_("Select Tilt Action"))
		ae.set_input(i, action, mode = Action.AC_BUTTON)
		ae.show(self.editor.window)

