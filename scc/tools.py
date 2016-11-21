#!/usr/bin/env python2
"""
SC-Controller - tools

Various stuff that I don't care to fit anywhere else.
"""
from __future__ import unicode_literals

from scc.paths import get_controller_icons_path, get_default_controller_icons_path
from scc.paths import get_profiles_path, get_default_profiles_path
from scc.paths import get_menus_path, get_default_menus_path
from scc.uinput import Axes, Rels
from math import pi as PI, sin, cos, atan2, sqrt
import os, sys, shlex, gettext, logging

HAVE_POSIX1E = False
try:
	import posix1e
	HAVE_POSIX1E = True
except ImportError:
	pass

log = logging.getLogger("tools.py")
_ = lambda x : x

LOG_FORMAT				= "%(levelname)s %(name)-13s %(message)s"

def init_logging(prefix="", suffix=""):
	"""
	Initializes logging, sets custom logging format and adds one
	logging level with name and method to call.
	
	prefix and suffix arguments can be used to modify log level prefixes.
	"""
	logging.basicConfig(format=LOG_FORMAT)
	logger = logging.getLogger()
	# Rename levels
	logging.addLevelName(10, prefix + "D" + suffix)	# Debug
	logging.addLevelName(20, prefix + "I" + suffix)	# Info
	logging.addLevelName(30, prefix + "W" + suffix)	# Warning
	logging.addLevelName(40, prefix + "E" + suffix)	# Error
	# Create additional, "verbose" level
	logging.addLevelName(15, prefix + "V" + suffix)	# Verbose
	# Add 'logging.verbose' method
	def verbose(self, msg, *args, **kwargs):
		return self.log(15, msg, *args, **kwargs)
	logging.Logger.verbose = verbose
	# Wrap Logger._log in something that can handle utf-8 exceptions
	old_log = logging.Logger._log
	def _log(self, level, msg, args, exc_info=None, extra=None):
		args = tuple([
			(str(c).decode("utf-8") if type(c) is str else c)
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
	while len(lst) and not lst[-1] and lst[-1] not in (Axes.ABS_X, Rels.REL_X):
		lst = lst[0:-1]
	return lst


def ensure_size(n, lst, fill_with=None):
	"""
	Returns copy of lst with size 'n'.
	If lst is shorter, None's are appended.
	If lst is longer, it is cat.
	"""
	l = list(lst)
	while len(l) < n : l.append(fill_with)
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
	""" Excpects values in radians """
	return (a2 - a1 + PI) % (2.0*PI) - PI


def degdiff(a1, a2):
	""" Excpects values in degrees """
	return (a2 - a1 + 180.0) % 360.0 - 180.0


def nameof(e):
	"""
	If 'e' is enum value, returns e.name.
	Otherwise, returns str(e).
	"""
	return e.name if hasattr(e, "name") else str(e)


def shjoin(lst):
	""" Joins list into shell-escaped, utf-8 encoded string """
	s = [ unicode(x).encode("utf-8") for x in lst ]
	#   - escape quotes
	s = [ x.encode('string_escape') if (b'"' in x or b"'" in x) else x for x in s ]
	#   - quote strings with spaces
	s = [ b"'%s'" % (x,) if b" " in x else x for x in s ]
	return b" ".join(s)


def shsplit(s):
	""" Returs original list from what shjoin returned """
	lex = shlex.shlex(s, posix=True)
	lex.escapedquotes = b'"\''
	lex.whitespace_split = True
	return [ x.decode('utf-8') for x in list(lex) ]


def static_vars(**kwargs):
	"""Static variable func decorator"""

	def decorate(func):
		"""inner function used to add kwargs attribute to a func"""
		for k in kwargs:
			setattr(func, k, kwargs[k])
		return func
	return decorate


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


def find_controller_icon(name):
	"""
	Returns filename for specified controller icon name.
	This is done by searching for name in ~/.config/controller-icons
	first and in /usr/share/scc/images/controller-icons later.
	
	Returns None if icon cannot be found.
	"""
	for p in (get_controller_icons_path(), get_default_controller_icons_path()):
		path = os.path.join(p, name)
		if os.path.exists(path):
			return path
	return None


def find_binary(name):
	"""
	Returns full path to script or binary.
	
	With some exceptions, this is done simply by searching PATH environment variable.
	"""
	if name.startswith("scc-osd-daemon"):
		# Special case, this one is not supposed to go to /usr/bin
		return os.path.join(os.path.split(__file__)[0], "x11", "scc-osd-daemon.py")
	if name.startswith("scc-autoswitch-daemon"):
		# As above
		return os.path.join(os.path.split(__file__)[0], "x11", "scc-autoswitch-daemon.py")
	for i in os.environ['PATH'].split(":"):
		path = os.path.join(i, name)
		if os.path.exists(path):
			return path
	# Not found, return name back and hope for miracle
	return name


def check_access(filename, write_required=True):
	"""
	Checks if user has read and optionaly write access to specified file.
	Uses acl first and possix file permisions if acl cannot be used.
	Returns true only if user has both required access rights.
	"""
	if HAVE_POSIX1E:
		for pset in posix1e.ACL(file=filename):
			if pset.tag_type == posix1e.ACL_USER and pset.qualifier == os.geteuid():
				if pset.permset.test(posix1e.ACL_READ) and (not write_required or pset.permset.test(posix1e.ACL_WRITE)):
					return True
			if pset.tag_type == posix1e.ACL_GROUP and pset.qualifier in os.getgroups():
				if pset.permset.test(posix1e.ACL_READ) and (not write_required or pset.permset.test(posix1e.ACL_WRITE)):
					return True
	if write_required:
		return os.access(filename, os.R_OK | os.W_OK)
	return os.access(filename, os.R_OK)


def strip_gesture(gstr):
	"""
	Converts gesture string to version where stroke lenght is ignored.
	
	That means removing repeating characters and adding 'i' to front.
	"""
	last, uniq = None, []
	for x in gstr:
		if x != last:
			uniq.append(x)
		last = x
	if uniq[0] != 'i':
		uniq = [ 'i' ] + uniq
	return "".join(uniq)


clamp = lambda low, value, high : min(high, max(low, value))


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
