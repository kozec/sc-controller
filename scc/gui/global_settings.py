#!/usr/bin/env python2
"""
SC-Controller - Global Settings

Currently setups only one thing...
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.editor import Editor

class GlobalSettings(Editor):
	GLADE = "global_settings.glade"
	
	def __init__(self, app):
		self.app = app
		self.setup_widgets()
