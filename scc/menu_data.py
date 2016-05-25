#!/usr/bin/env python2
"""
SC-Controller - Menu Data

Container for list of menu items + required parsers
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level
from scc.actions import Action

import json

class MenuData(object):
	""" Contains list of menu items. Indexable """
	def __init__(self, *items):
		self.__items = list(items)
	
	
	def __len__(self):
		return len(self.__items)
	
	
	def __getitem__(self, index):
		return self.__items[index]
	
	
	def __iter__(self):
		return iter(self.__items)
	
	
	def __str__(self):
		return ("<Menu with IDs: '" 
			+ ("', '".join([ i.id for i in self.__items ])) + "' >")
	
	
	def get_by_id(self, id):
		"""
		Returns item with specified ID.
		Throws KeyError if there is no such item.
		"""
		for a in self:
			if a.id == id:
				return a
		raise KeyError("No such item")
	
	
	def index(self, a):
		return self.__items.index(a)
	
	
	def encode(self):
		""" Returns menu data as dict storable in json (profile) file """
		rv = []
		for i in self:
			if i.action:
				item_data = i.action.encode()
			else:
				item_data = {}
			item_data['id'] = i.id
			item_data['name'] = i.label
			rv.append(item_data)
		return rv
	
	
	@staticmethod
	def from_args(data):
		"""
		Parses list of arguments in [id1, label1, id2, label2 ...] format.
		Throws ValueError if number of items in 'data' is odd.
		"""
		if len(data) % 2 != 0:
			raise ValueError("Odd number of items")
		if len(data) < 1:
			raise ValueError("Not items")
		
		# Rearange data into list of pair tuples
		data = [
			(data[i * 2], data[(i * 2) + 1])
			for i in xrange(0, len(data) / 2)
		]
		
		# Parse data
		m = MenuData()
		for id, label in data:
			m.__items.append(MenuItem(id, label))
		return m
	
	
	@staticmethod
	def from_json_data(data, action_parser=None):
		"""
		Loads menu from parsed JSON dict.
		Actions are parsed only if action_parser is set to ActionParser instance.
		"""
		m = MenuData()
		used_ids = set()
		for i in data:
			if "id" not in i:
				# Cannot add menu without ID
				continue
			action = None
			id = i["id"]
			if id in used_ids:
				# Cannot add duplicate ID
				continue
			if action_parser:
				action = action_parser.from_json_data(i)
			used_ids.add(id)
			label = id
			if "name" in i:
				label = i["name"]
			elif action:
				label = action.describe(Action.AC_OSD)
			m.__items.append(MenuItem(id, label, action))
		
		return m
	
	
	@staticmethod
	def from_profile(filename, menuname, action_parser=None):
		"""
		Loads menu from JSON profile file.
		Actions are parsed only if action_parser is set to ActionParser instance.
		
		Menus are stored as list under <root>/menus/<menuname>.
		Throws ValueError if specified file cannot be parsed or
		specified menu cannot be found.
		"""
		data = json.loads(open(filename, "r").read())
		if "menus" not in data:
			raise ValueError("Menu not found")
		if menuname not in data["menus"]:
			raise ValueError("Menu not found")
		
		return MenuData.from_json_data(data["menus"][menuname], action_parser)


class MenuItem(object):
	""" Really just dummy container """
	def __init__(self, id, label, action=None):
		self.id = id
		self.label = label
		self.action = action
		self.widget = None	# May be set by UI code
