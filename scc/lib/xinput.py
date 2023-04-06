#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
XInput tools

Interfaces with XInput by calling `xinput` command.
Currently allows only querying list of xinput devices and floating them.

Copyright (C) 2017 Kozec

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as published by
the Free Software Foundation

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""


import logging, re, subprocess
log = logging.getLogger("XI")

RE_DEVICE = re.compile(r"[ \t⎜]+↳ (.*)\tid=([0-9]+)[ \t]+\[([a-z ]+)")

def get_devices():
	"""
	Returns list of devices reported by xinput.
	"""
	rv = []
	try:
		lst = (subprocess.Popen([ "xinput" ], stdout=subprocess.PIPE, stdin=None)
			.communicate()[0]
			.decode("utf-8"))
	except:
		# calling xinput failed, return empty list
		return rv
	
	for line in lst.split("\n"):
		match = RE_DEVICE.match(line)
		if match:
			name, id, type = match.groups()
			name = name.strip(" \t")
			while "  " in type:
				type = type.replace("  ", " ")
			id = int(id)
			rv.append(XIDevice(id, name, type))
	return rv


class XIDevice(object):
	def __init__(self, id, name, type):
		self._id = id
		self._name = name
		self._type = type
	
	
	def float(self):
		""" Removes slave device from its current master """
		subprocess.Popen([ "xinput", "float", str(self._id) ])
		log.info("Deatached device %s from its master", self._id)
	
	
	def get_name(self):
		return self._name
	
	
	def is_pointer(self):
		""" Returns True if device is pointer, ie can controll mouse """
		return "pointer" in self._type
	
	
	def is_slave(self):
		""" Returns True if device is slave pointer or slave keyboard """
		return "slave" in self._type
	
	
	def __str__(self):
		return "<XIDevice #%s '%s' (%s)>" % (self._id, self._name, self._type)
	
	__repr__ = __str__
