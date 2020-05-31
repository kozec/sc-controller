#!/usr/bin/env python2
# Used to generate some icons
# Requires inkscape and imagemagick pacages

import os, subprocess, colorsys
from xml.etree import ElementTree as ET

ICODIR = "./share/images/"						# Directory with icons
CICONS = "./share/images/controller-icons/"		# Directory controller-icons
RECOLORS = {		# Defines set of hue shifts for controller-icons
	# "0" : 0.0,	# Green - original
	"1" : 0.3,		# Blue
	"2" : 0.7,		# Red
	"3" : 0.9,		# Yellow
	"4" : 0.2,		# Cyan
	"5" : 0.8,		# Orange
	"6" : 0.5,		# Purple
}


# Generate svg state icons
for size in (24, 256):
	for state in ('alive', 'dead', 'error', 'unknown'):
		print "scc-statusicon-%s.png" % (state,)
		subprocess.call([
			"inkscape",
			"%s/scc-statusicon-%s.svg" % (ICODIR, state),
			"--export-area-page",
			"--export-png=%s/%sx%s/status/scc-%s.png" % (ICODIR, size, size, state),
			"--export-width=%s" % (size,),
			"--export-height=%s" % (size,) ])


def html_to_rgb(html):
	""" Converts #rrggbbaa or #rrggbb to r, g, b,a in (0,1) ranges """
	html = html.strip("#")
	if len(html) == 6:
		html = html + "ff"
	elif html == "none":
		return 0, 0, 0, 0
	elif len(html) != 8:
		raise ValueError("Needs RRGGBB(AA) format, got '%s'" % (html, ))
	return tuple(( float(int(html[i:i+2],16)) / 255.0 for i in xrange(0, len(html), 2) ))


def rgb_to_html(r,g,b):
	""" Convets rgb back to html color code """
	return "#" + "".join(( "%02x" % int(x * 255) for x in (r,g,b) ))


def recolor(tree, add):
	""" Recursive part of recolor_strokes and recolor_background """
	if 'id' in tree.attrib and "overlay" in tree.attrib['id']:
		return
	for child in tree:
		if 'style' in child.attrib:
			styles = { a : b
				for (a, b) in (
					x.split(":", 1)
					for x in child.attrib['style'].split(';')
					if ":" in x
				)}
			if "fill" in styles or "stroke" in styles:
				for key in ("fill", "stroke"):
					if key in styles:
						# Convert color to HSV
						r,g,b,a = html_to_rgb(styles[key])
						h,s,v = colorsys.rgb_to_hsv(r,g,b)
						# Shift hue
						h += add
						while h > 1.0 : h -= 1.0
						# Convert it back
						r,g,b = colorsys.hsv_to_rgb(h,s,v)
						# Store
						styles[key] = rgb_to_html(r,g,b)
				child.attrib["style"] = ";".join(( ":".join((x,styles[x])) for x in styles ))
		recolor(child, add)

# Generate different colors for controller icons
ET.register_namespace("","http://www.w3.org/2000/svg")
for tp in ("sc", "scbt", "fake", "ds4", "dinput"):
	# Read svg and parse it
	data = file("%s/%s-0.svg" % (CICONS, tp), "r").read()
	# Create recolored images
	for key in RECOLORS:
		tree = ET.fromstring(data)
		# Walk recursively and recolor everything that has color
		recolor(tree, RECOLORS[key])
		
		out = "%s/%s-%s.svg" % (CICONS, tp, key)
		file(out, "w").write(ET.tostring(tree))
		print out
