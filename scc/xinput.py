#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
SC-Controller - XInput tools

Interfaces with XInput by calling `xinput` command.
Currently allows only querying list of xinput devices and floating them.
"""
from __future__ import unicode_literals

import logging, re, subprocess
log = logging.getLogger("XI")

RE_DEVICE = re.compile(r"[ \t⎜]+↳ (.*)\tid=([0-9]+)[ \t]+\[([a-z ]+)")

def get_devices():
	"""
	Returns list of devices reported by xinput.
	"""
	rv = []
	#try:
	lst = (subprocess.Popen([ "xinput" ], stdout=subprocess.PIPE, stdin=None)
		.communicate()[0]
		.decode("utf-8"))
	#except:
	#	# calling xinput failed, return empty list
	#	return rv
	
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


if __name__ == "__main__":
	devs = [
		d for d in get_devices()
		if "X-Box" in d.get_name() and d.is_slave() and d.is_pointer()
	]
	for d in devs:
		print d
		d.float()
	


def fix_xinput(self, mapper):
	"""
	Reads list of xinput devices and checks if there is controller device
	for specified mapper listed under 'Virtual core pointer' parent.
	If it is, then calls xinput again to deatach that controller.
	
	This is done to prevent controller emulation from emulating mouse,
	because that's apparently feature of xinput for whatever reason.
	This process can be disabled by setting 
	"""
	# Check stuff
	name = mapper.get_gamepad_name()
	if not self.xdisplay:				# xinput needs X
		return
	if not Config()["fix_xinput"]:		# disabled by user
		return
	if not name:						# Dummy
		return
	
	# Grab device ID
	deatach_id = None
	try:
		lst = (subprocess.Popen([ "xinput" ], stdout=subprocess.PIPE, stdin=None)
			.communicate()[0]
			.decode("utf-8"))
		for line in lst.split("\n"):
			if "slave  pointer" in line:
				if "↳ " + name in line:
					match = re.search("id=([0-9]+)", line)
					if match:
						deatach_id = match.group(1)
	except:
		# xinput failed, bad, but not fatal
		pass
	
	# Deatach
	if deatach_id:
		try:
			subprocess.Popen([ "xinput", "float", str(deatach_id) ])
			log.info("Deatached device %s from Virtual core pointer", deatach_id)
		except:
			# xinput failed, still not fatal
			pass
