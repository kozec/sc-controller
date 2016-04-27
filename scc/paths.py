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
import os, __main__


def get_config_path():
	"""
	Returns configuration directory.
	~/.config/scc under normal conditions.
	"""
	confdir = os.path.expanduser("~/.config")
	if "XDG_CONFIG_HOME" in os.environ:
		confdir = os.environ['XDG_CONFIG_HOME']
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
		local = os.path.join(os.path.split(__file__)[0], "../default_profiles")
		local = os.path.normpath(local)
		if os.path.exists(local):
			return local
	if os.path.exists("/usr/local/share/scc/default_profiles"):
		return "/usr/local/share/scc/default_profiles"
	return "/usr/share/scc/default_profiles"


def get_share_path():
	"""
	Returns directory where shared files are kept.
	Usually "/usr/share/scc" or "./" if program is being started from
	extracted source tarball
	"""
	if __main__.__file__.endswith(".py"):
		# Started as script with something like './scc.py'
		local = os.path.join(os.path.split(__file__)[0], "../")
		local = os.path.normpath(local)
		if os.path.exists(local):
			return local
	if os.path.exists("/usr/local/share/scc/"):
		return "/usr/local/share/scc/"
	return "/usr/share/scc/default_profiles"



def get_daemon_path():
	"""
	Returns path to sccdaemon "binary".
	
	Should be /usr/bin/scc-daemon if program is installed or
	./scc-daemon.py if program is being started from extracted source tarball
	"""
	if __main__.__file__.endswith(".py"):
		# Started as script with something like './scc.py'
		local = os.path.join(os.path.split(__file__)[0], "../scc-daemon.py")
		local = os.path.normpath(local)
		if os.path.exists(local):
			return local
	for x in ("/usr/bin/scc-daemon", "/usr/local/bin/scc-daemon"):
		# TODO: This is maybe possible in less insane way
		if os.path.exists(x):
			return x
	# Nothing found, just hope for miracles...
	return "scc-daemon"


def get_pid_file():
	"""
	Returns path to PID file.
	~/.config/scc/daemon.pid under normal conditions.
	"""
	return os.path.join(get_config_path(), "daemon.pid")


def get_daemon_socket():
	"""
	Returns path to socket that can be used to controll sccdaemon.
	
	~/.config/scc/daemon.socket under normal conditions.
	"""
	return os.path.join(get_config_path(), "daemon.socket")
