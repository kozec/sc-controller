#!/usr/bin/env python2
"""
SC-Controller - Profile

Handles loading, storing and querying confir file
"""
from __future__ import unicode_literals

from scc.paths import get_config_path
from scc.profile import Encoder

import os, json, logging
log = logging.getLogger("Config")


class Config(object):
	DEFAULTS = {
		"autoswitch_osd":	True,	# True to show OSD message when profile is autoswitched
		"autoswitch":		[],		# Empty list of conditions
		"recent_max":		10,		# Number of profiles to keep
		"recent_profiles":	[		# Hard-coded list of profiles from default_profiles/
			# This is actually updated by scc-osd-daemon. It may sound random,
			# but that's only thing actually using this list.
			"Desktop",
			"XBox Controller with High Precision Camera",
			"XBox Controller"
		],
		"osd_colors": {
			"background": "000000",
			"border": "00FF00",
			"text": "00FF00",
			"menuitem_border": "004000",
			"menuitem_hilight": "000070",
			"menuitem_hilight_text": "FFFFFF",
			"menuitem_hilight_border": "00FF00",
			"menuseparator": "109010",
		},
		"osk_colors": {
			'hilight' : '00688D',
			'pressed' : '1A9485',
		}
	}
	
	def __init__(self):
		self.filename = os.path.join(get_config_path(), "config.json")
		self.reload()
	
	
	def reload(self):
		""" (Re)loads configuration. Works as load(), but handles exceptions """
		try:
			self.load()
		except Exception, e:
			log.warning("Failed to load configuration; Creating new one.")
			log.warning("Reason: %s", (e,))
			self.create()
		if self.check_values():
			self.save()
	
	
	def check_values(self):
		"""
		Check if all required values are in place and fill by default
		whatever is missing.
		
		Returns True if anything gets changed.
		"""
		rv = False
		for d in self.DEFAULTS:
			if d not in self.values:
				self.values[d] = self.DEFAULTS[d]
				rv = True
		# Special check for nested dicts
		for key in ("osd_colors", "osk_colors"):
			if len(self.DEFAULTS[key]) != len(self.values[key]):
				src = self.DEFAULTS[key]
				self.values[key] = { k:src[k] for k in src }
		return rv
	
	
	def load(self):
		self.values = json.loads(open(self.filename, "r").read())
	
	
	def create(self):
		""" Creates new, empty configuration """
		self.values = {}
		self.check_values()
		self.save()
	
	
	def save(self):
		""" Saves configuration file """
		# Check & create directory
		if not os.path.exists(get_config_path()):
			os.makedirs(get_config_path())
		# Save
		data = { k:self.values[k] for k in self.values }
		jstr = Encoder(sort_keys=True, indent=4).encode(data)
		file(self.filename, "w").write(jstr)
		log.debug("Configuration saved")
	
	
	def __iter__(self):
		for k in self.values:
			yield k
	
	def get(self, key):
		return self.values[key]
	
	def set(self, key, value):
		self.values[key] = value
	
	__getitem__ = get
	__setitem__ = set
	
	def __contains__(self, key):
		""" Returns true if there is such value """
		return key in self.values

