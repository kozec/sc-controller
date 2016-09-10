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
	
	
	def init(daemon):
		pass
	
	
	def start(daemon):
		num = int(os.environ[ENV_VAR])
		log.debug("Creating %s fake controllers", num)
		for x in xrange(0, num):
			daemon.add_controller(FakeController(x))


	class FakeController(Controller):
		def __init__(self, number):
			Controller.__init__(self)
			self._number = number
			self.set_name(self.get_id())
		
		
		def __repr__(self):
			return "<FakeController sc%s>" % (self._number,)
		
		
		def get_id(self):
			return "fake%s" % (self._number,)
