#!/usr/bin/env python2
"""
SC-Controller - App

Main application window
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gio, GLib
from scc.gui.controller_button import ControllerButton
from scc.gui.controller_pad import ControllerPad
from scc.gui.action_editor import ActionEditor
from scc.gui.svg_widget import SVGWidget
from scc.constants import SCButtons
from scc.actions import InvalidActionParser
from scc.profile import Profile

import os, sys, time, logging
log = logging.getLogger("App")


class App(Gtk.Application):
	"""
	Main application / window.
	"""
	
	IMAGE = "background.svg"
	TRIGGERS = [ "LT", "RT" ]
	PADS	= [ "LPAD", "STICK", "RPAD" ]
	BUTTONS = [ b for b in SCButtons if b.name not in TRIGGERS + PADS + [ x + "TOUCH" for x in PADS ] ]
	
	def __init__(self, gladepath="/usr/share/scc",
						iconpath="/usr/share/scc/icons"):
		Gtk.Application.__init__(self,
				application_id="me.kozec.scc",
				flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
		# Setup Gtk.Application
		self.setup_commandline()
		# Set variables
		self.gladepath = gladepath
		self.iconpath = iconpath
		self.builder = None
		self.background = None
		self.current = Profile(InvalidActionParser())
		self.buttons = {}
		self.pads = {}
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.gladepath, "app.glade"))
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window")
		self.add_window(self.window)
		self.window.set_title(_("SC Controller"))
		self.window.set_wmclass("SC Controller", "SC Controller")
		
		for b in App.BUTTONS:
			self.buttons[b.name] = ControllerButton(self, b, self.builder.get_object("bt" + b.name))
		for b in App.TRIGGERS:
			self.buttons[b] = ControllerButton(self, b, self.builder.get_object("bt" + b))
		for p in App.PADS:
			self.buttons[p] = ControllerPad(self, p, self.builder.get_object("bt" + p))
		
		
		vbc = self.builder.get_object("vbC")
		main_area = self.builder.get_object("mainArea")
		vbc.get_parent().remove(vbc)
		vbc.connect('size-allocate', self.on_vbc_allocated)
		self.background = SVGWidget(self, os.path.join(self.iconpath, self.IMAGE))
		self.background.connect('hover', self.on_background_area_hover)
		self.background.connect('leave', self.on_background_area_hover, None)
		self.background.connect('click', self.on_background_area_click)
		main_area.put(self.background, 0, 0)
		main_area.put(vbc, 0, 0) # (self.IMAGE_SIZE[0] / 2) - 90, self.IMAGE_SIZE[1] - 100)
	
	
	def hilight(self, button):
		""" Hilights specified button on background image """
		self.background.hilight(button)
	
	
	def hint(self, button):
		""" As hilight, but marks GTK Button as well """
		for b in self.buttons.values():
			b.widget.set_state(Gtk.StateType.NORMAL)
		if button in self.buttons:
			self.buttons[button].widget.set_state(Gtk.StateType.ACTIVE)
		
		self.hilight(button)
	
	
	def show_editor(self, id):
		if id in SCButtons:
			ae = ActionEditor(self)
			ae.set_title(_("Edit action for %s Button") % (id.name,))
			ae.set_button(id)
			ae.show(self.window)
	
	
	def set_action(self, id, action):
		if what in SCButtons:
			self.button[what].update()
	
	
	def on_background_area_hover(self, trash, area):
		self.hint(area)
	
	
	def on_background_area_click(self, trash, area):
		if area in [ x.name for x in App.BUTTONS ]:
			self.hint(None)
			self.show_editor(getattr(SCButtons, area))
	
	
	def on_vbc_allocated(self, vbc, allocation):
		"""
		Called when size of 'Button C' is changed. Centers button
		on background image
		"""
		main_area = self.builder.get_object("mainArea")
		x = (main_area.get_allocation().width - allocation.width) / 2
		y = main_area.get_allocation().height - allocation.height - 50
		main_area.move(vbc, x, y)
	
	
	def on_ebImage_motion_notify_event(self, box, event):
		self.background.on_mouse_moved(event.x, event.y)
		
	
	def do_startup(self, *a):
		Gtk.Application.do_startup(self, *a)
		self.current.load("xbox.json")
		self.setup_widgets()
	
	
	def do_local_options(self, trash, lo):
		set_logging_level(lo.contains("verbose"), lo.contains("debug") )
		return -1
	
	
	def do_command_line(self, cl):
		Gtk.Application.do_command_line(self, cl)
		self.activate()
		return 0
	
	
	def do_activate(self, *a):
		self.builder.get_object("window").show()
	
	
	def setup_commandline(self):
		def aso(long_name, short_name, description,
				arg=GLib.OptionArg.NONE,
				flags=GLib.OptionFlags.IN_MAIN):
			""" add_simple_option, adds program argument in simple way """
			o = GLib.OptionEntry()
			o.long_name = long_name
			o.short_name = short_name
			o.description = description
			o.flags = flags
			o.arg = arg
			self.add_main_option_entries([o])
		
		self.connect('handle-local-options', self.do_local_options)
		
		aso("verbose",	b"v", "Be verbose")
		aso("debug",	b"d", "Be more verbose (debug mode)")
