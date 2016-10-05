#!/usr/bin/env python2
"""
SC-Controller - Aliases

This module generates Keys.BTN_x and Axes.AXIS_x aliases when imported
"""

from scc.uinput import Axes, Keys
from scc.constants import ALL_BUTTONS, ALL_AXES

for i in xrange(0, len(ALL_BUTTONS)):
	setattr(Keys, "BTN%i" % (i,), ALL_BUTTONS[i])

for i in xrange(0, len(ALL_AXES)):
	setattr(Axes, "ABS%i" % (i,), ALL_AXES[i])
