#!/usr/bin/env python2
"""
SC-Controller - Aliases

This module generates Keys.BTN_x and Axes.AXIS_x aliases when imported
"""

from scc.uinput import Axes, Keys

ALL_BUTTONS = ( Keys.BTN_START, Keys.BTN_MODE, Keys.BTN_SELECT, Keys.BTN_A,
	Keys.BTN_B, Keys.BTN_X, Keys.BTN_Y, Keys.BTN_TL, Keys.BTN_TR,
	Keys.BTN_THUMBL, Keys.BTN_THUMBR, Keys.BTN_WHEEL, Keys.BTN_GEAR_DOWN,
	Keys.BTN_GEAR_UP, Keys.KEY_OK, Keys.KEY_SELECT, Keys.KEY_GOTO,
	Keys.KEY_CLEAR, Keys.KEY_OPTION, Keys.KEY_INFO, Keys.KEY_TIME,
	Keys.KEY_VENDOR, Keys.KEY_ARCHIVE, Keys.KEY_PROGRAM, Keys.KEY_CHANNEL,
	Keys.KEY_FAVORITES, Keys.KEY_EPG )

ALL_AXES = ( Axes.ABS_X, Axes.ABS_Y, Axes.ABS_RX, Axes.ABS_RY, Axes.ABS_Z,
	Axes.ABS_RZ, Axes.ABS_HAT0X, Axes.ABS_HAT0Y, Axes.ABS_HAT1X, Axes.ABS_HAT1Y,
	Axes.ABS_HAT2X, Axes.ABS_HAT2Y, Axes.ABS_HAT3X, Axes.ABS_HAT3Y,
	Axes.ABS_PRESSURE, Axes.ABS_DISTANCE, Axes.ABS_TILT_X, Axes.ABS_TILT_Y,
	Axes.ABS_TOOL_WIDTH, Axes.ABS_VOLUME, Axes.ABS_MISC )

for i in range(0, len(ALL_BUTTONS)):
	setattr(Keys, "BTN%i" % (i,), ALL_BUTTONS[i])

for i in range(0, len(ALL_AXES)):
	setattr(Axes, "ABS%i" % (i,), ALL_AXES[i])
