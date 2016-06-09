#!/usr/bin/env python2
"""
SC-Controller - tools

Various stuff that I don't care to fit anywhere else.
"""
from __future__ import unicode_literals

from scc.paths import get_profiles_path, get_default_profiles_path
from scc.paths import get_menus_path, get_default_menus_path
from math import pi as PI, sin, cos, atan2, sqrt
import imp, os, sys, gettext, logging
log = logging.getLogger("tools.py")
_ = lambda x : x

LOG_FORMAT				= "%(levelname)s %(name)-13s %(message)s"

def init_logging():
	"""
	Initializes logging, sets custom logging format and adds one
	logging level with name and method to call.
	"""
	logging.basicConfig(format=LOG_FORMAT)
	logger = logging.getLogger()
	# Rename levels
	logging.addLevelName(10, "D")	# Debug
	logging.addLevelName(20, "I")	# Info
	logging.addLevelName(30, "W")	# Warning
	logging.addLevelName(40, "E")	# Error
	# Create additional, "verbose" level
	logging.addLevelName(15, "V")	# Verbose
	# Add 'logging.verbose' method
	def verbose(self, msg, *args, **kwargs):
		return self.log(15, msg, *args, **kwargs)
	logging.Logger.verbose = verbose
	# Wrap Logger._log in something that can handle utf-8 exceptions
	old_log = logging.Logger._log
	def _log(self, level, msg, args, exc_info=None, extra=None):
		args = tuple([
			(c if type(c) is unicode else str(c).decode("utf-8"))
			for c in args
		])
		msg = msg if type(msg) is unicode else str(msg).decode("utf-8")
		old_log(self, level, msg, args, exc_info, extra)
	logging.Logger._log = _log


def set_logging_level(verbose, debug):
	""" Sets logging level """
	logger = logging.getLogger()
	if debug:		# everything
		logger.setLevel(0)
	elif verbose:	# everything but debug
		logger.setLevel(11)
	else:			# INFO and worse
		logger.setLevel(20)


def strip_none(*lst):
	""" Returns lst without trailing None's """
	while len(lst) and lst[-1] is None:
		lst = lst[0:-1]
	return lst


def ensure_size(n, lst):
	"""
	Returns copy of lst with size 'n'.
	If lst is shorter, None's are appended.
	If lst is longer, it is cat.
	"""
	l = list(lst)
	while len(l) < n : l.append(None)
	return l[0:n]


def quat2euler(q0, q1, q2, q3):
	"""
	Converts quaterion to (pitch, yaw, roll).
	Values are in -PI to PI range.
	"""
	qq0, qq1, qq2, qq3 = q0**2, q1**2, q2**2, q3**2
	xa = qq0 - qq1 - qq2 + qq3
	xb = 2 * (q0 * q1 + q2 * q3)
	xn = 2 * (q0 * q2 - q1 * q3)
	yn = 2 * (q1 * q2 + q0 * q3)
	zn = qq3 + qq2 - qq0 - qq1
	
	pitch = atan2(xb , xa)
	yaw   = atan2(xn , sqrt(1 - xn**2))
	roll  = atan2(yn , zn)
	return pitch, yaw, roll


def point_in_gtkrect(rect, x, y):
	return (x > rect.x and y > rect.y and
		x < rect.x + rect.width and y < rect.y + rect.height)


def anglediff(a1, a2):
	return (a2 - a1 + PI) % (2.0*PI) - PI


def static_vars(**kwargs):
	"""Static variable func decorator"""

	def decorate(func):
		"""inner function used to add kwargs attribute to a func"""
		for k in kwargs:
			setattr(func, k, kwargs[k])
		return func
	return decorate


def get_so_extensions():
	"""Return so file extenstion compatible with python and pypy"""
	for ext, _, typ in imp.get_suffixes():
		if typ == imp.C_EXTENSION:
			yield ext


def find_profile(name):
	"""
	Returns filename for specified profile name.
	This is done by searching for name + '.sccprofile' in ~/.config/scc/profiles
	first and in /usr/share/scc/default_profiles if file is not found in first
	location.
	
	Returns None if profile cannot be found.
	"""
	filename = "%s.sccprofile" % (name,)
	for p in (get_profiles_path(), get_default_profiles_path()):
		path = os.path.join(p, filename)
		if os.path.exists(path):
			return path
	return None


def find_menu(name):
	"""
	Returns filename for specified menu name.
	This is done by searching for name in ~/.config/scc/menus
	first and in /usr/share/scc/default_menus later.
	
	Returns None if menu cannot be found.
	"""
	for p in (get_menus_path(), get_default_menus_path()):
		path = os.path.join(p, name)
		if os.path.exists(path):
			return path
	return None


def find_lib(name, base_path):
	"""
	Returns (filename, search_paths) if named library is found
	or (None, search_paths) if not.
	"""
	search_paths = []
	for extension in get_so_extensions():
		search_paths.append(os.path.abspath(os.path.normpath(os.path.join( base_path, '..', name + extension ))))
		search_paths.append(os.path.abspath(os.path.normpath(os.path.join( base_path, '../..', name + extension ))))
	for path in search_paths:
		if os.path.exists(path):
			return path, search_paths
	return None, search_paths


def find_binary(name):
	"""
	Returns full path to script or binary.
	
	With some exceptions, this is done simply by searching PATH environment variable.
	"""
	if name in ("osd_daemon", "scc-osd-daemon"):
		# Special case, this one is not supposed to go to /usr/bin
		return os.path.join(os.path.split(__file__)[0], "osd", "osd_daemon.py")
	for i in os.environ['PATH'].split(":"):
		path = os.path.join(i, name)
		if os.path.exists(path):
			return path
	# Not found, return name back and hope for miracle
	return name


PId4 = PI / 4.0
def circle_to_square(x, y):
	"""
	Projects coordinate in circle (of radius 1.0) to coordinate in square.
	"""
	# Adapted from http://theinstructionlimit.com/squaring-the-thumbsticks
	
	# Determine the theta angle
	angle = atan2(y, x) + PI
	
	squared = 0, 0
	# Scale according to which wall we're clamping to
	# X+ wall
	if angle <= PId4 or angle > 7.0 * PId4:
		squared = x * (1.0 / cos(angle)), y * (1.0 / cos(angle))
	# Y+ wall
	elif angle > PId4 and angle <= 3.0 * PId4:
		squared = x * (1.0 / sin(angle)), y * (1.0 / sin(angle))
	# X- wall
	elif angle > 3.0 * PId4 and angle <= 5.0 * PId4:
		squared = x * (-1.0 / cos(angle)), y * (-1.0 / cos(angle))
	# Y- wall
	elif angle > 5.0 * PId4 and angle <= 7.0 * PId4:
		squared = x * (-1.0 / sin(angle)), y * (-1.0 / sin(angle))
	else:
		raise ValueError("Invalid angle...?")
	
	return squared
