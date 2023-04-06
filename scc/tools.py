#!/usr/bin/env python3
"""
SC-Controller - tools

Various stuff that I don't care to fit anywhere else.
"""


from scc.paths import get_controller_icons_path, get_default_controller_icons_path
from scc.paths import get_menuicons_path, get_default_menuicons_path
from scc.paths import get_profiles_path, get_default_profiles_path
from scc.paths import get_menus_path, get_default_menus_path
from scc.paths import get_button_images_path
from math import pi as PI, sin, cos, atan2, sqrt
import os, sys, ctypes, imp, shlex, gettext, logging

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
		msg = msg if type(msg) is str else str(msg).decode("utf-8")
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
	s = [ str(x).encode("utf-8") for x in lst ]
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


def profile_is_override(name):
	"""
	Returns True if named profile exists both in user config directory and
	default_profiles directory.
	"""
	filename = "%s.sccprofile" % (name,)
	if os.path.exists(os.path.join(get_profiles_path(), filename)):
		if os.path.exists(os.path.join(get_default_profiles_path(), filename)):
			return True
	return False


def profile_is_default(name):
	"""
	Returns True if named profile exists in default_profiles directory, even
	if it is overrided by profile in user config directory.
	"""
	filename = "%s.sccprofile" % (name,)
	return os.path.exists(os.path.join(get_default_profiles_path(), filename))


def get_profile_name(path):
	"""
	Returns profile name for specified path. Basically removes path and
	.sccprofile and .mod extension.
	"""
	parts = os.path.split(path)[-1].split(".")
	if parts[-1] == "mod": parts = parts[0:-1]
	if parts[-1] == "sccprofile": parts = parts[0:-1]
	return ".".join(parts)


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


def find_icon(name, prefer_bw=False, paths=None, extensions=("png", "svg")):
	"""
	Returns (filename, has_colors) for specified icon name.
	This is done by searching for name + '.png' and name + ".bw.png"
	in user and default menu-icons folders. ".svg" is also supported, but only
	if no pngs are found.
	
	If both colored and grayscale version is found, colored is returned, unless
	prefer_bw is set to True.
	
	paths defaults to icons for menuicons
	
	Returns (None, False) if icon cannot be found.
	"""
	if name is None:
		# Special case, so code can pass menuitem.icon directly
		return None, False
	if paths is None:
		paths = get_default_menuicons_path(), get_menuicons_path()
	if name.endswith(".bw"):
		name = name[0:-3]
	for extension in extensions:
		gray_filename = "%s.bw.%s" % (name, extension)
		colors_filename = "%s.%s" % (name, extension)
		gray, colors = None, None
		for p in paths:
			# Check grayscale
			if gray is None:
				path = os.path.join(p, gray_filename)
				if os.path.exists(path):
					if prefer_bw:
						return path, False
					gray = path
			# Check colors
			if colors is None:
				path = os.path.join(p, colors_filename)
				if os.path.exists(path):
					if not prefer_bw:
						return path, True
					colors = path
		if colors is not None:
			return colors, True
		if gray is not None:
			return gray, False
	return None, False


def find_button_image(name, prefer_bw=False):
	""" Similar to find_icon, but searches for button image """
	return find_icon(nameof(name), prefer_bw,
			paths=[get_button_images_path()], extensions=("svg",))


def menu_is_default(name):
	"""
	Returns True if named menu exists in default_menus directory, even
	if it is overrided by menu in user config directory.
	"""
	return os.path.exists(os.path.join(get_default_menus_path(), name))


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
	user_path = os.environ['PATH'].split(":")
	# Try to add the standard binary paths if not present in PATH
	for d in ["/sbin", "/bin", "/usr/sbin", "/usr/bin"]:
		if d not in user_path:
			user_path.append(d)
	for i in user_path:
		path = os.path.join(i, name)
		if os.path.exists(path):
			return path
	# Not found, return name back and hope for miracle
	return name


def find_library(libname):
	"""
	Search for 'libname.so'.
	Returns library loaded with ctypes.CDLL
	Raises OSError if library is not found
	"""
	base_path = os.path.dirname(__file__)
	lib, search_paths = None, []
	so_extensions = [ ext for ext, _, typ in imp.get_suffixes()
			if typ == imp.C_EXTENSION ]
	for extension in so_extensions:
		search_paths += [
			os.path.abspath(os.path.normpath(
				os.path.join( base_path, '..', libname + extension ))),
			os.path.abspath(os.path.normpath(
				os.path.join( base_path, '../..', libname + extension )))
			]
	
	for path in search_paths:
		if os.path.exists(path):
			lib = path
			break
	
	if not lib:
		raise OSError('Cant find %s.so. searched at:\n %s' % (
			libname, '\n'.join(search_paths)))
	return ctypes.CDLL(lib)


def find_gksudo():
	"""
	Searchs for gksudo or other known graphical sudoing tool.
	Returns list of arguments.
	"""
	SUDOS = ["gksudo", "gksu", "kdesudo", "pkexec", "xdg-su"]
	for name in SUDOS:
		args = name.split(" ")
		bin = find_binary(args[0])
		if bin != args[0]:
			return args
	return None


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
