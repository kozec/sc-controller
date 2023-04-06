#!/usr/bin/env python2
"""
SC-Controller - Autoswitch Daemon

Observes active window and commands scc-daemon to change profiles as needed.
"""


from scc.x11.autoswitcher import AutoSwitcher
from scc.lib import xwrappers as X
from scc.tools import set_logging_level, find_profile
from scc.paths import get_daemon_socket
from scc.config import Config

import os, sys, time, socket, threading, signal, logging
log = logging.getLogger("AS-Daemon")


if __name__ == "__main__":
	from scc.tools import init_logging, set_logging_level
	from scc.paths import get_share_path
	init_logging(suffix=" AS ")
	set_logging_level('debug' in sys.argv, 'debug' in sys.argv)
	
	if "DISPLAY" not in os.environ:
		log.error("DISPLAY env variable not set.")
		sys.exit(1)
	
	d = AutoSwitcher()
	signal.signal(signal.SIGINT, d.sigint)
	d.run()
	sys.exit(d.exit_code)
