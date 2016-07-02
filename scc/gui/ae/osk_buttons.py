#!/usr/bin/env python2
"""
SC-Controller - Action Editor - OSK Button Component

Binds controller buttons on on on on on... screen keyboard.
Retuses ButtonsComponent, but hides image, so user can't select mouse or gamepad
button.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action, ButtonAction, MultiAction, NoAction
from scc.gui.area_to_action import action_to_area
from scc.gui.ae.buttons import ButtonsComponent
from scc.gui.key_grabber import KeyGrabber
from scc.gui.parser import InvalidAction
from scc.gui.chooser import Chooser
from scc.gui.ae import AEComponent

import os, logging
log = logging.getLogger("AE.Buttons")

__all__ = [ 'OSKButtonsComponent' ]


class OSKButtonsComponent(ButtonsComponent):
	CTXS = Action.AC_OSK
	PRIORITY = 1
	IMAGES = { }
	
	
	def get_button_title(self):
		return _("Key")
	
	
	def load(self):
		if not self.loaded:
			AEComponent.load(self)
			self.builder.get_object("lblClickAnyButton").set_visible(False)
