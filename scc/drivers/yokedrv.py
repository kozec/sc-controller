#!/usr/bin/env python2
"""
SC Controller - Yoke driver

Works with Yoke android application
"""

from zeroconf import InterfaceChoice, ServiceInfo, Zeroconf
from scc.constants import ControllerFlags
from scc.controller import Controller
from collections import namedtuple
import time, socket, sys, os, logging

log = logging.getLogger("YokeDrv")


YokeInput = namedtuple("YokeInput",
	('buttons', 'stick_x', 'stick_y', 'lpad_x', 'lpad_y', 'rpad_x', 'rpad_y',
	'ltrig', 'rtrig', 'gpitch', 'groll', 'gyaw', 'q1', 'q2', 'q3', 'q4',))

class YokeController(Controller):
	flags = ControllerFlags.HAS_RSTICK | ControllerFlags.SEPARATE_STICK
	
	def __init__(self, driver, address):
		Controller.__init__(self)
		self._address = address
		self._id = "yoke01"
		self._last_message = time.time()
		self._driver = driver
		self._old_state = YokeInput(*([0] * 16))
		self._check_timeout()
	
	def get_type(self):
		return "yoke"
	
	def __repr__(self):
		return "<YokeController %s>" % (self.get_id(),)
	
	def _check_timeout(self):
		if time.time() - self._last_message > 3:
			self._driver.on_timeout(self)
		else:
			self._driver.daemon.get_scheduler().schedule(1.0, self._check_timeout)
	
	@staticmethod
	def preprocess(message):
		v = message.split()[1:]  # first value is useless at the moment
		v = [float(m) for m in v]
		v = (
			(v[0]/9.81 - 0)    * 1.5 / 2 + 0.5,
			(v[1]/9.81 - 0.52) * 3.0 / 2 + 0.5,
			int(v[2] * 32767),
			int(v[3] * -32767),
			int(v[4] * 32767),
			int(v[5] * -32767),
		)
		return v
	
	def input(self, message):
		self._last_message = time.time()
		# This is called from try...catch everything block, so crashing on
		# badly formed message  is OK
		w1, w2, stick_x, stick_y, rpad_x, rpad_y = YokeController.preprocess(message)
		idata = YokeInput(
			0,					# buttons
			stick_x, stick_y,
			0, 0,				# lpad_x, lpad_y
			rpad_x, rpad_y,
			0, 0,				# ltrig, rtrig
			0, 0, 0,			# pitch, roll, yaw
			0, 0, 0, 0			# q's
		)
		old_state, self._old_state = self._old_state, idata
		self.mapper.input(self, old_state, idata)


class YokeDrv:
	def __init__(self, daemon):
		self.daemon = daemon
		self.controller = None
		self.zeroconf = Zeroconf()
		self.trecv = time.time()
		self.irecv = 0
		
		log.debug("Registering zeroconf service...")
		# open udp socket on random available port
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 512)  # small buffer for low latency
		self.sock.bind((YokeDrv.get_ip_address(), 0))
		self.sock.settimeout(0)
		adr, port = self.sock.getsockname()
		# self.daemon.add_mainloop(self.mainloop)
		poller = self.daemon.get_poller()
		poller.register(self.sock.fileno(), poller.POLLIN, self.on_data_ready)
		
		# create zeroconf service
		stype = "_yoke._udp.local."
		netname = socket.gethostname() + "-sc-controller"
		fullname = netname + "." + stype
		self.info = ServiceInfo(stype, fullname, socket.inet_aton(adr), port, 0, 0, {}, fullname)
		self.zeroconf.register_service(self.info, ttl=10)
		log.info('To connect, select "%s" on your device.' % (netname, ))
	
	@staticmethod
	def get_ip_address():
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(("8.8.8.8", 80))
		ip = s.getsockname()[0]
		s.close()
		return ip
	
	def on_exit(self, *a):
		self.daemon.get_poller().unregister(self.sock.fileno())
		if self.sock is not None:
			self.sock.close()
		if self.info is not None:
			self.zeroconf.unregister_service(self.info)
		log.debug("Unregistered zeroconf service.")
	
	def on_data_ready(self, *a):
		try:
			m, address = self.sock.recvfrom(128)
			if self.controller is None:
				self.controller = YokeController(self, address)
				self.daemon.add_controller(self.controller)
			self.controller.input(m)
		except Exception, e:
			log.exception(e)
	
	def on_timeout(self, controller):
		if self.controller == controller:
			self.controller = None
			log.debug("Timeout (3 seconds), disconnected.")
			self.daemon.remove_controller(controller)	

# Driver is process-wide singleton
_yoke_drv = None


def init(daemon, config):
	return True


def start(daemon):
	global _yoke_drv
	_yoke_drv = YokeDrv(daemon)
	daemon.add_on_exit(_yoke_drv.on_exit)
	# daemon.add_mainloop(_yoke_drv.mainloop)
