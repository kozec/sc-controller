#!/usr/bin/env python2
"""
SC Controller - Fake controller driver

This driver does nothing by default, unless SCC_FAKES environment variable is
set. If it is, creates as many fake controller devices as integer stored in
SCC_FAKES says.

Created controllers are completely useless. For debuging purposes only.
"""

from scc.controller import Controller
import os, logging

ENV_VAR = "SCC_FAKES"

if ENV_VAR in os.environ:
	log = logging.getLogger("FakeDrv")
	
	
	def init(daemon, config):
		return True
	
	
	def start(daemon):
		num = int(os.environ[ENV_VAR])
		log.debug("Creating %s fake controllers", num)
		for x in range(0, num):
			daemon.add_controller(FakeController(x))


class FakeController(Controller):
	def __init__(self, number):
		Controller.__init__(self)
		self._number = number
		self._id = "fake%s" % (self._number,)
	
	
	def get_type(self):
		return "fake"
	
	
	def set_led_level(self, level):
		log.debug("FakeController %s led level set to %s", self.get_id(), level)
	
	
	def __repr__(self):
		return "<FakeController %s>" % (self.get_id(),)
