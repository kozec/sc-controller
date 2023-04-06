#!/usr/bin/env python3
from scc.tools import _

from scc.actions import Action, DPadAction, XYAction, MouseAction
from scc.modifiers import ModeModifier, DoubleclickModifier
from scc.special_actions import MenuAction
from scc.parser import TalkingActionParser
from scc.constants import SCButtons
from scc.profile import Profile
from scc.tools import nameof
from scc.uinput import Rels
from scc.gui.svg_widget import SVGEditor
from scc.lib import IntEnum
import os


class Align(IntEnum):
	TOP  =    1 << 0
	BOTTOM =  1 << 1
	LEFT =    1 << 2
	RIGHT =   1 << 3


def find_image(name):
	# TODO: This
	filename = "images/" + name + ".svg"
	if os.path.exists(filename):
		return filename
	return None


class Line(object):
	
	def __init__(self, icon, text):
		self.icons = [ icon ]
		self.text = text
	
	
	def get_size(self, gen):
		# TODO: This
		return gen.char_width * len(self.text), gen.line_height
	
	
	def add_icon(self, icon):
		self.icons.append(icon)
		return self
	
	
	def to_string(self):
		return "%-10s: %s" % (",".join([ x for x in self.icons if x ]), self.text)


class LineCollection(object):
	""" Allows calling add_icon on multiple lines at once """
	
	def __init__(self, *lines):
		self.lines = lines
	
	
	def add_icon(self, icon):
		for line in self.lines:
			line.add_icon(icon)
		return self


class Box(object):
	PADDING = 5
	SPACING = 2
	MIN_WIDTH = 100
	MIN_HEIGHT = 50
	
	def __init__(self, anchor_x, anchor_y, align, name,
			min_width = MIN_WIDTH, min_height = MIN_HEIGHT):
		self.name = name
		self.lines = []
		self.anchor = anchor_x, anchor_y
		self.align = align
		self.min_height = min_height
		self.x, self.y = 0, 0
		self.min_width = min_width
		self.min_height = min_height
	
	
	def to_string(self):
		return "--- %s ---\n%s\n" % (
			self.name,
			"\n".join([ x.to_string() for x in self.lines ])
		)
	
	
	def add(self, icon, context, action):
		if not action: return LineCollection()
		if isinstance(action, ModeModifier):
			lines = [ self.add(icon, context, action.default) ]
			for x in action.mods:
				lines.append( self.add(nameof(x), context, action.mods[x])
						.add_icon(icon) )
			return LineCollection(*lines)
		elif isinstance(action, DoubleclickModifier):
			lines = []
			if action.normalaction:
				lines.append( self.add(icon, context, action.normalaction) )
			if action.action:
				lines.append( self.add("DOUBLECLICK", context, action.action)
						.add_icon(icon) )
			if action.holdaction:
				lines.append( self.add("HOLD", context, action.holdaction)
						.add_icon(icon) )
			return LineCollection(*lines)
		
		action = action.strip()
		if isinstance(action, MenuAction):
			if self.name == "bcs" and action.menu_id == "Default.menu":
				# Special case, this action is expected in every profile,
				# so there is no need to draw it here
				return LineCollection()
		elif isinstance(action, DPadAction):
			return LineCollection(
				self.add("DPAD_UP",    Action.AC_BUTTON, action.actions[0]),
				self.add("DPAD_DOWN",  Action.AC_BUTTON, action.actions[1]),
				self.add("DPAD_LEFT",  Action.AC_BUTTON, action.actions[2]),
				self.add("DPAD_RIGHT", Action.AC_BUTTON, action.actions[3])
			)
		elif isinstance(action, XYAction):
			if isinstance(action.x, MouseAction) and isinstance(action.y, MouseAction):
				if action.x.get_axis() in (Rels.REL_HWHEEL, Rels.REL_WHEEL):
					# Special case, pad bound to wheel
					line = Line(icon, _("Mouse Wheel"))
					self.lines.append(line)
					return line	
			return LineCollection(
				self.add("AXISX",  Action.AC_BUTTON, action.x),
				self.add("AXISY",  Action.AC_BUTTON, action.y)
			)
		line = Line(icon, action.describe(context))
		self.lines.append(line)
		return line
	
	
	def calculate(self, gen):
		self.width, self.height = self.min_width, 2 * self.PADDING
		self.icount = 0
		for line in self.lines:
			lw, lh = line.get_size(gen)
			self.width, self.height = max(self.width, lw), self.height + lh + self.SPACING
			self.icount = max(self.icount, len(line.icons))
		self.width += 2 * self.PADDING + self.icount * (gen.line_height + self.SPACING)
		self.height = max(self.height, self.min_height)
		
		anchor_x, anchor_y = self.anchor
		if (self.align & Align.TOP) != 0:
			self.y = anchor_y
		elif (self.align & Align.BOTTOM) != 0:
			self.y = gen.full_height - self.height - anchor_y
		else:
			self.y = (gen.full_height - self.height) / 2
		
		if (self.align & Align.LEFT) != 0:
			self.x = anchor_x
		elif (self.align & Align.RIGHT) != 0:
			self.x = gen.full_width - self.width - anchor_x
		else:
			self.x = (gen.full_width - self.width) / 2
	
	
	def place(self, gen, root):
		e = SVGEditor.add_element(root, "rect",
			style = "opacity:1;fill-opacity:0.0;stroke-width:2.0;",
			fill="#000000",
			stroke="#06a400",
			id = "box_%s" % (self.name,),
			width = self.width, height = self.height,
			x = self.x, y = self.y,
		)
		
		y = self.y + self.PADDING
		for line in self.lines:
			h = gen.line_height
			x = self.x + self.PADDING
			for icon in line.icons:
				image = find_image(icon)
				if image:
					SVGEditor.add_element(root, "image", x = x, y = y,
						style = "filter:url(#filterInvert)",
						width = h, height = h, href = image)
				x += h + self.SPACING
			x = self.x + self.PADDING + self.icount * (h + self.SPACING)
			y += h
			txt = SVGEditor.add_element(root, "text", x = x, y = y,
				style = gen.label_template.attrib['style']
			)
			SVGEditor.set_text(txt, line.text)
			y += self.SPACING
	
	
	def place_marker(self, gen, root):
		x1, y1 = self.x, self.y
		x2, y2 = x1 + self.width, y1 + self.height
		if self.align & (Align.LEFT | Align.RIGHT) == 0:
			edges = [ [ x2, y2 ], [ x1, y2 ] ]
		elif self.align & Align.BOTTOM == Align.BOTTOM:
			if self.align & Align.LEFT != 0:
				edges = [ [ x2, y2 ], [ x1, y1 ] ]
			elif self.align & Align.RIGHT != 0:
				edges = [ [ x2, y1 ], [ x1, y2 ] ]
		elif self.align & Align.TOP == Align.TOP:
			if self.align & Align.LEFT != 0:
				edges = [ [ x2, y1 ], [ x2, y2 ] ]
			elif self.align & Align.RIGHT != 0:
				edges = [ [ x1, y1 ], [ x1, y2 ] ]
		else:
			if self.align & Align.LEFT != 0:
				edges = [ [ x2, y1 ], [ x2, y2 ] ]
			elif self.align & Align.RIGHT != 0:
				edges = [ [ x1, y1 ], [ x2, y2 ] ]
		
		targets = SVGEditor.get_element(root, "markers_%s" % (self.name,))
		if targets is None:
			return
		i = 0
		for target in targets:
			tx, ty = float(target.attrib["cx"]), float(target.attrib["cy"])
			try:
				edges[i] += [ tx, ty ]
				i += 1
			except IndexError:
				break
		edges = [ i for i in edges if len(i) == 4]
		
		for x1, y1, x2, y2 in edges:
			e = SVGEditor.add_element(root, "line",
				style = "opacity:1;stroke:#06a400;stroke-width:0.5;",
				# id = "box_%s_line0" % (self.name,),
				x1 = x1, y1 = y1, x2 = x2, y2 = y2
			)



class Generator(object):
	PADDING = 10
	
	def __init__(self):
		svg = SVGEditor(file("images/binding-display.svg").read())
		background = SVGEditor.get_element(svg, "background")
		self.label_template = SVGEditor.get_element(svg, "label_template")
		self.line_height = int(float(self.label_template.attrib.get("height") or 8))
		self.char_width = int(float(self.label_template.attrib.get("width") or 8))
		self.full_width = int(float(background.attrib.get("width") or 800))
		self.full_height = int(float(background.attrib.get("height") or 800))
		
		profile = Profile(TalkingActionParser()).load("test.sccprofile")
		boxes = []
		
		
		box_bcs = Box(0, self.PADDING, Align.TOP, "bcs")
		box_bcs.add("BACK", Action.AC_BUTTON, profile.buttons.get(SCButtons.BACK))
		box_bcs.add("C", Action.AC_BUTTON, profile.buttons.get(SCButtons.C))
		box_bcs.add("START", Action.AC_BUTTON, profile.buttons.get(SCButtons.START))
		boxes.append(box_bcs)
		
		
		box_left = Box(self.PADDING, self.PADDING, Align.LEFT | Align.TOP, "left",
			min_height = self.full_height * 0.5,
			min_width = self.full_width * 0.2)
		box_left.add("LEFT", Action.AC_TRIGGER, profile.triggers.get(profile.LEFT))
		box_left.add("LB", Action.AC_BUTTON, profile.buttons.get(SCButtons.LB))
		box_left.add("LGRIP", Action.AC_BUTTON, profile.buttons.get(SCButtons.LGRIP))
		box_left.add("LPAD", Action.AC_PAD, profile.pads.get(profile.LEFT))
		boxes.append(box_left)
		
		
		box_right = Box(self.PADDING, self.PADDING, Align.RIGHT | Align.TOP, "right",
			min_height = self.full_height * 0.5,
			min_width = self.full_width * 0.2)
		box_right.add("RIGHT", Action.AC_TRIGGER, profile.triggers.get(profile.RIGHT))
		box_right.add("RB", Action.AC_BUTTON, profile.buttons.get(SCButtons.RB))
		box_right.add("RGRIP", Action.AC_BUTTON, profile.buttons.get(SCButtons.RGRIP))
		box_right.add("RPAD", Action.AC_PAD, profile.pads.get(profile.RIGHT))
		boxes.append(box_right)
		
		
		box_abxy = Box(4 * self.PADDING, self.PADDING, Align.RIGHT | Align.BOTTOM, "abxy")
		box_abxy.add("A", Action.AC_BUTTON, profile.buttons.get(SCButtons.A))
		box_abxy.add("B", Action.AC_BUTTON, profile.buttons.get(SCButtons.B))
		box_abxy.add("X", Action.AC_BUTTON, profile.buttons.get(SCButtons.X))
		box_abxy.add("Y", Action.AC_BUTTON, profile.buttons.get(SCButtons.Y))
		boxes.append(box_abxy)
		
		
		box_stick = Box(4 * self.PADDING, self.PADDING, Align.LEFT | Align.BOTTOM, "stick")
		box_stick.add("STICK", Action.AC_STICK, profile.stick)
		boxes.append(box_stick)
		
		
		w = int(float(background.attrib.get("width") or 800))
		h = int(float(background.attrib.get("height") or 800))
		
		root = SVGEditor.get_element(svg, "root")
		for b in boxes:
			b.calculate(self)
		
		# Set ABXY and Stick size & position
		box_abxy.height = box_stick.height = self.full_height * 0.25
		box_abxy.width = box_stick.width = self.full_width * 0.3
		box_abxy.y = self.full_height - self.PADDING - box_abxy.height
		box_stick.y = self.full_height - self.PADDING - box_stick.height
		box_abxy.x = self.full_width - self.PADDING - box_abxy.width
		
		self.equal_width(box_left, box_right)
		self.equal_height(box_left, box_right)
		
		for b in boxes:
			b.place_marker(self, root)
		for b in boxes:
			b.place(self, root)
		
		file("out.svg", "w").write(svg.to_string())
	
	
	
	def equal_width(self, *boxes):
		""" Sets width of all passed boxes to width of widest box """
		width = 0
		for b in boxes: width = max(width, b.width)
		for b in boxes:
			b.width = width
			if b.align & Align.RIGHT:
				b.x = self.full_width - b.width - self.PADDING
	
	
	def equal_height(self, *boxes):
		""" Sets height of all passed boxes to height of tallest box """
		height = 0
		for b in boxes: height = max(height, b.height)
		for b in boxes:
			b.height = height


Generator()
