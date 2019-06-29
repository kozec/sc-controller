#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
SC-Controller - Action Editor - First Page

Provides links for quick settings.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GLib
from scc.actions import Action
from scc.gui.ae import AEComponent
from scc.tools import nameof


import os, logging
log = logging.getLogger("AE.1st")

__all__ = [ 'FirstPage' ]

MARKUP_BUTTON = """
<big>%(what)s: Quick settings</big>

  • Map to <a href='page://buttons'>Button</a>
  
  • Use to <a href='quick://menu("Default.menu")'>display on-screen menu</a>
"""

MARKUP_TRIGGER = """
<big>%(what)s: Quick settings</big>

  • Map to <a href='quick://axis(Axes.ABS_Z)'>Left</a> or <a href='quick://axis(Axes.ABS_RZ)'>Right</a> Trigger
  
  • Map to <a href='quick://trigger(50, 255, button(Keys.BTN_LEFT))'>Left</a> or <a href='quick://trigger(50, 255, button(Keys.BTN_RIGHT))'>Right</a> mouse button
  
  • Map to <a href='grab://trigger_button'>Button</a>
"""


# TODO: Add haptics here
MARKUP_PAD = """
<big>%(what)s: Quick settings</big>

  • Use as <a href='quick://sens(1.2, 1.2, XY(axis(Axes.ABS_X), raxis(Axes.ABS_Y)))'>Left</a> or <a href='quick://sens(1.2, 1.2, XY(axis(Axes.ABS_RX), raxis(Axes.ABS_RY)))'>Right</a> gamepad stick, or <a href='quick://dpad(hatup(Axes.ABS_HAT0Y), hatdown(Axes.ABS_HAT0Y), hatleft(Axes.ABS_HAT0X), hatright(Axes.ABS_HAT0X))'>DPAD</a>

  • Use as keyboard: <a href='quick://dpad(button(Keys.KEY_W), button(Keys.KEY_S), button(Keys.KEY_A), button(Keys.KEY_D))'>WSAD</a> or <a href='quick://dpad(button(Keys.KEY_UP), button(Keys.KEY_DOWN), button(Keys.KEY_LEFT), button(Keys.KEY_RIGHT))'>Arrows</a>

  • Use as <a href='quick://smooth(8, 0.78, 2.0, feedback(RIGHT, 256, ball(mouse())))'>mouse</a> or <a href='quick://feedback(LEFT, 4096, 16.0, ball(XY(mouse(Rels.REL_HWHEEL), mouse(Rels.REL_WHEEL))))'>mouse wheel</a>

  • Create <a href='quick://feedback(LEFT, 4096, 16.0, menu("Default.menu",DEFAULT,A,B))'>touch menu</a>

  • Enable <a href='page://gesture'>gesture recognition</a>
"""

MARKUP_STICK = """
<big>Stick: Quick settings</big>

  • Use as <a href='quick://sens(1.2, 1.2, XY(axis(Axes.ABS_X), raxis(Axes.ABS_Y)))'>Left</a> or <a href='quick://sens(1.2, 1.2, XY(axis(Axes.ABS_RX), raxis(Axes.ABS_RY)))'>Right</a> gamepad stick, or <a href='quick://dpad(hatup(Axes.ABS_HAT0Y), hatdown(Axes.ABS_HAT0Y), hatleft(Axes.ABS_HAT0X), hatright(Axes.ABS_HAT0X))'>DPAD</a>

  • Use as keyboard: <a href='quick://dpad(button(Keys.KEY_W), button(Keys.KEY_S), button(Keys.KEY_A), button(Keys.KEY_D))'>WSAD</a> or <a href='quick://dpad(button(Keys.KEY_UP), button(Keys.KEY_DOWN), button(Keys.KEY_LEFT), button(Keys.KEY_RIGHT))'>Arrows</a>

  • Use as <a href='quick://smooth(8, 0.78, 2.0, feedback(RIGHT, 256, ball(mouse())))'>mouse</a> or <a href='quick://feedback(LEFT, 4096, 16.0, ball(XY(mouse(Rels.REL_HWHEEL), mouse(Rels.REL_WHEEL))))'>mouse wheel</a>
"""

MARKUP_GYRO = """
<big>Gyro: Quick settings</big>

  • Setup for aiming when right <a href='quick://mode(RPADTOUCH, mouse(ROLL), None)'>pad is touched</a>
  
  • Setup for aiming when right <a href='quick://mode(LT >= 0.7, mouse(ROLL), None)'>trigger is pushed</a>
  
  • <a href='quick://sens(3.5, 3.5, 3.5, mouse(ROLL))'>Use as mouse</a>
  
  • <a href='quick://cemuhook'>Use with Citra, Cemu or other compatibile emulator</a>
"""


class FirstPage(AEComponent):
	GLADE = "ae/first_page.glade"
	NAME = "first_page"
	CTXS = 0
	PRIORITY = 999
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
	
	def load(self):
		if AEComponent.load(self):
			markup = ""
			if self.editor.get_mode() == Action.AC_PAD:
				markup = MARKUP_PAD
			elif self.editor.get_mode() == Action.AC_STICK:
				markup = MARKUP_STICK
			elif self.editor.get_mode() == Action.AC_GYRO:
				markup = MARKUP_GYRO
			elif self.editor.get_mode() == Action.AC_TRIGGER:
				markup = MARKUP_TRIGGER
			else:
				markup = MARKUP_BUTTON
			
			long_names = {
				'LPAD' : _("Left Pad"),
				'RPAD' : _("Right Pad"),
				'LGRIP' : _("Left Grip"),
				'RGRIP' : _("Right Grip"),
				'LB' : _("Left Bumper"),
				'RB' : _("Right Bumper"),
				'LEFT' : _("Left Trigger"),
				'RIGHT' : _("Right Trigger"),
				'STICK' : _("Stick"),
			}
			
			markup = markup % {
				'what' : long_names.get(nameof(self.editor.get_id()),
								nameof(self.editor.get_id()).title())
			}
			self.builder.get_object("lblMarkup").set_markup(markup.strip(" \r\n\t"))
			return True
	
	def on_lblMarkup_activate_link(self, trash, link):
		self.editor.on_link(link)
