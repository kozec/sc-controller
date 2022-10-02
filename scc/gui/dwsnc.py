"""
DWSNC - Doing Weird Things in Name of Compatibility

This module, when imported, applies various fixes and monkey-patching to allow
application to run with older versions of GLib and/or GTK.
"""
from __future__ import unicode_literals
from gi.repository import Gtk, GObject
import os


def fix_label_missing_set_XYalign_methods():
	"""
	Fix Gtk.Label missing set_xalign and set_yalign methods with older
	versions of Gtk.
	
	Prevents crashing, but alings are ignored.
	"""
	Gtk.Label.set_xalign = Gtk.Label.set_yalign = lambda *a : None

def child_get_property(parent, child, propname):
	"""
	Wrapper for child_get_property, which pygobject doesn't properly
	introspect
	"""
	value = GObject.Value()
	value.init(GObject.TYPE_INT)
	parent.child_get_property(child, propname, value)
	return value.get_int()


def headerbar(bar):
	"""
	Moves all buttons from left to right (and vice versa) if user's desktop
	environment is identified as Unity.
	
	Removes 'icon' button otherwise
	"""
	bar.set_decoration_layout(":minimize,close")
	pass	# Not outside of Unity

IS_UNITY = False
IS_GNOME = False
IS_KDE = False

if "XDG_CURRENT_DESKTOP" in os.environ:
	if "GNOME" in os.environ["XDG_CURRENT_DESKTOP"].split(":"):
		IS_GNOME = True
	
	if "KDE" in os.environ["XDG_CURRENT_DESKTOP"].split(":"):
		IS_KDE = True
	
	if "Unity" in os.environ["XDG_CURRENT_DESKTOP"].split(":"):
		# User runs Unity
		IS_UNITY = True
		
		def _headerbar(bar):
			children = [] + bar.get_children()
			pack_start = []
			pack_end = []
			for c in children:
				if child_get_property(bar, c, 'pack-type') == Gtk.PackType.END:
					bar.remove(c)
					pack_start.append(c)
				else:
					bar.remove(c)
					pack_end.append(c)
			if len(pack_end) > 1:
				c,  pack_end = pack_end[0], pack_end[1:]
				pack_end.append(c)
			if (Gtk.get_major_version(), Gtk.get_minor_version()) > (3, 10):
				# Old ubuntu has this in order, new Ubuntu has it reversed
				pack_end = reversed(pack_end)
			for c in pack_start: bar.pack_start(c)
			for c in pack_end: bar.pack_end(c)
		headerbar = _headerbar

if not hasattr(Gtk.Label, "set_xalign"):
	# GTK is old enough
	fix_label_missing_set_XYalign_methods()

