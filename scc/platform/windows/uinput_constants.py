#!/usr/bin/env python2
"""
UInput emulation on Windows - constants.

See uinput.py for details.
"""
from scc.cheader import defines
from scc.lib import IntEnum

UNPUT_MODULE_VERSION = 6

# Get All defines from linux headers
CHEAD = defines('./scc/platform/windows', 'input.h')

MAX_FEEDBACK_EFFECTS = 4

# Keys enum contains all keys and button from linux/uinput.h (KEY_* BTN_*)
Keys = IntEnum('Keys', {i: CHEAD[i] for i in CHEAD.keys() if (i.startswith('KEY_') or
															i.startswith('BTN_'))})
# Keys enum contains all keys and button from linux/uinput.h (KEY_* BTN_*)
KeysOnly = IntEnum('KeysOnly', {i: CHEAD[i] for i in CHEAD.keys() if i.startswith('KEY_')})

# Axes enum contains all axes from linux/uinput.h (ABS_*)
Axes = IntEnum('Axes', {i: CHEAD[i] for i in CHEAD.keys() if i.startswith('ABS_')})

# Rels enum contains all rels from linux/uinput.h (REL_*)
Rels = IntEnum('Rels', {i: CHEAD[i] for i in CHEAD.keys() if i.startswith('REL_')})

# Scan codes for each keys (taken from a logitech keyboard)
Scans = {
	Keys.KEY_ESC: 0x70029,
	Keys.KEY_F1: 0x7003a,
	Keys.KEY_F2: 0x7003b,
	Keys.KEY_F3: 0x7003c,
	Keys.KEY_F4: 0x7003d,
	Keys.KEY_F5: 0x7003e,
	Keys.KEY_F6: 0x7003f,
	Keys.KEY_F7: 0x70040,
	Keys.KEY_F8: 0x70041,
	Keys.KEY_F9: 0x70042,
	Keys.KEY_F10: 0x70043,
	Keys.KEY_F11: 0x70044,
	Keys.KEY_F12: 0x70045,
	Keys.KEY_SYSRQ: 0x70046,
	Keys.KEY_SCROLLLOCK: 0x70047,
	Keys.KEY_PAUSE: 0x70048,
	Keys.KEY_GRAVE: 0x70035,
	Keys.KEY_1: 0x7001e,
	Keys.KEY_2: 0x7001f,
	Keys.KEY_3: 0x70020,
	Keys.KEY_4: 0x70021,
	Keys.KEY_5: 0x70022,
	Keys.KEY_6: 0x70023,
	Keys.KEY_7: 0x70024,
	Keys.KEY_8: 0x70025,
	Keys.KEY_9: 0x70026,
	Keys.KEY_0: 0x70027,
	Keys.KEY_MINUS: 0x7002d,
	Keys.KEY_EQUAL: 0x7002e,
	Keys.KEY_BACKSPACE: 0x7002a,
	Keys.KEY_TAB: 0x7002b,
	Keys.KEY_Q: 0x70014,
	Keys.KEY_W: 0x7001a,
	Keys.KEY_E: 0x70008,
	Keys.KEY_R: 0x70015,
	Keys.KEY_T: 0x70017,
	Keys.KEY_Y: 0x7001c,
	Keys.KEY_U: 0x70018,
	Keys.KEY_I: 0x7000c,
	Keys.KEY_O: 0x70012,
	Keys.KEY_P: 0x70013,
	Keys.KEY_LEFTBRACE: 0x7002f,
	Keys.KEY_RIGHTBRACE: 0x70030,
	Keys.KEY_ENTER: 0x70028,
	Keys.KEY_CAPSLOCK: 0x70039,
	Keys.KEY_A: 0x70004,
	Keys.KEY_S: 0x70016,
	Keys.KEY_D: 0x70007,
	Keys.KEY_F: 0x70009,
	Keys.KEY_G: 0x7000a,
	Keys.KEY_H: 0x7000b,
	Keys.KEY_J: 0x7000d,
	Keys.KEY_K: 0x7000e,
	Keys.KEY_L: 0x7000f,
	Keys.KEY_SEMICOLON: 0x70033,
	Keys.KEY_APOSTROPHE: 0x70034,
	Keys.KEY_BACKSLASH: 0x70032,
	Keys.KEY_LEFTSHIFT: 0x700e1,
	Keys.KEY_102ND: 0x70064,
	Keys.KEY_Z: 0x7001d,
	Keys.KEY_X: 0x7001b,
	Keys.KEY_C: 0x70006,
	Keys.KEY_V: 0x70019,
	Keys.KEY_B: 0x70005,
	Keys.KEY_N: 0x70011,
	Keys.KEY_M: 0x70010,
	Keys.KEY_COMMA: 0x70036,
	Keys.KEY_DOT: 0x70037,
	Keys.KEY_SLASH: 0x70038,
	Keys.KEY_RIGHTSHIFT: 0x700e5,
	Keys.KEY_LEFTCTRL: 0x700e0,
	Keys.KEY_LEFTMETA: 0x700e3,
	Keys.KEY_LEFTALT: 0x700e2,
	Keys.KEY_SPACE: 0x7002c,
	Keys.KEY_RIGHTALT: 0x700e6,
	Keys.KEY_RIGHTMETA: 0x700e7,
	Keys.KEY_COMPOSE: 0x70065,
	Keys.KEY_RIGHTCTRL: 0x700e4,
	Keys.KEY_INSERT: 0x70049,
	Keys.KEY_HOME: 0x7004a,
	Keys.KEY_PAGEUP: 0x7004b,
	Keys.KEY_DELETE: 0x7004c,
	Keys.KEY_END: 0x7004d,
	Keys.KEY_PAGEDOWN: 0x7004e,
	Keys.KEY_UP: 0x70052,
	Keys.KEY_LEFT: 0x70050,
	Keys.KEY_DOWN: 0x70051,
	Keys.KEY_RIGHT: 0x7004f,
	Keys.KEY_NUMLOCK: 0x70053,
	Keys.KEY_KPSLASH: 0x70054,
	Keys.KEY_KPASTERISK: 0x70055,
	Keys.KEY_KPMINUS: 0x70056,
	Keys.KEY_KP7: 0x7005f,
	Keys.KEY_KP8: 0x70060,
	Keys.KEY_KP9: 0x70061,
	Keys.KEY_KPPLUS: 0x70057,
	Keys.KEY_KP4: 0x7005c,
	Keys.KEY_KP5: 0x7005d,
	Keys.KEY_KP6: 0x7005e,
	Keys.KEY_KP1: 0x70059,
	Keys.KEY_KP2: 0x7005a,
	Keys.KEY_KP3: 0x7005b,
	Keys.KEY_KPENTER: 0x70058,
	Keys.KEY_KP0: 0x70062,
	Keys.KEY_KPDOT: 0x70063,
	Keys.KEY_CONFIG: 0xc0183,
	Keys.KEY_PLAYPAUSE: 0xc00cd,
	Keys.KEY_MUTE: 0xc00e2,
	Keys.KEY_VOLUMEDOWN: 0xc00ea,
	Keys.KEY_VOLUMEUP: 0xc00e9,
	Keys.KEY_HOMEPAGE: 0xc0223,

	Keys.KEY_PREVIOUSSONG: 0xc00f0,
	Keys.KEY_NEXTSONG: 0xc00f1,

	Keys.KEY_BACK: 0xc00f2,
	Keys.KEY_FORWARD: 0xc00f3,
}

SCAN_TO_VK = {
	Keys.KEY_LEFT.value:	0x25,	# VK_LEFT
	Keys.KEY_UP.value:		0x26,	# VK_UP
	Keys.KEY_RIGHT.value:	0x27,	# VK_RIGHT
	Keys.KEY_DOWN.value:	0x28,	# VK_DOWN
}
