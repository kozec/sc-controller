#!/usr/bin/env python2
"""
Imports VDFFZ profile and converts it to Profile object.
VDFFZ is just VDF encapsulated in json, so this just gets one value and calls
VDFProfile to decode rest.
"""
from vdf import VDFProfile
from scc.lib.vdf import parse_vdf

import json, logging
log = logging.getLogger("import.vdffz")

class VDFFZProfile(VDFProfile):
	def load(self, filename):
		try:
			data = json.loads(open(filename, "r").read())
		except Exception, e:
			raise ValueError("Failed to parse JSON")
		if 'ConfigData' not in data:
			raise ValueError("ConfigData missing in JSON")
		self.load_data(parse_vdf(data['ConfigData'].encode('utf-8')))
