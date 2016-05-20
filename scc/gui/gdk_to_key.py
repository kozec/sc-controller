#!/usr/bin/env python2
"""
SC-Controller - GDK_TO_KEY

Maps Gdk.KEY_* constants into Keys.KEY_* constants.
Used by ActionEditor (when grabbing the key)
"""
from __future__ import unicode_literals

from gi.repository import Gdk
from scc.uinput import Keys

GDK_TO_KEY = {
	# Row 1
	Gdk.KEY_Escape		: Keys.KEY_ESC,
	Gdk.KEY_Print		: Keys.KEY_PRINT,
	Gdk.KEY_Scroll_Lock	: Keys.KEY_SCROLLLOCK,
	Gdk.KEY_Sys_Req		: Keys.KEY_SYSRQ,
	Gdk.KEY_Pause		: Keys.KEY_PAUSE,
	
	# Row 2
	Gdk.KEY_quoteleft	: Keys.KEY_GRAVE,	# tilde
	Gdk.KEY_minus		: Keys.KEY_MINUS,
	Gdk.KEY_equal		: Keys.KEY_EQUAL,
	Gdk.KEY_BackSpace	: Keys.KEY_BACKSPACE,
	
	# Row 3
	Gdk.KEY_Tab			: Keys.KEY_TAB,
	Gdk.KEY_bracketleft	: Keys.KEY_LEFTBRACE,
	Gdk.KEY_bracketright: Keys.KEY_RIGHTBRACE,
	Gdk.KEY_backslash	: Keys.KEY_BACKSLASH,
	
	# Row 4
	Gdk.KEY_Caps_Lock	: Keys.KEY_CAPSLOCK,
	Gdk.KEY_semicolon	: Keys.KEY_SEMICOLON,
	Gdk.KEY_apostrophe	: Keys.KEY_APOSTROPHE,
	Gdk.KEY_Return		: Keys.KEY_ENTER,
	
	# Row 5
	Gdk.KEY_Shift_L		: Keys.KEY_LEFTSHIFT,
	Gdk.KEY_comma		: Keys.KEY_COMMA,
	Gdk.KEY_period		: Keys.KEY_DOT,
	Gdk.KEY_slash		: Keys.KEY_SLASH,
	Gdk.KEY_Shift_R		: Keys.KEY_RIGHTSHIFT,
	
	# Numpad
	Gdk.KEY_KP_0		: Keys.KEY_KP0,
	Gdk.KEY_KP_1		: Keys.KEY_KP1,
	Gdk.KEY_KP_2		: Keys.KEY_KP2,
	Gdk.KEY_KP_3		: Keys.KEY_KP3,
	Gdk.KEY_KP_4		: Keys.KEY_KP4,
	Gdk.KEY_KP_5		: Keys.KEY_KP5,
	Gdk.KEY_KP_6		: Keys.KEY_KP6,
	Gdk.KEY_KP_7		: Keys.KEY_KP7,
	Gdk.KEY_KP_8		: Keys.KEY_KP8,
	Gdk.KEY_KP_9		: Keys.KEY_KP9,
	Gdk.KEY_KP_Delete	: Keys.KEY_KPDOT,
	Gdk.KEY_KP_Divide	: Keys.KEY_KPSLASH,
	Gdk.KEY_KP_Add		: Keys.KEY_KPPLUS,
	Gdk.KEY_KP_Multiply	: Keys.KEY_KPASTERISK,
	Gdk.KEY_KP_Subtract	: Keys.KEY_KPMINUS,
	Gdk.KEY_KP_Enter	: Keys.KEY_KPENTER,
	Gdk.KEY_Num_Lock	: Keys.KEY_NUMLOCK,
	
	# Home & co
	Gdk.KEY_Insert		: Keys.KEY_INSERT,
	Gdk.KEY_Home		: Keys.KEY_HOME,
	Gdk.KEY_Page_Up		: Keys.KEY_PAGEUP,
	Gdk.KEY_Delete		: Keys.KEY_DELETE,
	Gdk.KEY_End			: Keys.KEY_END,
	Gdk.KEY_Page_Down	: Keys.KEY_PAGEDOWN,
	
	# Arrows
	Gdk.KEY_Up			: Keys.KEY_UP,
	Gdk.KEY_Left		: Keys.KEY_LEFT,
	Gdk.KEY_Right		: Keys.KEY_RIGHT,
	Gdk.KEY_Down		: Keys.KEY_DOWN,
	
	# Bottom row
	Gdk.KEY_Control_L	: Keys.KEY_LEFTCTRL,
	Gdk.KEY_Super_L		: Keys.KEY_LEFTMETA,
	Gdk.KEY_Alt_L		: Keys.KEY_LEFTALT,
	Gdk.KEY_space		: Keys.KEY_SPACE,
	Gdk.KEY_Alt_R		: Keys.KEY_RIGHTALT,
	Gdk.KEY_Super_R		: Keys.KEY_RIGHTMETA,
	Gdk.KEY_Menu		: Keys.KEY_COMPOSE,
	Gdk.KEY_Control_R	: Keys.KEY_RIGHTCTRL,
}

# Stuff that is missing above is auto-generated here
names = { x.name : x for x in Keys }

for x in dir(Gdk):
	if x.startswith("KEY_"):
		if x in names:
			GDK_TO_KEY[getattr(Gdk, x)] = names[x]

# A-Z keys, because GDK has different codes for 'A' and 'a'
for x in xrange(ord('a'), ord('z')+1):
	GDK_TO_KEY[getattr(Gdk, "KEY_" + chr(x))] = names["KEY_" + chr(x).upper()]

KEY_TO_GDK = { GDK_TO_KEY[a] : a for a in GDK_TO_KEY }

def keyevent_to_key(event):
	keymap = Gdk.Keymap.get_default()
	found, whatever, keyvals = keymap.get_entries_for_keycode(event.hardware_keycode)
	if found and len(keyvals) > 0:
		if keyvals[0] in GDK_TO_KEY:
			return GDK_TO_KEY[keyvals[0]]
	
	if event.keyval in GDK_TO_KEY:
		return GDK_TO_KEY[event.keyval]
	return None
