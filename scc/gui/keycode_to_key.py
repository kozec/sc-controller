#!/usr/bin/env python2
"""
SC-Controller - KEYCODE_TO_KEY

Similar to GDK_TO_KEY, maps X11 keycodes to Keys.KEY_* constants.
Used by OSD keyboard
"""
from __future__ import unicode_literals

from scc.uinput import Keys

KEYCODE_TO_KEY = {
	# Row 1
	9	: Keys.KEY_ESC,
	67	: Keys.KEY_F1,
	68	: Keys.KEY_F2,
	69	: Keys.KEY_F3,
	70	: Keys.KEY_F4,
	71	: Keys.KEY_F5,
	72	: Keys.KEY_F6,
	73	: Keys.KEY_F7,
	74	: Keys.KEY_F8,
	75	: Keys.KEY_F9,
	76	: Keys.KEY_F10,
	95	: Keys.KEY_F11,
	96	: Keys.KEY_F12,
	107	: Keys.KEY_PRINT,
	78	: Keys.KEY_SCROLLLOCK,
	127	: Keys.KEY_PAUSE,
	
	# Row 2
	49	: Keys.KEY_GRAVE,	# tilde
	10	: Keys.KEY_1,
	11	: Keys.KEY_2,
	12	: Keys.KEY_3,
	13	: Keys.KEY_4,
	14	: Keys.KEY_5,
	15	: Keys.KEY_6,
	16	: Keys.KEY_7,
	17	: Keys.KEY_8,
	18	: Keys.KEY_9,
	19	: Keys.KEY_0,
	20	: Keys.KEY_MINUS,
	21	: Keys.KEY_EQUAL,
	22	: Keys.KEY_BACKSPACE,
	
	# Row 3
	23	: Keys.KEY_TAB,
	24	: Keys.KEY_Q,
	25	: Keys.KEY_W,
	26	: Keys.KEY_E,
	27	: Keys.KEY_R,
	28	: Keys.KEY_T,
	29	: Keys.KEY_Y,
	30	: Keys.KEY_U,
	31	: Keys.KEY_I,
	32	: Keys.KEY_O,
	33	: Keys.KEY_P,
	34	: Keys.KEY_LEFTBRACE,
	35	: Keys.KEY_RIGHTBRACE,
	51	: Keys.KEY_BACKSLASH,
	
	# Row 4
	66	: Keys.KEY_CAPSLOCK,
	38	: Keys.KEY_A,
	39	: Keys.KEY_S,
	40	: Keys.KEY_D,
	41	: Keys.KEY_F,
	42	: Keys.KEY_G,
	43	: Keys.KEY_H,
	44	: Keys.KEY_J,
	45	: Keys.KEY_K,
	46	: Keys.KEY_L,
	47	: Keys.KEY_SEMICOLON,
	48	: Keys.KEY_APOSTROPHE,
	36	: Keys.KEY_ENTER,
	
	# Row 5
	50	: Keys.KEY_LEFTSHIFT,
	52	: Keys.KEY_Z,
	53	: Keys.KEY_X,
	54	: Keys.KEY_C,
	55	: Keys.KEY_V,
	56	: Keys.KEY_B,
	57	: Keys.KEY_N,
	58	: Keys.KEY_M,
	59	: Keys.KEY_COMMA,
	60	: Keys.KEY_DOT,
	61	: Keys.KEY_SLASH,
	62	: Keys.KEY_RIGHTSHIFT,
	
	# Numpad
	90	: Keys.KEY_KP0,
	87	: Keys.KEY_KP1,
	88	: Keys.KEY_KP2,
	89	: Keys.KEY_KP3,
	83	: Keys.KEY_KP4,
	84	: Keys.KEY_KP5,
	85	: Keys.KEY_KP6,
	79	: Keys.KEY_KP7,
	80	: Keys.KEY_KP8,
	81	: Keys.KEY_KP9,
	91	: Keys.KEY_KPDOT,
	106	: Keys.KEY_KPSLASH,
	86	: Keys.KEY_KPPLUS,
	63	: Keys.KEY_KPASTERISK,
	82	: Keys.KEY_KPMINUS,
	104	: Keys.KEY_KPENTER,
	77	: Keys.KEY_NUMLOCK,
	
	# Home & co
	118	: Keys.KEY_INSERT,
	110	: Keys.KEY_HOME,
	112	: Keys.KEY_PAGEUP,
	119	: Keys.KEY_DELETE,
	115	: Keys.KEY_END,
	117	: Keys.KEY_PAGEDOWN,
	
	# Arrows
	111	: Keys.KEY_UP,
	113	: Keys.KEY_LEFT,
	114	: Keys.KEY_RIGHT,
	116	: Keys.KEY_DOWN,
	
	# Bottom row
	37	: Keys.KEY_LEFTCTRL,
	133	: Keys.KEY_LEFTMETA,
	64	: Keys.KEY_LEFTALT,
	65	: Keys.KEY_SPACE,
	108	: Keys.KEY_RIGHTALT,
	134	: Keys.KEY_RIGHTMETA,
	135	: Keys.KEY_COMPOSE,
	105	: Keys.KEY_RIGHTCTRL,
}

KEY_TO_KEYCODE = { KEYCODE_TO_KEY[a] : a for a in KEYCODE_TO_KEY }
