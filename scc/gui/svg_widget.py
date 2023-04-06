#!/usr/bin/env python3
"""
SC-Controller - Background

Changes SVG on the fly and uptates that magnificent image on background with it.
Also supports clicking on areas defined in SVG image.
"""

from scc.tools import _

from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, Rsvg
from xml.etree import ElementTree as ET
from math import sin, cos, pi as PI
from collections import OrderedDict
import os, sys, re, logging

log = logging.getLogger("Background")
ET.register_namespace('', "http://www.w3.org/2000/svg")


class SVGWidget(Gtk.EventBox):
	FILENAME = "background.svg"
	CACHE_SIZE = 50
	
	__gsignals__ = {
			# Raised when mouse is over defined area
			b"hover"	: (GObject.SignalFlags.RUN_FIRST, None, (object,)),
			# Raised when mouse leaves all defined areas
			b"leave"	: (GObject.SignalFlags.RUN_FIRST, None, ()),
			# Raised user clicks on defined area
			b"click"	: (GObject.SignalFlags.RUN_FIRST, None, (object,)),
	}
	
	
	def __init__(self, filename, init_hilighted=True):
		Gtk.EventBox.__init__(self)
		self.cache = OrderedDict()
		self.areas = []
		
		self.connect("motion-notify-event", self.on_mouse_moved)
		self.connect("button-press-event", self.on_mouse_click)
		self.set_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
		
		self.size_override = None
		self.image_width = 1
		self.image_height = 1
		self.set_image(filename)
		self.image = Gtk.Image()
		if init_hilighted:
			self.hilight({})
		self.add(self.image)
		self.show_all()
	
	
	def set_image(self, filename):
		self.current_svg = open(filename, "r").read().decode("utf-8")
		self.cache = OrderedDict()
		self.areas = []
		self.parse_image()
	
	
	def parse_image(self):
		"""
		Goes trought SVG image, searches for all rects named
		'AREA_SOMETHING' and generates area list from it.
		This area list is later used to determine over which button is mouse
		hovering.
		"""
		tree = ET.fromstring(self.current_svg.encode("utf-8"))
		SVGWidget.find_areas(tree, None, self.areas)
		self.image_width =  float(tree.attrib["width"])
		self.image_height = float(tree.attrib["height"])
	
	
	def resize(self, width, height):
		"""
		Overrides image size.
		Doesn't keep aspect ratio and causes cache to be flushed,
		so this may be slow and nasty.
		"""
		self.size_override = width, height
		self.cache = OrderedDict()
	
	
	def on_mouse_click(self, trash, event):
		area = self.on_mouse_moved(trash, event)
		if area is not None:
			self.emit('click', area)
	
	
	def on_mouse_moved(self, trash, event):
		"""
		Not actual signal handler, just called from App.
		"""
		x_offset = (self.get_allocation().width - self.image_width) / 2
		x = event.x - x_offset
		y = event.y
		for a in self.areas:
			if a.contains(x, y):
				self.emit('hover', a.name)
				return a.name
		self.emit('leave')
		return None
	
	
	def get_area(self, id):
		for a in self.areas:
			if a.name == id:
				return a
		return None
	
	
	def get_all_by_prefix(self, prefix):
		"""
		Searchs for areas using specific prefix.
		For prefix "AREA_", returns self.areas arrray. For anything else,
		re-parses current image and searchs recursivelly for anything that matches, so it
		may be good idea to not call this too often.
		"""
		if prefix == "AREA_":
			return self.areas
		lst = []
		tree = ET.fromstring(self.current_svg.encode("utf-8"))
		SVGWidget.find_areas(tree, None, lst, prefix=prefix)
		return lst
	
	
	def get_area_position(self, area_id):
		"""
		Computes and returns area position on image as (x, y, width, height).
		Raises ValueError if such area is not found.
		"""
		# TODO: Maybe cache this?
		a = self.get_area(area_id)
		if a:
			return a.x, a.y, a.w, a.h
		raise ValueError("Area '%s' not found" % (area_id, ))
	
	
	@staticmethod
	def find_areas(xml, parent_transform, areas, get_colors=False, prefix="AREA_"):
		"""
		Recursively searches throught XML for anything with ID of 'AREA_SOMETHING'
		"""
		for child in xml:
			child_transform = SVGEditor.matrixmul(
				parent_transform or SVGEditor.IDENTITY,
				SVGEditor.parse_transform(child))
			if str(child.attrib.get('id')).startswith(prefix):
				# log.debug("Found SVG area %s", child.attrib['id'][5:])
				a = Area(child, child_transform)
				if get_colors:
					a.color = None
					if 'style' in child.attrib:
						style = { y[0] : y[1] for y in [ x.split(":", 1) for x in child.attrib['style'].split(";") ] }
						if 'fill' in style:
							a.color = SVGWidget.color_to_float(style['fill'])
				areas.append(a)
			else:
				SVGWidget.find_areas(child, child_transform, areas, get_colors=get_colors, prefix=prefix)
	
	
	def get_rect_area(self, element):
		"""
		Returns x, y, width and height of rect element relative to document root.
		element can be specified by it's id.
		"""
		if type(element) in (str, str):
			tree = ET.fromstring(self.current_svg.encode("utf-8"))
			SVGEditor.update_parents(tree)
			element = SVGEditor.get_element(tree, element)
		width, height = 0, 0
		x, y = SVGEditor.get_translation(element, absolute=True)
		if 'width' in element.attrib:  width = float(element.attrib['width'])
		if 'height' in element.attrib: height = float(element.attrib['height'])
		
		return x, y, width, height
	
	
	@staticmethod
	def color_to_float(colorstr):
		"""
		Parses color expressed as RRGGBB (as in config) and returns
		three floats of r, g, b, a (range 0 to 1)
		"""
		b, color = Gdk.Color.parse("#" + colorstr.strip("#"))
		if b:
			return color.red_float, color.green_float, color.blue_float, 1
		return 1, 0, 1, 1	# uggly purple
	
	
	def hilight(self, buttons):
		""" Hilights specified button, if same ID is found in svg """
		cache_id = "|".join([ "%s:%s" % (x, buttons[x]) for x in buttons ])
		if not cache_id in self.cache:
			# Ok, this is close to madness, but probably better than drawing
			# 200 images by hand;
			if len(buttons) == 0:
				# Quick way out - changes are not needed
				svg = Rsvg.Handle.new_from_data(self.current_svg.encode("utf-8"))
			else:
				# 1st, parse source as XML
				tree = ET.fromstring(self.current_svg.encode("utf-8"))
				# 2nd, change colors of some elements
				for button in buttons:
					el = SVGEditor.find_by_id(tree, button)
					if el is not None:
						SVGEditor.recolor(el, buttons[button])
					
				# 3rd, turn it back into XML string......
				xml = ET.tostring(tree)
				
				# ... and now, parse that as XML again......
				svg = Rsvg.Handle.new_from_data(xml.encode("utf-8"))
			while len(self.cache) >= self.CACHE_SIZE:
				self.cache.popitem(False)
			if self.size_override:
				w, h = self.size_override
				self.cache[cache_id] = svg.get_pixbuf().scale_simple(
						w, h, GdkPixbuf.InterpType.BILINEAR)
			else:
				self.cache[cache_id] = svg.get_pixbuf()
		
		self.image.set_from_pixbuf(self.cache[cache_id])
	
	
	def get_pixbuf(self):
		""" Returns pixbuf of current image """
		return self.image.get_pixbuf()
	
	
	def edit(self):
		""" Returns new Editor instance bound to this widget """
		return SVGEditor(self)


class Area:
	SPECIAL_CASES = ( "LSTICK", "RSTICK", "DPAD", "ABS", "MOUSE",
		"MINUSHALF", "PLUSHALF", "KEY" )
	
	""" Basicaly just rectangle with name """
	def __init__(self, element, transform):
		self.name = element.attrib['id'].split("_")[1]
		if self.name in Area.SPECIAL_CASES:
			self.name = "_".join(element.attrib['id'].split("_")[1:3])
		self.x, self.y = SVGEditor.get_translation(transform)
		self.w = float(element.attrib.get('width', 0))
		self.h = float(element.attrib.get('height', 0))
	
	
	def contains(self, x, y):
		return (x >= self.x and y >= self.y 
			and x <= self.x + self.w and y <= self.y + self.h)
	
	
	def __str__(self):
		return "<Area %s,%s %sx%s>" % (self.x, self.y, self.w, self.h)


class SVGEditor(object):
	"""
	Allows some basic edit operations by parsing SVG into dom tree and doing
	unholly mess on that.
	
	Constructed by SVGWidget.edit(), updates original SVGWidget when commit()
	is called.
	"""
	RE_PARSE_TRANSFORM = re.compile(r"([a-z]+)\(([-0-9\.,]+)\)(.*)")
	IDENTITY = ( (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0) )
	
	def __init__(self, svgw):
		if type(svgw) == str:
			self._svgw = None
			self._tree = ET.fromstring(svgw)
		elif type(svgw) == str:
			self._svgw = None
			self._tree = ET.fromstring(svgw.encode("utf-8"))
		else:
			self._svgw = svgw
			self._tree = ET.fromstring(svgw.current_svg.encode("utf-8"))
	
	
	def commit(self):
		"""
		Sends modified SVG back to original SVGWidget instance.
		
		Return self.
		"""
		self._svgw.current_svg = ET.tostring(self._tree)
		self._svgw.cache = OrderedDict()
		self._svgw.hilight({})
		
		return self
	
	
	def to_string(self):
		""" Returns modivied SVG as string """
		return ET.tostring(self._tree)
	
	
	@staticmethod
	def _deep_copy(element):
		""" Creates deep copy of XML element """
		e = element.copy()
		for ch in element:
			copy = SVGEditor._deep_copy(ch)
			e.remove(ch)
			e.append(copy)
			copy.parent = e
		return e
	
	
	def clone_element(self, id):
		"""
		Grabs element with specified ID, duplicates it and returns created
		element. Returned element may get invalidated when commit() is called.
		
		Returns None if element cannot be found
		"""
		SVGEditor.update_parents(self)
		e = SVGEditor.get_element(self, id)
		if e is not None:
			copy = SVGEditor._deep_copy(e)
			e.parent.append(copy)
			copy.parent = e.parent
			return copy
		return None
	
	
	def remove_element(self, e):
		"""
		Removes element with specified ID, or, if element is passed,
		removed that element. If  'id' is None, does nothing.
		
		Returns self.
		"""
		
		if type(e) in (str, str):
			e = SVGEditor.get_element(self, e)
		if e is not None:
			e.parent.remove(e)
		return self
	
	
	def keep(self, *ids):
		"""
		Removes all elements but ones with ID specified.
		Keeps child elements as well.
		
		Returns self.
		"""
		
		def recursive(element):
			for child in list(element):
				if (child.tag.endswith("metadata") 
						or child.tag.endswith("defs")
						or child.tag.endswith("defs")
						or child.tag.endswith("namedview")
					):
					recursive(child)
				elif child.attrib.get('id') not in ids:
					element.remove(child)
		
		
		recursive(self._tree)
		return self
	
	
	@staticmethod
	def update_parents(tree):
		"""
		Ensures that parent fields of all tree elements are are set.
		"""
		if isinstance(tree, SVGEditor):
			tree = tree._tree
		def add_parent(parent):
			for child in parent:
				child.parent = parent
				add_parent(child)
		add_parent(tree)
		if not hasattr(tree, "parent"):
			tree.parent = None
	
	
	@staticmethod
	def get_element(tree, id):
		"""
		Recursively searches throught XML until element with specified ID is found.
		
		Returns element or None, if there is not any.
		"""
		if isinstance(tree, SVGEditor):
			tree = tree._tree
		
		return SVGEditor.find_by_id(tree, id)
	
	
	@staticmethod
	def find_by_id(tree, id):
		"""
		Recursively searches throught XML until element with specified ID is found.
		
		Returns element or None, if there is not any.
		"""
		for child in tree:
			if 'id' in child.attrib:
				if child.attrib['id'] == id:
					return child
			r = SVGEditor.find_by_id(child, id)
			if r is not None:
				return r
		return None	
	
	
	@staticmethod
	def find_by_tag(tree, tag):
		"""
		Recursively searches throught XML until element with specified tag is found.
		
		Returns element or None, if there is not any.
		"""
		for child in tree:
			if child.tag.endswith(tag):
				return child
			r = SVGEditor.find_by_tag(child, tag)
			if r is not None:
				return r
		return None	
	
	
	@staticmethod
	def recolor(element, color):
		"""
		Changes background color of element.
		If element is group, descends into first element with fill set.
		
		Returns True on success, False if element cannot be recolored.
		"""
		if element.tag.endswith("path") or element.tag.endswith("rect") or element.tag.endswith("circle") or element.tag.endswith("ellipse") or element.tag.endswith("text"):
			if 'style' in element.attrib:
				style = { y[0] : y[1] for y in [ x.split(":", 1) for x in element.attrib['style'].split(";") ] }
				if 'fill' in style:
					if len(color.strip("#")) == 8:
						style['fill'] = "#%s" % (color[-6:],)
						alpha = float(int(color.strip("#")[0:2], 16)) / 255.0
						style['fill-opacity'] = style['opacity'] = str(alpha)
					else:
						style['fill'] = color
						style['fill-opacity'] = style['opacity'] = "1"
					element.attrib['style'] = ";".join([ "%s:%s" % (x, style[x]) for x in style ])
					return True
		elif element.tag.endswith("g"):
			# Group, needs to find RECT, CIRCLE or PATH, whatever comes first
			for child in element:
				SVGEditor.recolor(child, color)
			return True
		return False
	
	
	@staticmethod
	def _recolor(tree, s_from, s_to):
		""" Recursive part of recolor_strokes and recolor_background """
		for child in tree:
			if 'style' in child.attrib:
				if s_from in child.attrib['style']:
					child.attrib['style'] = child.attrib['style'].replace(s_from, s_to)
			SVGEditor._recolor(child, s_from, s_to)
	
	
	def recolor_background(self, change_from, change_to):
		"""
		Recursively travels entire DOM tree and changes every matching
		background color into specified color.
		
		Returns self.
		"""
		s_from = "fill:#%s" % (change_from,)
		s_to   = "fill:#%s" % (change_to,)
		SVGEditor._recolor(self._tree, s_from, s_to)
		return self
	
	
	def recolor_strokes(self, change_from, change_to):
		"""
		Recursively travels entire DOM tree and changes every matching
		line (stroke) color into specified color.
		
		Returns self.
		"""
		s_from = "stroke:#%s" % (change_from,)
		s_to   = "stroke:#%s" % (change_to,)
		SVGEditor._recolor(self._tree, s_from, s_to)
		return self
	
	
	@staticmethod
	def matrixmul(X, Y, *a):
		if len(a) > 0:
			return SVGEditor.matrixmul(SVGEditor.matrixmul(X, Y), a[0], *a[1:])
		return [[ sum(a*b for a,b in zip(x,y)) for y in zip(*Y) ] for x in X ]
	
	
	@staticmethod
	def scale(xml, sx, sy=None):
		"""
		Changes element scale.
		Creates or updates 'transform' attribute.
		"""
		sy = sy or sx
		SVGEditor.set_transform(xml, SVGEditor.matrixmul(
			SVGEditor.parse_transform(xml),
			[ [ sx, 0.0, 0.0 ], [ 0.0, sy, 0.0 ], [ 0.0, 0.0, 1.0 ] ],
		))
	
	
	@staticmethod
	def rotate(xml, a, x, y):
		"""
		Changes element rotation.
		Creates or updates 'transform' attribute.
		"""
		a = a * PI / 180.0
		SVGEditor.set_transform(xml, SVGEditor.matrixmul(
			SVGEditor.parse_transform(xml),
			[ [ 1.0, 0.0, x ], [ 0.0, 1.0, y ], [ 0.0, 0.0, 1.0 ] ],
			[ [ cos(a), -sin(a), 0 ], [ sin(a), cos(a), 0 ], [ 0.0, 0.0, 1.0 ] ],
			[ [ 1.0, 0.0, -x ], [ 0.0, 1.0, -y ], [ 0.0, 0.0, 1.0 ] ],
		))
	
	
	@staticmethod
	def translate(xml, x, y):
		"""
		Changes element translation.
		Creates or updates 'transform' attribute.
		"""
		SVGEditor.set_transform(xml, SVGEditor.matrixmul(
			SVGEditor.parse_transform(xml),
			[ [ 1.0, 0.0, x ], [ 0.0, 1.0, y ], [ 0.0, 0.0, 1.0 ] ],
		))
	
	
	@staticmethod
	def set_transform(xml, matrix):
		"""
		Sets element transformation matrix
		"""
		xml.attrib['transform'] = "matrix(%s,%s,%s,%s,%s,%s)" % (
			matrix[0][0], matrix[1][0], matrix[0][1],
			matrix[1][1], matrix[0][2], matrix[1][2],
		)
	
	
	@staticmethod
	def get_translation(elm_or_matrix, absolute=False):
		if isinstance(elm_or_matrix, ET.Element):
			elm = elm_or_matrix
			matrix = SVGEditor.parse_transform(elm)
			parent = elm.parent
			while parent is not None:
				matrix = SVGEditor.matrixmul(matrix, SVGEditor.parse_transform(parent))
				parent = parent.parent
		else:
			matrix = elm_or_matrix
		
		return matrix[0][2], matrix[1][2]
	
	
	@staticmethod
	def get_size(elm):
		width, height = 1, 1
		if 'width' in elm.attrib:
			width = float(elm.attrib['width'])
		if 'height' in elm.attrib:
			height = float(elm.attrib['height'])
		return width, height
	
	
	@staticmethod
	def parse_transform(xml):
		"""
		Returns element transform data in transformation matrix,
		"""
		matrix = SVGEditor.IDENTITY
		if 'x' in xml.attrib or 'y' in xml.attrib:
			x = float(xml.attrib.get('x', 0.0))
			y = float(xml.attrib.get('y', 0.0))
			# Assuming matrix is identity matrix here
			matrix = ((1.0, 0.0, x), (0.0, 1.0, y), (0.0, 0.0, 1.0))
		if 'transform' in xml.attrib:
			transform = xml.attrib['transform']
			match = SVGEditor.RE_PARSE_TRANSFORM.match(transform.strip())
			while match:
				op, values, transform = match.groups()
				if op == "translate":
					translation = [ float(x) for x in values.split(",")[0:2] ]
					while len(translation) < 2: translation.append(0.0)
					x, y = translation
					matrix = SVGEditor.matrixmul(matrix, ((1.0, 0.0, x), (0.0, 1.0, y), (0.0, 0.0, 1.0)))
				elif op == "rotate":
					rotation = [ float(x) for x in values.split(",")[0:3] ]
					while len(rotation) < 3: rotation.append(0.0)
					a, x, y = rotation
					a = a * PI / 180.0
					matrix = SVGEditor.matrixmul(
						matrix,
						[ [ 1.0, 0.0, x ], [ 0.0, 1.0, y ], [ 0.0, 0.0, 1.0 ] ],
						[ [ cos(a), -sin(a), 0 ], [ sin(a), cos(a), 0 ], [ 0.0, 0.0, 1.0 ] ],
						[ [ 1.0, 0.0, -x ], [ 0.0, 1.0, -y ], [ 0.0, 0.0, 1.0 ] ],
					)
				elif op == "scale":
					scale = tuple([ float(x) for x in values.split(",")[0:2] ])
					if len(scale) == 1:
						sx, sy = scale[0], scale[0]
					else:
						sx, sy = scale
					matrix = SVGEditor.matrixmul(matrix, ((sx, 0.0, 0.0), (0.0, sy, 0.0), (0.0, 0.0, 1.0)))
				elif op == "matrix":
					m = [ float(x) for x in values.split(",") ][0:6]
					while len(m) < 6: m.append(0.0)
					a,b,c,d,e,f = m
					matrix = SVGEditor.matrixmul(matrix,
						[ [ a, c, e], [b, d, f], [0, 0, 1] ]
					)
				
				match = SVGEditor.RE_PARSE_TRANSFORM.match(transform.strip())
		
		return matrix
	
	
	@staticmethod
	def set_text(xml, text):
		has_valid_children = False
		for child in xml:
			if child.tag.endswith("text") or child.tag.endswith("tspan"):
				has_valid_children = True
				SVGEditor.set_text(child, text)
		if not has_valid_children:
			xml.text = text
	
	
	def set_labels(self, labels):
		"""
		Replaces text on every element named LABEL_something with coresponding
		value from 'labels' dict.
		
		Returns self.
		"""
		def walk(xml):
			for child in xml:
				if 'id' in child.attrib:
					if child.attrib['id'].startswith("LABEL_"):
						id = child.attrib['id'][6:]
						if id in labels:
							SVGEditor.set_text(child, labels[id])
				walk(child)
		
		walk(self._tree)
		return self
	
	
	@staticmethod
	def add_element(parent, e, **attributes):
		"""
		Creates new element as child of specified parent or, if 1st argument
		is ET.Element, adds that element.
		
		Returns created or passed element.
		"""
		if not isinstance(e, ET.Element):
			attributes = { k : str(attributes[k]) for k in attributes }
			e = ET.Element(e, attributes)
		parent.append(e)
		return e
	
	
	@staticmethod
	def load_from_file(filename):
		tree = ET.fromstring(open(filename, "r").read())
		return SVGEditor.find_by_tag(tree, "g")
