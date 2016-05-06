#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Button Component

Assigns emulated button to physical button
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, NoAction, DPadAction, DPad8Action
from scc.gui.ae import AEComponent, describe_action
from scc.gui.action_editor import ActionEditor


import os, logging
log = logging.getLogger("AE.DPAD")

__all__ = [ 'DPADComponent' ]


class DPADComponent(AEComponent):
	GLADE = "ae/dpad.glade"
	NAME = "dpad"
	CTXS = Action.AC_STICK, Action.AC_PAD,
	PRIORITY = 2
	
	DPAD8_WIDGETS = [ 'btDPAD4', 'btDPAD5', 'btDPAD6', 'btDPAD7' ]
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
		self.actions = [ NoAction() ] * 8
	
	
	def set_action(self, mode, action):
		if self.handles(mode, action):
			for i in xrange(0, len(action.actions)):
				self.actions[i] = action.actions[i]
		for i in xrange(0, 8):
			self.set_button_desc(i)
	
	
	def set_button_desc(self, i):
		desc = describe_action(Action.AC_BUTTON, None, self.actions[i])
		l = self.builder.get_object("lblDPAD%s" % (i,))
		if l is None:
			l = self.builder.get_object("btDPAD%s" % (i,)).get_children()[0]
		l.set_markup(desc)
	
	
	def get_button_title(self):
		return _("DPAD")
	
	
	def handles(self, mode, action):
		return isinstance(action, DPadAction) # DPad8Action is derived from DPadAction
	
	
	def update(self):
		cb = self.builder.get_object("cbDPADType")
		if cb.get_active() == 1:
			# 8-way dpad
			action = DPad8Action(*self.actions)
		else:
			# 4-way dpad
			action = DPadAction(*self.actions[0:4])
		self.editor.set_action(action)
	
	
	def on_cbDPADType_changed(self, *a):
		cb = self.builder.get_object("cbDPADType")
		for i in self.DPAD8_WIDGETS:
			self.builder.get_object(i).set_visible(cb.get_active() == 1)
		self.update()
	
	
	def on_choosen(self, i, action):
		self.actions[i] = action
		self.set_button_desc(i)
		self.update()
	
	
	def on_btDPAD_clicked(self, b):
		""" 'Select DPAD Left Action' handler """
		i = int(b.get_name())
		ae = ActionEditor(self.app, self.on_choosen)
		ae.set_title(_("Select DPAD Action"))
		ae.set_button(i, self.actions[i])
		ae.show(self.app.window)
