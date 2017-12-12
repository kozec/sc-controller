#!/usr/bin/env python2
from scc.constants import HapticPos
import logging

log = logging.getLogger("SCController")

next_id = 1		# Used with fallback controller id generator

class Controller(object):
	"""
	Base class for all controller drivers. Implementations are in
	scc.drivers package.
	
	Derived class should implement every method from here.
	"""
	flags = 0
	
	def __init__(self):
		global next_id
		self.mapper = None
		self._id = next_id
		next_id += 1
	
	
	def get_type(self):
		"""
		This method has to return type identifier - short string without spaces
		that describes type of controller which should be unique for each
		driver.
		String is used by UI to assign icons and, along with ID,
		to store controller settings.
		
		This method has to be overriden.
		"""
		raise RuntimeError("Controller.get_type not overriden")
	
	
	def get_id(self):
		"""
		Returns identifier that has to be unique at least until daemon
		is restarted, ideally derived from HW device serial number.
		"""
		return self._id
	
	
	def get_gui_config_file(self):
		"""
		Returns file name of json file that GUI can use to load more data about
		controller (background image, button images, available buttons and
		axes, etc...) File name may be absolute path or just name of file in
		/usr/share/scc
		
		Returns None if there is no configuration file (GUI will use
		defaults in such case)
		"""
		return None
	
	
	def set_mapper(self, mapper):
		""" Sets mapper for controller """
		self.mapper = mapper
	
	
	def get_mapper(self):
		""" Returns mapper set for controller """
		return self.mapper
	
	
	def apply_config(self, config):
		"""
		Called from daemon to apply controller configuration stored
		in config file.
		
		Does nothing by default.
		"""
		pass
	
	
	def set_led_level(self, level):
		"""
		Configures LED intensity, if supported.
		'level' goes from 0.0 to 100.0
		"""
		pass
	
	
	def set_gyro_enabled(self, enabled):
		""" Enables or disables gyroscope, if supported """
		pass
	
	
	def get_gyro_enabled(self):
		""" Returns True if gyroscope is enabled """
		return False
	
	
	def feedback(self, data):
		"""
		Generates feedback effect, if supported.
		'data' is HapticData instance.
		"""
		pass
	
	
	def turnoff(self):
		""" Turns off controller, if supported """
		pass
	
	
	def disconnected(self):
		""" Called from daemon after controller is disconnected """
		pass
	

class HapticData(object):
	""" Simple container to hold haptic feedback settings """
	
	def __init__(self, position, amplitude=512, frequency=4, period=1024, count=1):
		"""
		'frequency' is used only when emulating touchpad and describes how many
		pixels should mouse travell between two feedback ticks.
		"""
		data = tuple([ int(x) for x in (position, amplitude, period, count) ])
		if data[0] not in (HapticPos.LEFT, HapticPos.RIGHT, HapticPos.BOTH):
			raise ValueError("Invalid position")
		for i in (1,2,3):
			if data[i] > 0x8000 or data[i] < 0:
				raise ValueError("Value out of range")
		# frequency is multiplied by 1000 just so I don't have big numbers everywhere;
		# it's float until here, so user still can make pad squeak if he wish
		frequency = int(max(1.0, frequency * 1000.0))
		
		self.data = data				# send to controller
		self.frequency = frequency		# used internally
	
	
	def with_position(self, position):
		""" Creates copy of HapticData with position value changed """
		trash, amplitude, period, count = self.data
		return HapticData(position, amplitude, self.frequency, period, count)
	
	
	def get_position(self):
		return HapticPos(self.data[0])
	
	def get_amplitude(self):
		return self.data[1]
	
	def get_frequency(self):
		return float(self.frequency) / 1000.0
	
	def get_period(self):
		return self.data[2]
	
	def get_count(self):
		return self.data[3]
	
	def __mul__(self, by):
		"""
		Allows multiplying HapticData by scalar to get same values
		with increased amplitude.
		"""
		position, amplitude, period, count = self.data
		amplitude = min(amplitude * by, 0x8000)
		return HapticData(position, amplitude, self.frequency, period, count)
