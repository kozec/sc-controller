#!/usr/bin/env python2
"""
Python wrapper for some X-related stuff.

Copyright (C) 2017 Kozec

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as published by
the Free Software Foundation

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

from ctypes import CDLL, POINTER, c_void_p, Structure, byref, cast
from ctypes import c_long, c_ulong, c_int, c_uint, c_short, c_char_p
from ctypes import c_ushort, c_ubyte, c_char_p, c_bool


def _load_lib(*names):
	"""
	Tries multiple alternative names to load .so library.
	"""
	for l in names:
		try:
			return CDLL(l)
		except OSError:
			pass
	raise OSError("Failed to load %s, library not found" % (names[0],))


libXFixes = _load_lib('libXfixes.so', 'libXfixes.so.3')
libX11 = _load_lib('libX11.so', 'libX11.so.6')
libXext = _load_lib('libXext.so', 'libXext.so.6')


# Types
XID = c_ulong
Pixmap = XID
Colormap = XID
Atom = c_ulong
XserverRegion = c_ulong
GC = c_void_p
Display = c_void_p

# Structures
class XRectangle(Structure):
	_fields_ = [
		('x', c_short),
		('y', c_short),
		('width', c_ushort),
		('height', c_ushort),
	]

class XClassHint(Structure):
	_fields_ = [
		('res_name', c_char_p),
		('res_class', c_char_p),
	]

class XkbStateRec(Structure):
	_fields_ = [
		('group', c_ubyte),
		('locked_group', c_ubyte),
		('base_group', c_ushort),
		('latched_group', c_ushort),
		('mods', c_ubyte),
		('base_mods', c_ubyte),
		('latched_mods', c_ubyte),
		('locked_mods', c_ubyte),
		('compat_state', c_ubyte),
		('grab_mods', c_ubyte),
		('compat_grab_mods', c_ubyte),
		('lookup_mods', c_ubyte),
		('compat_lookup_mods', c_ubyte),
		('ptr_buttons', c_ushort),
	]

class XWindowAttributes(Structure):
	_fields_ = [
		('x', c_int),
		('y', c_int),
		('width', c_int),
		('height', c_int),
		('depth', c_int),
		('visual', c_void_p),
		('root', XID),
		('i_class', c_int),
		('bit_gravity', c_int),
		('win_gravity', c_int),
		('backing_store', c_int),
		('backing_planes', c_ulong),
		('backing_pixel', c_ulong),
		('save_under', c_bool),
		('colormap', Colormap),
		('map_installed', c_bool),
		('map_state', c_int),
		('all_event_masks', c_long),
		('your_event_mask', c_long),
		('do_not_propagate_mask', c_long),
		('map_installed', c_bool),
		('screen', c_void_p)
	]


# Consants
SHAPE_BOUNDING	= 0
SHAPE_CLIP		= 1
SHAPE_INPUT		= 2
SHAPE_SET		= 0

XKBUSECOREKBD	= 0x0100
ANYPROPERTYTYPE	= 0
SUCCESS			= 0

ISVIEWABLE		= 2


# Functions
open_display = libX11.XOpenDisplay
open_display.__doc__ = "Opens connection to XDisplay"
open_display.argtypes = [ c_char_p ]
open_display.restype = c_void_p

free = libX11.XFree
free.__doc__ = "Used to free some resource returned by XLib"
free.argtypes = [ c_void_p ]

create_region = libXFixes.XFixesCreateRegion
create_region.__doc__ = "Creates rectanglular region for use with set_window_shape_region"
create_region.argtypes = [ c_void_p, POINTER(XRectangle), c_int ]
create_region.restype = XserverRegion

set_window_shape_region = libXFixes.XFixesSetWindowShapeRegion
set_window_shape_region.__doc__ = "Sets region in which window accepts inputs"
set_window_shape_region.argtypes = [ c_void_p, XID, c_int, c_int, c_int, XserverRegion ]

destroy_region = libXFixes.XFixesDestroyRegion
destroy_region.__doc__ = "Frees region created by create_region"
destroy_region.argtypes = [ c_void_p, XserverRegion ]

get_default_root_window = libX11.XDefaultRootWindow
get_default_root_window.argtypes = [ c_void_p ]

flush = libX11.XFlush
flush.__doc__ = "Asks Xlib to send queued commands to XServer"
flush.argtypes = [ c_void_p ]

warp_pointer = libX11.XWarpPointer
warp_pointer.__doc__ = "Very, very, V*E*R*Y complicated shit used to move cursor"
warp_pointer.argtypes = [ c_void_p, XID, XID, c_int, c_int, c_int, c_int, c_int, c_int ]

query_pointer = libX11.XQueryPointer
query_pointer.__doc__ = "Returns a lot of nonsense along with mouse cursor position"
query_pointer.argtypes = [ c_void_p, XID, POINTER(XID), POINTER(XID),
	POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_uint) ]

get_window_attributes = libX11.XGetWindowAttributes
get_window_attributes.__doc__ = "https://tronche.com/gui/x/xlib/window-information/XGetWindowAttributes.html"
get_window_attributes.argtypes = [ c_void_p, XID, POINTER(XWindowAttributes) ]


translate_coordinates = libX11.XTranslateCoordinates
translate_coordinates.argtypes = [ c_void_p, XID, XID, c_int, c_int,
	POINTER(c_int), POINTER(c_int), POINTER(XID) ]
translate_coordinates.restype = c_bool


get_input_focus = libX11.XGetInputFocus
get_input_focus.__doc__ = """Returns window that currently have window focus.
	Most of window managers and some GTK applications are breaking this.
	See https://specifications.freedesktop.org/wm-spec/1.3/ar01s03.html
	"""
get_input_focus.argtypes = [ c_void_p, POINTER(XID), POINTER(c_int) ]

get_window_property = libX11.XGetWindowProperty
get_window_property.__doc__ = "Returns value of property associated with window"
get_window_property.argtypes = [ c_void_p, XID, Atom, c_long, c_long, c_bool,
	Atom, POINTER(Atom), POINTER(Atom), POINTER(c_ulong), POINTER(c_ulong),
	POINTER(c_void_p) ]
get_window_property.restype = c_int

alloc_class_hint = libX11.XAllocClassHint
alloc_class_hint.restype = POINTER(XClassHint)
alloc_class_hint.argtypes = []
alloc_class_hint.__doc__ = 	"""Allocates and returns a pointer to a XClassHint
	structure. Returned pointer has to be deallocated using free()"""

get_class_hint = libX11.XGetClassHint
get_class_hint.argtypes = [ c_void_p, XID, POINTER(XClassHint) ]
get_class_hint.restype = c_int

intern_atom = libX11.XInternAtom
intern_atom.__doc__ = "Returns integer ID for specified Atom name."
intern_atom.argtypes = [ c_void_p, c_char_p, c_bool ]
intern_atom.restype = Atom

create_pixmap = libX11.XCreatePixmap
create_pixmap.argtypes = [ c_void_p, XID, c_uint, c_uint, c_uint ]
create_pixmap.restype = Pixmap

create_pixmap_from_bitmap = libX11.XCreatePixmapFromBitmapData
create_pixmap_from_bitmap.argtypes = [ c_void_p, XID, c_char_p, c_uint, c_uint, c_uint, c_uint, c_uint ]
create_pixmap_from_bitmap.restype = Pixmap

write_bitmap = libX11.XWriteBitmapFile
write_bitmap.argtypes = [ c_void_p, c_char_p, Pixmap, c_uint, c_uint, c_int, c_int ]
write_bitmap.restype = c_int

free_pixmap = libX11.XFreePixmap
free_pixmap.__doc__ = "Deallocates pixmap created by create_pixmap"
free_pixmap.argtypes = [ c_void_p, Pixmap ]

create_gc = libX11.XCreateGC
create_gc.__doc__ = "Creates graphics context to draw on"
create_gc.argtypes = [ c_void_p, XID, c_ulong, c_void_p ]
create_gc.restype = GC

flush_gc = libX11.XFlushGC
flush_gc.__doc__ = "Force sending GC component changes"
flush_gc.argtypes = [ c_void_p, GC ]

free_gc = libX11.XFreeGC
free_gc.__doc__ = "Deallocates graphics context created by create_gc"
free_gc.argtypes = [ c_void_p, GC ]

fill_rectangle = libX11.XFillRectangle
fill_rectangle.__doc__ = "Draws and fills rectangle on graphics context"
fill_rectangle.argtypes = [ c_void_p, XID, GC, c_int, c_int, c_uint, c_uint ]

draw_arc = libX11.XDrawArc
draw_arc.argtypes = [ c_void_p, Pixmap, GC, c_int, c_int, c_uint, c_uint, c_int, c_int ]

fill_arc = libX11.XFillArc
fill_arc.argtypes = [ c_void_p, Pixmap, GC, c_int, c_int, c_uint, c_uint, c_int, c_int ]


set_foreground = libX11.XSetForeground
set_foreground.__doc__ = "Sets foreground color for drawing on graphics context"
set_foreground.argtypes = [ c_void_p, GC, c_ulong ]

set_background = libX11.XSetBackground
set_background.__doc__ = "Sets background color for drawing on graphics context"
set_background.argtypes = set_foreground.argtypes

shape_combine_mask = libXext.XShapeCombineMask
shape_combine_mask.__doc__ = "Sets 1-bit transparency mask for window"
shape_combine_mask.argtypes = [ c_void_p, XID, c_int, c_int, c_int, Pixmap, c_int ]



# Wrapped functions
_xkb_get_state = libX11.XkbGetState
_xkb_get_state.argtypes = [c_void_p, c_uint, POINTER(XkbStateRec)]

# Wrappers
def get_xkb_state(dpy):
	rec = XkbStateRec()
	_xkb_get_state(dpy, XKBUSECOREKBD, rec)
	return rec


def get_window_size(dpy, window):
	attrs = XWindowAttributes()
	get_window_attributes(dpy, window, byref(attrs))
	return attrs.width, attrs.height


def is_window_visible(dpy, window):
	""" Return True if window mapping state is IsViewable """
	attrs = XWindowAttributes()
	get_window_attributes(dpy, window, byref(attrs))
	return attrs.map_state == ISVIEWABLE


def get_window_geometry(dpy, win):
	""" Returns window x,y,width,height """
	attrs = XWindowAttributes()
	get_window_attributes(dpy, win, byref(attrs))
	x, y = c_int(), c_int()
	trash = XID()
	if translate_coordinates(dpy, win, get_default_root_window(dpy),
			0, 0, byref(x), byref(y), byref(trash)):
		return x.value, y.value, attrs.width, attrs.height
	else:
		# translate_coordinates failed
		return attrs.x, attrs.y, attrs.width, attrs.height


def get_screen_size(dpy):
	return get_window_size(dpy, get_default_root_window(dpy))


def get_mouse_pos(dpy, relative_to=None):
	"""
	Returns mouse position relative to specified window or to screen, if no
	window is specified.
	"""
	if relative_to is None:
		relative_to = get_default_root_window(dpy)
	root_return, child = XID(), XID()
	x, y = c_int(), c_int()
	child_x, child_y = c_int(), c_int()
	mask = c_uint()
	
	query_pointer(dpy, relative_to, byref(root_return), byref(child),
		byref(x), byref(y),
		byref(child_x), byref(child_y), byref(mask))
	return x.value, y.value


def set_mouse_pos(dpy, x, y, relative_to=None):
	"""
	Sets mouse position relative to specified window or to screen, if no
	window is specified.
	"""
	if relative_to is None:
		relative_to = get_default_root_window(dpy)
	warp_pointer(dpy, 0, relative_to, 0, 0, 0, 0, x, y)
	flush(dpy)


def get_window_prop(dpy, window, prop_name, max_size=2):
	"""
	Returns (nitems, property) of specified window or (-1, None) if anything fails.
	Returned 'property' is POINTER(c_void_p) and has to be freed using X.free().
	"""
	prop_atom = intern_atom(dpy, prop_name, False)
	type_return, format_return = Atom(), Atom()
	nitems, bytes_after = c_ulong(), c_ulong()
	prop = c_void_p()
	
	if SUCCESS == get_window_property(dpy, window,
				prop_atom, 0, max_size, False, ANYPROPERTYTYPE,
				byref(type_return), byref(format_return), byref(nitems),
				byref(bytes_after), byref(prop)):
		return nitems.value, prop
	return -1, None


def get_current_window(dpy):
	"""
	Returns active window or root window if there is no active.
	"""
	# Try using WM-provided info first
	trash, prop = get_window_prop(dpy,
			get_default_root_window(dpy), "_NET_ACTIVE_WINDOW")
	if prop is not None:
		rv = cast(prop, POINTER(Atom)).contents.value
		free(prop)
		return rv
	
	# Fall-back to something what probably can't work anyway
	win, revert_to = XID(), c_int()
	get_input_focus(dpy, byref(win), byref(revert_to))
	if win == 0:
		return get_default_root_window(dpy)
	return win


def get_window_type(dpy, window):
	"""
	Returns _NET_WM_WINDOW_TYPE value for window specified or None if anything
	fails while recieving it.
	"""
	trash, prop = get_window_prop(dpy, window, "_NET_WM_WINDOW_TYPE")
	if prop is not None and prop.value is not None:
		rv = cast(prop, POINTER(Atom)).contents.value
		free(prop)
		return rv
	return None


def get_window_title(dpy, window):
	"""
	Returns window title or None if title cannot be obtained.
	"""
	for prop_name in ("_NET_WM_NAME", "WM_NAME"):
		trash, prop = get_window_prop(dpy, window, prop_name, max_size=2048)
		if prop:
			try:
				value = cast(prop, c_char_p).value.decode('utf-8')
				free(prop)
				return value
			except: pass
			free(prop)
	return None


def get_window_class(dpy, window):
	"""
	Returns window class or None, None if class cannot be obtained.
	"""
	s = alloc_class_hint()
	if s:
		if get_class_hint(dpy, window, s):
			value = s.contents.res_name.decode('utf-8'), s.contents.res_class.decode('utf-8')
			free(s)
			return value
		free(s)
	
	return None, None


def get_wm_state(dpy, window):
	"""
	Returns list of _NET_WM_STATE atoms assotiated with window or empty list
	if list be obtained.
	"""
	count, state = get_window_prop(dpy, window, "_NET_WM_STATE", 1024)
	if count <= 0: return []
	return cast(state, POINTER(Atom))[0:count]
