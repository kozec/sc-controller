#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.button_chooser import ButtonChooser
import logging
log = logging.getLogger("AxisChooser")

class AxisChooser(ButtonChooser):
	GLADE = "button_chooser.glade"
	IMAGES = { "vbButChooser" : "axistrigger.svg" }
	
	
	def setup_widgets(self):
		ButtonChooser.setup_widgets(self)
		self.builder.get_object("lblClickOn").set_text("click any axis")
		self.builder.get_object("btnGrabKey").set_visible(False)
