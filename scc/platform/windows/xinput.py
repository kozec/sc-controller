#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
SC-Controller - XInput stub

As Windows has no XInput, this just returns empty lists of devices.
"""
from __future__ import unicode_literals

import logging, re, subprocess
log = logging.getLogger("XI")

def get_devices():
	"""
	Returns empty list of devices
	"""
	return []
