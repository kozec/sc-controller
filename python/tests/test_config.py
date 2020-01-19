from scc.config import Config
import os, platform


class TestConfig(object):
	
	@staticmethod
	def setup_class(cls):
		if platform.system() == "Windows":
			filename = "Software\\SCController-test-%s" % os.getpid()
		else:
			filename = "/tmp/test_config_%i.json" % os.getpid()
		cls.c = Config(filename)
	
	def test_invalid(self):
		""" Tests loading non-existing keys """
		try:
			self.c.get("invalid/key")
			assert False
		except KeyError:
			pass
		try:
			self.c["invalid/key"]
			assert False
		except KeyError:
			pass
		try:
			self.c["invalid"]["key"]
			assert False
		except KeyError:
			pass
		assert "nonexisting" not in self.c
	
	def X_test_defaults(self):
		"""
		Tests loading default values
		"""
		assert self.c.get("gui/news/last_version")
		assert 10 == self.c.get("recent_max")
		assert 0.95 == self.c["windows_opacity"]
		assert False == self.c["gui/enable_status_icon"]
		assert "Reloaded.gtkstyle.css" == self.c["osd_style"]
		assert unicode == type(self.c["osd_style"])
		assert "gui/enable_status_icon" in self.c
	
	def test_bool(self):
		""" Tests weirdness of booleans """
		self.c["new_bool"] = True
		assert self.c["new_bool"]
		assert self.c["new_bool"] is not True
		
		self.c["new_false"] = False
		assert not self.c["new_false"]
		assert self.c["new_false"] is not False
		
		self.c["gui/enable_status_icon"] = True
		assert self.c["gui/enable_status_icon"]
		assert self.c["gui/enable_status_icon"] is True
		self.c["gui/enable_status_icon"] = False
		assert self.c["gui/enable_status_icon"] is False
	
	def X_test_set(self):
		""" Tests setting values """
		self.c.set("test/string", "Hello")
		self.c.set("test/int", 112)
		self.c.set("test/long", 112L)
		self.c["test/double"] = 1.12
		self.c["test/bool"] = True
		
		assert "Hello" == self.c["test/string"]
		assert "Hello" == self.c["test"]["string"]
		assert 112 == self.c["test/int"]
		assert 112 == self.c["test"]["int"]
		assert 112 == self.c["test/long"]
		assert 1.12 == self.c["test/double"]
		assert self.c["test/bool"]
	
	def test_invalid_types(self):
		""" Test situations that sould fail as they sets wrong type to known key """
		def should_fail(key, value):
			try:
				self.c.set(key, value)
			except TypeError:
				return
			assert False
		
		should_fail("recent_max", "not-an-int")
		should_fail("gui/news/enabled", "not-a-bool")
		should_fail("windows_opacity", "not-double")
		should_fail("osd_style", 12)	# Not sting
	
	def test_valid_types(self):
		""" Tests setting types that are close enough, such as int to double """
		self.c["windows_opacity"] = 4
		self.c.save()
		assert self.c["windows_opacity"] == 4.0
		self.c["recent_max"] = 3.2
		assert self.c["recent_max"] == 3

if __name__ == "__main__":
	from scc.tools import init_logging, set_logging_level
	init_logging()
	set_logging_level(True, True)
	
	TestConfig.setup_class(TestConfig)
	TestConfig().test_invalid_types()

