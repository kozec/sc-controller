#!/usr/bin/env python2
"""
SC-Controller - Autoswitch Daemon

Observes active window and commands scc-daemon to change profiles as needed.
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from scc.lib import xwrappers as X

import os, sys, time, logging
log = logging.getLogger("AutoSwitcher")

class AutoSwitcher(object):
	INTERVAL = 1
	
	def __init__(self):
		self.dpy = X.open_display(os.environ["DISPLAY"])
		self.conds = [
			Condition(title_part="Chromium"),
			Condition(wm_class="Atom")
		]
	
	
	def check(self, *a):
		w = X.get_current_window(self.dpy)
		pars = X.get_window_title(self.dpy, w), X.get_window_class(self.dpy, w)
		for c in self.conds:
			if c.matches(*pars):
				print "MATCH!", c
	
	
	def run(self):
		log.debug("AutoSwitcher started")
		while True:
			self.check()
			time.sleep(self.INTERVAL)
		return 1



class Condition(object):
	"""
	Represents switching condition loaded from configuration file.
	
	Currently, there are 4 ways to match window:
	By exact title, by part of title, by regexp aplied on title and by matching
	window class.
	It's possible to combine all three types of title matching with window class
	matching.
	"""
	
	def __init__(self, title=None, title_part=None, title_regexp=None, wm_class=None):
		"""
		At least one parameter has to be specified; title_regexp has to be
		compiled regular expression.
		"""
		if not ( title or title_part or title_regexp or wm_class ):
			raise ValueError("Empty Condition")
		self.title = title
		self.title_part = title_part
		self.title_regexp = title_regexp
		self.wm_class = wm_class
	
	
	def __str__(self):
		return "<Condition title=%s, title_part=%s, title_regexp=%s, wm_class=%s>" % (
			self.title, self.title_part, self.title_regexp, self.wm_class)
	
	def matches(self, window_title, wm_class):
		"""
		Returns True if condition matches provided window properties.
		
		wm_class is what xwrappers.get_window_class returns, tuple of two strings.
		"""
		if self.wm_class:
			if self.wm_class != wm_class[0] and self.wm_class != wm_class[1]:
				# Window class matching is enabled and window doesn't match
				return False
			
		if self.title and self.title != window_title:
			# Matching exact title is enabled, but title doesn't match
			return False
		
		if self.title_part and self.title_part not in window_title:
			# Matching part of title is enabled, but doesn't match
			return False
		
		if self.title_regexp and not self.title_regexp.match(window_title):
			# Matching by regexp is enabled, but regexp doesn't match
			return False
		
		return True


if __name__ == "__main__":
	from scc.tools import init_logging, set_logging_level
	from scc.paths import get_share_path
	init_logging(suffix=" AutoSwitcher")
	set_logging_level('debug' in sys.argv, 'debug' in sys.argv)
	
	if "DISPLAY" not in os.environ:
		log.error("DISPLAY env variable not set.")
		sys.exit(1)
	
	d = AutoSwitcher()
	d.run()
	sys.exit(d.get_exit_code())
