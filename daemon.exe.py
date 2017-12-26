#!/c/Python27/python
import os, sys
sys.path.insert(0, ".")
import scc.platform.windows.override_paths

from scc.sccdaemon import SCCDaemon
from scc.paths import get_pid_file
from scc.tools import init_logging

import os, argparse

init_logging()
parser = argparse.ArgumentParser()
parser.add_argument('profile', type=str, nargs='*')
parser.add_argument('--alone', action='store_true', help="prevent scc-daemon from launching osd-daemon and autoswitch-daemon.")
daemon = SCCDaemon(get_pid_file(), None)
args = parser.parse_args()
daemon.alone = args.alone

profile = " ".join(args.profile)
if profile:
	daemon.set_default_profile(profile)
	# If no default_profile is set, daemon will try to load last used
	# from config

daemon.debug()
