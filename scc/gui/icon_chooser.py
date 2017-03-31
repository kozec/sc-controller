#!/usr/bin/env python2
"""
SC-Controller - Icon Chooser
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gdk, GdkPixbuf, GObject
from scc.gui.userdata_manager import UserDataManager
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
import os, traceback, logging
log = logging.getLogger("IconChooser")

class IconChooser(Editor, UserDataManager):
	GLADE = "icon_chooser.glade"

	def __init__(self, app, callback):
		UserDataManager.__init__(self)
		self.app = app
		self.setup_widgets()
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		clIcon = self.builder.get_object("clIcon")
		crIconName = self.builder.get_object("crIconName")
		cr = CellRendererMenuIcon(32)
		clIcon.clear()
		clIcon.pack_start(cr, False)
		clIcon.pack_start(crIconName, True)
		clIcon.set_attributes(cr, icon=1, has_colors=2)
		clIcon.set_attributes(crIconName, text=0)
		
		headerbar(self.builder.get_object("header"))
		self.load_menu_icons()
	
	
	def on_btSave_clicked(self, *a): pass
	def on_tvItems_cursor_changed(self, *a): pass
	def on_entName_changed(self, *a): pass
	
	
	def on_menuicons_loaded(self, icons):
		tvIcons = self.builder.get_object("tvIcons")
		model = tvIcons.get_model()
		for f in icons:
			pb = None
			try:
				pb = GdkPixbuf.Pixbuf.new_from_file(f.get_path())
			except Exception, e:
				log.error(e)
				log.error(traceback.format_exc())
				
			name = os.path.split(f.get_path())[-1].split(".")
			has_colors = True
			if name[-1] == "png":
				name = name[0:-1]
			if name[-1] == "bw":
				has_colors = False
				name = name[0:-1]
			
			model.append(( ".".join(name), pb, has_colors ))


class CellRendererMenuIcon(Gtk.CellRenderer):
	icon = GObject.property(type=GdkPixbuf.Pixbuf)
	has_colors = GObject.property(type=bool, default=False)
	
	def __init__(self, size):
		Gtk.CellRenderer.__init__(self)
		self.size = size
	
	def do_get_size(self, *a):
		return 0, 0, self.size, self.size
	
	
	def do_render(self, cr, treeview, background_area, cell_area, flags):
		context = Gtk.Widget.get_style_context(treeview)
		Gtk.render_background(context, cr,
				cell_area.x, cell_area.y,
				cell_area.x + cell_area.width,
				cell_area.y + cell_area.height
		)
		
		scaled = self.icon.scale_simple(
				self.size, self.size,
				GdkPixbuf.InterpType.BILINEAR
		)
		surf = Gdk.cairo_surface_create_from_pixbuf(scaled, 1)
		if self.has_colors:
			cr.set_source_surface(surf, cell_area.x, cell_area.y)
			cr.rectangle(cell_area.x, cell_area.y, self.size, self.size)
		else:
			color_flags = Gtk.StateFlags.NORMAL
			if (flags & Gtk.CellRendererState.SELECTED) != 0:
				color_flags = Gtk.StateFlags.SELECTED
			Gdk.cairo_set_source_rgba(cr, context.get_color(color_flags))
			cr.mask_surface(surf, cell_area.x, cell_area.y)
		cr.fill()
