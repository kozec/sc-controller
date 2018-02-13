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
import os, sys, __main__


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
	or $SCC_SHARED/default_profiles if program is being started from
	script extracted from source tarball
	"""
	return os.path.join(get_share_path(), "default_profiles")


def get_menuicons_path():
	"""
	Returns directory where menu icons are stored.
	~/.config/scc/menu-icons under normal conditions.
	"""
	return os.path.join(get_config_path(), "menu-icons")


def get_default_menuicons_path():
	"""
	Returns directory where default menu icons are stored.
	Probably something like /usr/share/scc/images/menu-icons,
	or $SCC_SHARED/images/menu-icons if program is being started from
	script extracted from source tarball
	"""
	return os.path.join(get_share_path(), "images/menu-icons")


def get_button_images_path():
	"""
	Returns directory where button images are stored.
	/usr/share/scc/images/button-images by default.
	"""
	return os.path.join(get_share_path(), "images/button-images")


def get_menus_path():
	"""
	Returns directory where profiles are stored.
	~/.config/scc/profiles under normal conditions.
	"""
	return os.path.join(get_config_path(), "menus")


def get_default_menus_path():
	"""
	Returns directory where default profiles are stored.
	Probably something like /usr/share/scc/default_profiles,
	or ./default_profiles if program is being started from
	extracted source tarball
	"""
	return os.path.join(get_share_path(), "default_menus")


def get_controller_icons_path():
	"""
	Returns directory where controller icons are stored.
	~/.config/scc/controller-icons under normal conditions.
	
	This directory may not exist.
	"""
	return os.path.join(get_config_path(), "controller-icons")


def get_default_controller_icons_path():
	"""
	Returns directory where controller icons are stored.
	Probably something like /usr/share/scc/images/controller-icons,
	or ./images/controller-icons if program is being started from
	extracted source tarball.
	
	This directory should always exist.
	"""
	return os.path.join(get_share_path(), "images", "controller-icons")


def get_share_path():
	"""
	Returns directory where shared files are kept.
	Usually "/usr/share/scc" or $SCC_SHARED if program is being started from
	script extracted from source tarball
	"""
	if "SCC_SHARED" in os.environ:
		return os.environ["SCC_SHARED"]
	paths = (
		"/usr/local/share/scc/",
		os.path.expanduser("~/.local/share/scc"),
		os.path.join(sys.prefix, "share/scc")
	)
	for path in paths:
		if os.path.exists(path):
			return path
	# No path found, assume default and hope for best
	return "/usr/share/scc"


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
