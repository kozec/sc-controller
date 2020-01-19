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
from scc.find_library import find_library
import os, sys, ctypes, __main__


def get_config_path():
	"""
	Returns configuration directory.
	~/.config/scc under normal conditions.
	"""
	return lib_bindings.scc_get_config_path().decode("utf-8")


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
	# TODO: Get this from c
	return os.path.join(get_config_path(), "menus")


def get_default_menus_path():
	"""
	Returns directory where default profiles are stored.
	Probably something like /usr/share/scc/default_profiles,
	or ./default_profiles if program is being started from
	extracted source tarball
	"""
	# TODO: Get this from c
	return os.path.join(get_share_path(), "default_menus")


def get_controller_icons_path():
	"""
	Returns directory where controller icons are stored.
	~/.config/scc/controller-icons under normal conditions.
	
	This directory may not exist.
	"""
	return lib_bindings.scc_get_controller_icons_path().decode("utf-8")


def get_default_controller_icons_path():
	"""
	Returns directory where controller icons are stored.
	Probably something like /usr/share/scc/images/controller-icons,
	or ./images/controller-icons if program is being started from
	extracted source tarball.
	
	This directory should always exist.
	"""
	return lib_bindings.scc_get_default_controller_icons_path().decode("utf-8")


def get_share_path():
	"""
	Returns directory where shared files are kept.
	Usually "/usr/share/scc" or $SCC_SHARED if program is being started from
	script extracted from source tarball
	"""
	return lib_bindings.scc_get_share_path().decode("utf-8")


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
	return str(lib_bindings.scc_get_daemon_socket())


lib_bindings = find_library("libscc-bindings")

lib_bindings.scc_get_config_path.argtypes = [ ]
lib_bindings.scc_get_config_path.restype = ctypes.c_char_p
lib_bindings.scc_get_daemon_socket.argtypes = [ ]
lib_bindings.scc_get_daemon_socket.restype = ctypes.c_char_p
lib_bindings.scc_get_share_path.argtypes = [ ]
lib_bindings.scc_get_share_path.restype = ctypes.c_char_p
lib_bindings.scc_get_controller_icons_path.argtypes = [ ]
lib_bindings.scc_get_controller_icons_path.restype = ctypes.c_char_p
lib_bindings.scc_get_default_controller_icons_path.argtypes = [ ]
lib_bindings.scc_get_default_controller_icons_path.restype = ctypes.c_char_p

