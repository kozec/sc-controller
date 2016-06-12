#!/usr/bin/env python2
""" Common stuff for UI """
from __future__ import unicode_literals

class ComboSetter(object):
	
	def set_cb(self, cb, key, keyindex=0):
		"""
		Sets combobox value.
		Returns True on success or False if key is not found.
		"""
		model = cb.get_model()
		self._recursing = True
		for row in model:
			if key == row[keyindex]:
				cb.set_active_iter(row.iter)
				self._recursing = False
				return True
		self._recursing = False
		return False
