#!/usr/bin/env python2
"""
Quick and dirty ViGEm wrapper.

Supplies controller emulation part of uinput on Windows
"""

from ctypes import c_void_p, c_int32
from scc.tools import find_library

import sys, time
sys.path.insert(0, "build/lib.win32-2.7")

import vigemclient

vigemclient.connect()
target = vigemclient.target_x360_alloc()
print vigemclient.target_add(target)

report = vigemclient.XUSBReport()
print report
print dir(report)


while True:
	time.sleep(0.1)
	print "Doing nothing..."
	sys.stdout.flush()
