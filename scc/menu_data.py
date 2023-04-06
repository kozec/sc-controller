#!/usr/bin/env python2
"""
SC-Controller - Menu Data

Container for list of menu items + required parsers
"""

from scc.tools import _, set_logging_level
from scc.actions import Action

import json, os

class MenuData(object):
	""" Contains list of menu items. Indexable """
	def __init__(self, *items):
		self.__items = list(items)
	
	
	def generate(self, menuhandler):
		"""
		Converts all generators into MenuItems (by calling .generate() on them)
		and returns generated MenuData.
		
		Returns new MenuData instance.
		"""
		items = []
		for i in self:
			if isinstance(i, MenuGenerator):
				items.extend(i.generate(menuhandler))
			else:
				items.append(i)
		return MenuData(*items)
	
	
	def compress(self):
		for i in self.__items:
			if i.action:
				i.action = i.action.compress()
	
	
	def __len__(self):
		return len(self.__items)
	
	
	def __getitem__(self, index):
		return self.__items[index]
	
	
	def __iter__(self):
		return iter(self.__items)
	
	
	def get_all_actions(self):
		"""
		Returns generator with every action defined in this menu, including
		child actions.
		"""
		for item in self:
			if hasattr(item, "action") and item.action:
				for i in item.action.get_all_actions():
					yield i
	
	
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
			rv.append(i.encode())
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
			for i in range(0, len(data) / 2)
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
			item = None
			if "generator" in i and i["generator"] in MENU_GENERATORS:
				item = MENU_GENERATORS[i["generator"]](**i)
			elif "separator" in i:
				item = Separator(i["name"] if "name" in i else None)
			elif "submenu" in i:
				item = Submenu(i["submenu"],
					i["name"] if "name" in i else None,
					icon = i["icon"] if "icon" in i else None,
				)
			elif "id" not in i:
				# Cannot add menu without ID
				continue
			else:
				action = None
				id = i["id"]
				if id in used_ids:
					# Cannot add duplicate ID
					continue
				if action_parser:
					action = action_parser.from_json_data(i)
				used_ids.add(id)
				label, icon = id, None
				if "name" in i:
					label = i["name"]
				elif action:
					label = action.describe(Action.AC_OSD)
				if "icon" in i:
					icon = i["icon"]
				item = MenuItem(id, label, action, icon=icon)
			m.__items.append(item)
		
		return m
	
	
	@staticmethod
	def from_fileobj(fileobj, action_parser=None):
		"""
		Loads menu from file-like object.
		Actions are parsed only if action_parser is set to ActionParser instance.
		"""
		data = json.loads(fileobj.read())
		return MenuData.from_json_data(data, action_parser)
	
	
	@staticmethod
	def from_file(filename, action_parser=None):
		"""
		Loads menu from file.
		Actions are parsed only if action_parser is set to ActionParser instance.
		"""
		return MenuData.from_fileobj(file(filename, "r"), action_parser)
	
	
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
	def __init__(self, id, label, action=None, callback=None, icon=None):
		self.id = id
		self.label = label
		self.action = action
		self.icon = icon
		self.callback = callback	# If defined, called when user chooses menu instead of using action
		self.widget = None			# May be set by UI code
	
	
	def describe(self):
		"""
		Returns user-friendly description of MenuItem or MenuGenerator.
		"""
		return self.label
	
	
	def encode(self):
		""" Returns item data as dict storable in json (profile) file """
		if self.action and type(self.action) in (str, str):
			rv = { 'action' : self.action }
		elif self.action:
			rv = self.action.encode()
		else:
			rv = {}
		rv['id'] = self.id
		rv['name'] = self.label
		if self.icon: rv['icon'] = self.icon
		return rv


class Separator(MenuItem):
	""" Internally, separator is MenuItem without action and id """
	def __init__(self, label=None):
		MenuItem.__init__(self, None, label)
	
	
	def describe(self):
		if self.label:
			return _("----[ %s ]----") % (self.label,)
		else:
			return _("---- Separator ----")
	
	
	def encode(self):
		if self.label:
			return { "separator" : True, "name" : self.label }
		return { "separator" : True }


class Submenu(MenuItem):
	""" Internally, separator is MenuItem without action and id """
	def __init__(self, filename, label=None, icon=None):
		if not label:
			label = ".".join(os.path.split(filename)[-1].split(".")[0:-1])
		self.filename = filename
		MenuItem.__init__(self, str(id(self)), label=label, icon=icon)
	
	
	def describe(self):
		return self.label + "  " + _(">>")
	
	
	def encode(self):
		rv = { "submenu" : self.filename }
		if self.label: rv["name"] = self.label
		if self.icon: rv["icon"] = self.icon
		return rv


class MenuGenerator(object):
	GENERATOR_NAME = None
	""" Generates list of MenuItems """ 
	
	def __init__(self, **b):
		"""
		Passed are all keys loaded from json dict that defined this generator.
		__init__ of generator should ignore all unknown keys.
		"""
		self.id = None		# Used only in editor
		self.icon = None	# same
	
	
	def describe(self):
		"""
		Returns user-friendly description of MenuItem or MenuGenerator.
		"""
		return "[ %s ] " % (self.__class__.__name__,)
	
	
	def encode(self):
		""" Returns generator data as dict storable in json (profile) file """
		return { "generator" : self.GENERATOR_NAME }
	
	def generate(self, menuhandler):
		return []


# Holds dict of knowm menu ganerators, but generated elsewhere
MENU_GENERATORS = { }
