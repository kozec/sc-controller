#!/usr/bin/env python2
"""
SC-Controller - Paths

Methods in this module are used to determine stuff like where user data is stored,
where sccdaemon can be executed from and similar.

This is gui-only thing, as sccdaemon doesn't really need to load anything what
python can't handle.
All this is needed since I want to have entire thing installable, runnable
from source tarball *and* debugable in working folder.
"""
from scc.sccdaemon import DEFAULT_SOCKET
from gi.repository import GLib
import os, __main__

def get_config_path():
	"""
	Returns configuration directory.
	~/.config/scc under normal conditions.
	"""
	confdir = GLib.get_user_config_dir()
	if confdir is None:
		confdir = os.path.expanduser("~/.config")
	return os.path.join(confdir, "scc")


def get_profiles_path():
	"""
	Returns directory where profiles are stored.
	~/.config/scc/profiles under normal conditions.
	"""
	return os.path.join(get_config_path(), "profiles")


def get_default_profiles_path():
	"""
	Returns directory where default profiles are stored.
	Probably something like /usr/share/scc/default_profiles,
	or ./default_profiles if program is being started from
	extracted source tarball
	"""
	if __main__.__file__.endswith(".py"):
		# Started as script with something like './scc.py'
		local = os.path.join(os.path.split(__file__)[0], "../../default_profiles")
		local = os.path.normpath(local)
		if os.path.exists(local):
			return local
	return "/usr/share/scc/default_profiles"


def get_daemon_path():
	"""
	Returns path to sccdaemon "binary".
	
	Should be /usr/bin/sccdaemon if program is installed or
	./sccdaemon.py if program is being started from extracted source tarball
	"""
	if __main__.__file__.endswith(".py"):
		# Started as script with something like './scc.py'
		local = os.path.join(os.path.split(__file__)[0], "../../sccdaemon.py")
		local = os.path.normpath(local)
		if os.path.exists(local):
			return local
	for x in ("/usr/bin/sccdaemon", "/usr/local/bin/sccdaemon"):
		# TODO: This is maybe possible in less insane way
		if os.path.exists(x):
			return x
	# Nothing found, just hope for miracles...
	return "sccdaemon"


def get_daemon_socket():
	"""
	Returns path to socket that can be used to controll sccdaemon.
	
	Currently it's just default value of ~/.scccontroller.socket
	"""
	return DEFAULT_SOCKET
