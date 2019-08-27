# -*- coding: utf-8 -*-
"""
SC-Controller - Keyboard converter

Converts keyboard in svg, easily editable in Inkscape and supported
by python version of SCC, to json file supported by c.

Usage: keyboard-converter.py svgfile.svg jsongile.json

"""
from __future__ import unicode_literals
import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
from xml.etree import ElementTree as ET
import os, sys, re, json

RE_PARSE_TRANSFORM = re.compile(r"([a-z]+)\(([-0-9\.,]+)\)(.*)")
IDENTITY = ( (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0) )


class Button:
	def __init__(self, tree, area):
		self.contains = area.contains
		self.name = area.name
		self.label = None
		self.x, self.y = area.x, area.y
		self.w, self.h = area.w, area.h
		self.dark = area.color[2] < 0.5		# Dark button is less than 50% blue
	
	
	def __iter__(self):
		return iter(( self.x, self.y, self.w, self.h ))


class Area:
	SPECIAL_CASES = ( "LSTICK", "RSTICK", "DPAD", "ABS", "MOUSE",
		"MINUSHALF", "PLUSHALF", "KEY" )
	
	""" Basicaly just rectangle with name """
	def __init__(self, element, transform):
		self.name = element.attrib['id'].split("_")[1]
		if self.name in Area.SPECIAL_CASES:
			self.name = "_".join(element.attrib['id'].split("_")[1:3])
		self.x, self.y = get_translation(transform)
		self.w = float(element.attrib.get('width', 0))
		self.h = float(element.attrib.get('height', 0))
	
	
	def contains(self, x, y):
		return (x >= self.x and y >= self.y
			and x <= self.x + self.w and y <= self.y + self.h)
	
	
	def __str__(self):
		return "<Area %s,%s %sx%s>" % (self.x, self.y, self.w, self.h)


def color_to_float(colorstr):
	"""
	Parses color expressed as RRGGBB (as in config) and returns
	three floats of r, g, b, a (range 0 to 1)
	"""
	b, color = Gdk.Color.parse("#" + colorstr.strip("#"))
	if b:
		return color.red_float, color.green_float, color.blue_float, 1
	return 1, 0, 1, 1	# uggly purple


def parse_transform(xml):
	"""
	Returns element transform data in transformation matrix,
	"""
	matrix = IDENTITY
	if 'x' in xml.attrib or 'y' in xml.attrib:
		x = float(xml.attrib.get('x', 0.0))
		y = float(xml.attrib.get('y', 0.0))
		# Assuming matrix is identity matrix here
		matrix = ((1.0, 0.0, x), (0.0, 1.0, y), (0.0, 0.0, 1.0))
	if 'transform' in xml.attrib:
		transform = xml.attrib['transform']
		match = RE_PARSE_TRANSFORM.match(transform.strip())
		while match:
			op, values, transform = match.groups()
			if op == "translate":
				translation = [ float(x) for x in values.split(",")[0:2] ]
				while len(translation) < 2: translation.append(0.0)
				x, y = translation
				matrix = matrixmul(matrix, ((1.0, 0.0, x), (0.0, 1.0, y), (0.0, 0.0, 1.0)))
			elif op == "rotate":
				rotation = [ float(x) for x in values.split(",")[0:3] ]
				while len(rotation) < 3: rotation.append(0.0)
				a, x, y = rotation
				a = a * PI / 180.0
				matrix = matrixmul(
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
				matrix = matrixmul(matrix, ((sx, 0.0, 0.0), (0.0, sy, 0.0), (0.0, 0.0, 1.0)))
			elif op == "matrix":
				m = [ float(x) for x in values.split(",") ][0:6]
				while len(m) < 6: m.append(0.0)
				a,b,c,d,e,f = m
				matrix = matrixmul(matrix,
					[ [ a, c, e], [b, d, f], [0, 0, 1] ]
				)
			
			match = RE_PARSE_TRANSFORM.match(transform.strip())
	
	return matrix


def matrixmul(X, Y, *a):
	if len(a) > 0:
		return matrixmul(matrixmul(X, Y), a[0], *a[1:])
	return [[ sum(a*b for a,b in zip(x,y)) for y in zip(*Y) ] for x in X ]


def get_translation(elm_or_matrix, absolute=False):
	if isinstance(elm_or_matrix, ET.Element):
		elm = elm_or_matrix
		matrix = parse_transform(elm)
		parent = elm.parent
		while parent is not None:
			matrix = matrixmul(matrix, parse_transform(parent))
			parent = parent.parent
	else:
		matrix = elm_or_matrix
	
	return matrix[0][2], matrix[1][2]

def find_areas(xml, parent_transform, areas, get_colors=False, prefix="AREA_"):
	"""
	Recursively searches throught XML for anything with ID of 'AREA_SOMETHING'
	"""
	for child in xml:
		child_transform = matrixmul(
				parent_transform or IDENTITY,
				parse_transform(child))
		if str(child.attrib.get('id')).startswith(prefix):
			# log.debug("Found SVG area %s", child.attrib['id'][5:])
			a = Area(child, child_transform)
			if get_colors:
				a.color = None
				if 'style' in child.attrib:
					style = { y[0] : y[1] for y in [ x.split(":", 1) for x in child.attrib['style'].split(";") ] }
					if 'fill' in style:
						a.color = color_to_float(style['fill'])
			areas.append(a)
		else:
			find_areas(child, child_transform, areas, get_colors=get_colors, prefix=prefix)


def get_limit(tree, id):
	a = find_by_id(tree, id)
	width, height = 0, 0
	if not hasattr(a, "parent"): a.parent = None
	x, y = get_translation(a, absolute=True)
	if 'width' in a.attrib:  width = float(a.attrib['width'])
	if 'height' in a.attrib: height = float(a.attrib['height'])
	return x, y, width, height


def find_by_id(tree, id):
	"""
	Recursively searches throught XML until element with specified ID is found.
	
	Returns element or None, if there is not any.
	"""
	for child in tree:
		if 'id' in child.attrib:
			if child.attrib['id'] == id:
				return child
		r = find_by_id(child, id)
		if r is not None:
			return r
	return None	

if __name__ == "__main__":
	areas = []
	tree = ET.fromstring(open(sys.argv[1], "r").read())
	find_areas(tree, None, areas, get_colors=True)
	
	help_areas = [
		{
			"limit": get_limit(tree, x),
			"align": "right" if "right" in x.lower() else "left"
		}
		for x in ("HELP_LEFT", "HELP_RIGHT")
	]
	help_lines = ( [], [] )
	limits = { x[6:].lower(): get_limit(tree, x) for x in ( "LIMIT_LEFT", "LIMIT_RIGHT", "LIMIT_CPAD" ) }
	
	buttons = []
	for a in areas:
		buttons.append({
			"action": "button(%s)" % (a.name,),
			"dark": a.color[2] < 0.5,		# Dark button is less than 50% blue
			"pos": [ a.x, a.y ],
			"size": [ a.w, a.h ],
		})
	
	# TODO: It would be cool to use user-set font here, but cairo doesn't
	# have glyph replacement and most of default fonts (Ubuntu, Cantarell,
	# similar shit) misses pretty-much everything but letters, notably ↲
	#
	# For that reason, DejaVu Sans is hardcoded for now. On systems
	# where DejaVu Sans is not available, Cairo will automatically fallback
	# to default font.
	font = "DejaVu Sans"
	open(sys.argv[2], "w").write(json.dumps({
		"font": font,
		"buttons": buttons,
		"size": get_limit(tree, "BACKGROUND")[2:],
		"help_areas": help_areas,
		"limits": limits,
	}, indent=4, ensure_ascii=True))

