#!/usr/bin/python2
from __future__ import unicode_literals

from scc.mapper import Mapper
from scc.uinput import Dummy

import traceback, logging, time, os
log = logging.getLogger("WindowsMapper")

class WindowsMapper(Mapper):
	
	def _create_device(self, cls, name):
		return Dummy()
	
	def _create_gamepad(self, enabled, poller):
		return Dummy()
