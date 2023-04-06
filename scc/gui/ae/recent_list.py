#!/usr/bin/env python2
"""
SC-Controller - Action Editor - Recent List Component

Displays page that can edit settings for RecentListMenuGenerator
"""

from scc.tools import _

from scc.gui.ae import AEComponent

import os, logging
log = logging.getLogger("AE.SA")

__all__ = [ 'RecentListGenComponent' ]


class RecentListGenComponent(AEComponent):
	GLADE = "ae/recent_list.glade"
	NAME = "recent_list"
	CTXS = 0
	PRIORITY = 0
	
	def __init__(self, app, editor):
		AEComponent.__init__(self, app, editor)
	
	
	def set_action(self, mode, action):
		pass
	
	
	def get_button_title(self):
		return _("Recent List")
	
	
	def handles(self, mode, action):
		""" Not visible by default """
		return False
	
	
	def set_row_count(self, count):
		self.builder.get_object("sclNumOfProfiles").set_value(count)
	
	
	def get_row_count(self):
		return int(self.builder.get_object("sclNumOfProfiles").get_value())
