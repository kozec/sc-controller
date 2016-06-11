#!/usr/bin/env python2
"""
SC-Controller - Background

Changes SVG on the fly and uptates that magnificent image on background with it.
Also supports clicking on areas defined in SVG image.
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GObject, Rsvg
from xml.etree import ElementTree as ET
import os, sys, logging

log = logging.getLogger("Background")

class SVGWidget(Gtk.EventBox):
	FILENAME = "background.svg"
	
	__gsignals__ = {
			# Raised when mouse is over defined area
			b"hover"	: (GObject.SIGNAL_RUN_FIRST, None, (object,)),
			# Raised when mouse leaves all defined areas
			b"leave"	: (GObject.SIGNAL_RUN_FIRST, None, ()),
			# Raised user clicks on defined area
			b"click"	: (GObject.SIGNAL_RUN_FIRST, None, (object,)),
	}
	
	
	def __init__(self, app, filename):
		Gtk.EventBox.__init__(self)
		self.app = app
		self.cache = {}
		self.areas = []
		
		self.connect("motion-notify-event", self.on_mouse_moved)
		self.connect("button-press-event", self.on_mouse_click)
		self.set_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
		
		self.svg_source = open(filename, "r").read()
		self.image_width = 1
		self.image = Gtk.Image()
		self.parse_image()
		self.hilight({})
		self.add(self.image)
		self.show_all()
	
	
	def parse_image(self):
		"""
		Goes trought SVG image and searches for all rects named
		'AREA_SOMETHING' and generates area list from it.
		This area list is later used to determine over which button is mouse
		hovering.
		"""
		tree = ET.fromstring(self.svg_source)
		find_areas(tree, (0, 0), self.areas)
		self.image_width = float(tree.attrib["width"])
	
	
	def set_labels(self, labels):
		tree = ET.fromstring(self.svg_source)
		
		def set_text(xml, text):
			has_valid_children = False
			for child in xml:
				if child.tag.endswith("text") or child.tag.endswith("tspan"):
					has_valid_children = True
					set_text(child, text)
			if not has_valid_children:
				xml.text = text
		
		
		def walk(xml):
			for child in xml:
				if 'id' in child.attrib:
					if child.attrib['id'].startswith("LABEL_"):
						id = child.attrib['id'][6:]
						if id in labels:
							set_text(child, labels[id])
				walk(child)
		
		walk(tree)
		self.svg_source = ET.tostring(tree)
		
		self.cache = {}
		self.hilight({})
	
	
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
	
	
	def get_element(self, id):
		tree = ET.fromstring(self.svg_source)
		tree.parent = None
		el = find_by_id(tree, id)
		if el is not None:
			def add_parent(parent):
				for child in parent:
					child.parent = parent
					add_parent(child)
			add_parent(tree)
			return el
		return None
	
	
	def get_rect_area(self, xml, x=0, y=0):
		"""
		Returns x, y, width and height of rect element relative to document root.
		"""
		width, height = 0, 0
		if 'x' in xml.attrib: x += float(xml.attrib['x'])
		if 'y' in xml.attrib: y += float(xml.attrib['y'])
		if 'width' in xml.attrib:  width = float(xml.attrib['width'])
		if 'height' in xml.attrib: height = float(xml.attrib['height'])
		
		if xml.parent is not None:
			px, py, trash, trash = self.get_rect_area(xml.parent)
			x += px
			y += py
		
		return x, y, width, height
	
	
	def hilight(self, buttons):
		""" Hilights specified button, if same ID is found in svg """
		cache_id = "|".join([ "%s:%s" % (x, buttons[x]) for x in buttons ])
		if not cache_id in self.cache:
			# Ok, this is close to madness, but probably better than drawing
			# 200 images by hand;
			# 1st, parse source as XML
			tree = ET.fromstring(self.svg_source)
			# 2nd, change colors of some elements
			for button in buttons:
				el = find_by_id(tree, button)
				if el is not None:
					recolor(el, buttons[button])
				
			# 3rd, turn it back into XML string......
			xml = ET.tostring(tree)
			
			# ... and now, parse that as XML again......
			svg = Rsvg.Handle.new_from_data(xml.encode("utf-8"))
			self.cache[cache_id] = svg.get_pixbuf()
		
		self.image.set_from_pixbuf(self.cache[cache_id])
	
	
	def get_pixbuf(self):
		""" Returns currently displayed pixbuf """
		return self.image.get_pixbuf()


class Area:
	SPECIAL_CASES = ( "LSTICK", "RSTICK", "DPAD", "ABS", "MOUSE",
		"MINUSHALF", "PLUSHALF", "KEY" )
	
	""" Basicaly just rectangle with name """
	def __init__(self, translation, element):
		self.name = element.attrib['id'].split("_")[1]
		if self.name in Area.SPECIAL_CASES:
			self.name = "_".join(element.attrib['id'].split("_")[1:3])
		self.x = float(element.attrib['x']) + translation[0]
		self.y = float(element.attrib['y']) + translation[1]
		self.w = float(element.attrib['width'])
		self.h = float(element.attrib['height'])
	
	
	def contains(self, x, y):
		return (x >= self.x and y >= self.y 
			and x <= self.x + self.w and y <= self.y + self.h)
	
	
	def __str__(self):
		return "<Area %s,%s %sx%s>" % (self.x, self.y, self.w, self.h)


def find_areas(xml, translation, areas):
	"""
	Recursively searches throught XML for anything with ID of 'AREA_SOMETHING'
	"""
	# print translation, xml
	for child in xml:
		if 'id' in child.attrib:
			if child.attrib['id'].startswith("AREA_"):
				# log.debug("Found SVG area %s", child.attrib['id'][5:])
				areas.append(Area(translation, child))
				continue
		if 'transform' in child.attrib:
			if child.attrib['transform'].startswith("translate"):
				# Only transform supported and, luckily, only transform used
				value = child.attrib['transform'].split("(")[-1].strip(")").split(",")
				child_translation = (
					translation[0] + float(value[0]),
					translation[1] + float(value[1])
				)
				find_areas(child, child_translation, areas)
				continue
		find_areas(child, translation, areas)


def find_by_id(xml, id):
	"""
	Recursively searches throught XML until element with specified ID is found.
	
	Returns element or None, if there is not any.
	"""
	for child in xml:
		if 'id' in child.attrib:
			if child.attrib['id'] == id:
				return child
		r = find_by_id(child, id)
		if r is not None:
			return r
	return None


def recolor(element, color):
	"""
	Changes background color of element.
	If element is group, descends into first element with fill set.
	
	Returns True on success, False if element cannot be recolored.
	"""
	if element.tag.endswith("path") or element.tag.endswith("rect") or element.tag.endswith("circle") or element.tag.endswith("text"):
		if 'style' in element.attrib:
			style = { y[0] : y[1] for y in [ x.split(":", 1) for x in element.attrib['style'].split(";") ] }
			if 'fill' in style:
				style['fill'] = color
				if 'opacity' in style:
					style['opacity'] = "1"
				element.attrib['style'] = ";".join([ "%s:%s" % (x, style[x]) for x in style ])
				return True
	elif element.tag.endswith("g"):
		# Group, needs to find RECT, CIRCLE or PATH, whatever comes first
		for child in element:
			if recolor(child, color):
				return True
	return False

