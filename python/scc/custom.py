#!/usr/bin/env python2
"""
SC-Controller - Custom module loader

Loads ~/.config/scc/custom.py, if present. This allows injecting custom action
classes by user and breaking everything in very creative ways.

load_custom_module function needs to be called by daemon and GUI, so it exists
in separate module.
"""

from scc.paths import get_config_path
import os

def load_custom_module(log, who_calls="daemon"):
	"""
	Loads and imports ~/.config/scc/custom.py, if it is present and displays
	big, fat warning in such case.
	
	Returns True if file exists.
	"""
	
	filename = os.path.join(get_config_path(), "custom.py")
	if os.path.exists(filename):
		log.warning("=" * 60)
		log.warning("Loading %s" % (filename, ))
		log.warning("If you don't know what this means or you haven't "
			"created it, stop daemon right now and remove this file.")
		log.warning("")
		log.warning("Also try removing it if %s crashes "
			"shortly after this message." % (who_calls,))
		
		import imp
		imp.load_source("custom", filename)
		log.warning("=" * 60)
		return True
	return False
