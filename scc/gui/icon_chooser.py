#!/usr/bin/env python2
"""
SC-Controller - Icon Chooser
"""

from scc.tools import _

from gi.repository import Gtk, Gdk, Gio, GdkPixbuf, GObject
from scc.gui.userdata_manager import UserDataManager
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
from scc.paths import get_menuicons_path
from scc.tools import find_icon
import os, traceback, logging, re
log = logging.getLogger("IconChooser")
RE_URL = re.compile(r"(.*)(https?://[^ ]+)(.*)")
DEFAULT_ICON_CATEGORIES = ( "items", "media", "weapons", "system" )

class IconChooser(Editor, UserDataManager):
	GLADE = "icon_chooser.glade"

	def __init__(self, app, callback):
		UserDataManager.__init__(self)
		self.app = app
		self.callback = callback
		self.setup_widgets()
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		clIcon = self.builder.get_object("clIcon")
		crIconName = self.builder.get_object("crIconName")
		btUserFolder = self.builder.get_object("btUserFolder")
		cr = CellRendererMenuIcon(32)
		clIcon.clear()
		clIcon.pack_start(cr, False)
		clIcon.pack_start(crIconName, True)
		clIcon.set_attributes(cr, icon=1, has_colors=2)
		clIcon.set_attributes(crIconName, text=0)
		btUserFolder.set_label("Add icons...")
		btUserFolder.set_uri("file://%s" % (get_menuicons_path(),))
		
		headerbar(self.builder.get_object("header"))
		self.load_menu_icons()
	
	
	def on_btUserFolder_activate_link(self, *a):
		for c in DEFAULT_ICON_CATEGORIES:
			try:
				os.makedirs(os.path.join(get_menuicons_path(), c))
			except:
				# Dir. exists
				pass
	
	
	def on_btOk_clicked(self, *a):
		icon = self.get_selected()
		self.window.destroy()
		if icon:
			self.callback(icon)
	
	
	def get_selected(self):
		"""
		Returns 'category/name' of currently selected icon.
		Returns None if nothing is selected.
		"""
		tsCategories = self.builder.get_object("tsCategories")
		tsIcons = self.builder.get_object("tsIcons")
		try:
			model, iter = tsCategories.get_selected()
			category = model.get_value(iter, 0)
			model, iter = tsIcons.get_selected()
			icon_name = model.get_value(iter, 0)
			return "%s/%s" % (category, icon_name)
		except TypeError:
			# This part may throw TypeError if either list has nothing selected.
			return None
	
	
	def on_entName_changed(self, *a): pass
	
	
	def on_tvItems_cursor_changed(self, view):
		entName = self.builder.get_object("entName")
		lblLicense = self.builder.get_object("lblLicense")
		rvLicense = self.builder.get_object("rvLicense")
		icon = self.get_selected()
		if icon:
			entName.set_text(icon)
			full_path, trash = find_icon(icon)
			if full_path:
				path, name = os.path.split(full_path)
				license = IconChooser.find_license(path, name)
				if license and "(CC 0)" in license:
					# My own icons
					license = license.replace("(CC 0)", "").strip(" ,")
			else:
				license = None
			if license:
				m = RE_URL.match(license)
				if m:
					license = "%s<a href='%s'>%s</a>%s" % (
						m.group(1), m.group(2), m.group(2), m.group(3))
				lblLicense.set_markup(_("Free-use icon created by %s" % (license,)))
			rvLicense.set_reveal_child(bool(license))
	
	
	def on_tvCategories_cursor_changed(self, view):
		model, iter = view.get_selection().get_selected()
		category = model.get_value(iter, 0)
		self.load_menu_icons(category=category)
	
	
	@staticmethod
	def color_icon_exists(model, search_name):
		for name, pb, has_colors in model:
			if has_colors and search_name == name:
				return True
		return False
	
	
	def on_menuicons_loaded(self, icons):
		tvIcons = self.builder.get_object("tvIcons")
		tvCategories = self.builder.get_object("tvCategories")
		model = tvIcons.get_model()
		model.clear()
		for f in icons:
			name = f.get_basename()
			if f.query_info(Gio.FILE_ATTRIBUTE_STANDARD_TYPE, Gio.FileQueryInfoFlags.NONE, None).get_file_type() == Gio.FileType.DIRECTORY:
				# ^^ woo, Gio is fun...
				tvCategories.get_model().append(( name, name.title() ))
			else:
				has_colors = True
				if name.startswith("."):
					# Ignore hidden files
					continue
				name = name.split(".")
				if name[-1] not in ("svg", "png"):
					# Ignore non-supported files
					continue
				name = name[0:-1]
				if name[-1] == "bw":
					has_colors = False
					name = name[0:-1]
				name = ".".join(name)
				
				if IconChooser.color_icon_exists(model, name):
					continue
				
				pb = None
				try:
					pb = GdkPixbuf.Pixbuf.new_from_file(f.get_path())
				except Exception as e:
					log.error(e)
					log.error(traceback.format_exc())
					continue
				
				model.append(( name, pb, has_colors ))
		
		trash, selected = tvCategories.get_selection().get_selected()
		if not selected:
			try:
				# Try to select 1st category, but ignore if that fails
				tvCategories.get_selection().select_path(( 0, ))
				self.on_tvCategories_cursor_changed(tvCategories)
			except: pass
	
	
	@staticmethod
	def find_license(path, name):
		""" Parses LICENSE file, if any, and returns license for give file """
		licensefile = os.path.join(path, "LICENCES")
		if not os.path.exists(licensefile):
			return None
		for line in file(licensefile, "r").readlines():
			if line.startswith(name):
				if "-" in line:
					return line.split("-")[-1].strip("\t\r\n ")
		return None


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
