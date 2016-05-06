#!/usr/bin/env python2
"""
SC-Controller - tools

Various stuff that I don't care to fit anywhere else.
"""
from __future__ import unicode_literals

from math import pi as PI
import imp, os, sys, gettext, logging, math
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
	
	pitch = math.atan2(xb , xa)
	yaw   = math.atan2(xn , math.sqrt(1 - xn**2))
	roll  = math.atan2(yn , zn)
	return pitch, yaw, roll


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
