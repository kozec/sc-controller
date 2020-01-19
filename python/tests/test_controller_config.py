from scc.config import Config
import pytest, os, shutil


class TestControllerConfig(object):
	prefix = "/tmp/test_config_%i" % os.getpid()
	
	@classmethod
	def setup_class(cls):
		os.makedirs("%s/devices" % cls.prefix)
		file("%s/devices/test_empty.json" % cls.prefix, "w").write("{}")
		file("%s/devices/test_changeme.json" % cls.prefix, "w").write("{}")
		file("%s/devices/test.json" % cls.prefix, "w").write("""{
			"axes": { "1": { "axis": "stick_y", "deadzone": 2000, "max": -32768, "min": 32767 } },
			"buttons": { "305": "B", "307": "X", "308": "Y" },
			"dpads": {},
			
			"gui": {
				"icon": "test-01",
				"background": "psx",
				"buttons": ["A","B","X","Y","BACK","C","START","LB","RB","LT","RT","LG","RG"]
			}
		}""")
		filename = "%s.json" % (cls.prefix)
		cls.c = Config(filename)
		cls.c.set_prefix(cls.prefix)
	
	@classmethod
	def teardown_class(cls):
		shutil.rmtree(cls.prefix)
	
	def test_get_controllers(self):
		assert "test" in self.c.get_controllers()
	
	def test_defaults(self):
		""" Tests if defaults are provided to both daemon and gui-specific values """
		ccfg = self.c.get_controller_config("test_empty")
		assert len(list(ccfg["axes"])) == 0
		assert len(list(ccfg["buttons"])) == 0
		assert len(list(ccfg["dpads"])) == 0
		
		assert type(ccfg["input_rotation"]["right"]) is float
		assert type(ccfg["input_rotation/left"]) is float
		assert type(ccfg["idle_timeout"]) in (int, long)
		
		assert ccfg["gui"]["icon"] == ""
		assert ccfg["gui/icon"] == ""
		assert type(ccfg["gui/name"]) in (str, unicode)
		assert len(ccfg["gui"]["buttons"]) == 0
	
	def test_same_object(self):
		""" Tests that repeated requests to some types of key return same object """
		ccfg = self.c.get_controller_config("test")
		a = ccfg["gui"]
		assert ccfg["gui"] is ccfg["gui"]
		assert ccfg["gui"] is a
		
		b = a["buttons"]
		assert ccfg["gui"]["buttons"] is b
		a["buttons"] = ["A", "B"]
		assert ccfg["gui"]["buttons"] is not b
	
	def test_gui_related(self):
		""" Tests loading values typicaly used by GUI """
		gcfg = self.c.get_controller_config("test")["gui"]
		assert gcfg["background"] == "psx"
		assert gcfg["buttons"][1] == "B"
		assert gcfg["icon"] == "test-01"
	
	def test_get_invalid(self):
		""" Tests whether opening non-existing config fails """
		with pytest.raises(OSError):
			ccfg = self.c.get_controller_config("notexisting")
	
	def test_write_errors(self):
		""" Tests error that may arrise when writing stuff """
		ccfg = self.c.get_controller_config("test_changeme")
		# Setting non-string to strarray
		with pytest.raises(TypeError):
			ccfg["gui"]["buttons"] = ["X", "Y", 1, "A"]
		with pytest.raises(TypeError):
			ccfg["gui"]["buttons"] = ["X", True, "B", "A"]
	
	def test_write(self):
		""" Tests changing config values """
		ccfg = self.c.get_controller_config("test_changeme")
		ccfg["gui/icon"] = "icon1"
		ccfg["gui"]["buttons"] = ["X", "Y", "A", "B"]
		ccfg["gui"]["buttons"][1] = "C"
		ccfg["gui"]["buttons"].append("Z")
		ccfg.save()
		ccfg = self.c.get_controller_config("test_changeme")
		assert ccfg["gui"]["icon"] == "icon1"
		assert ccfg["gui"]["buttons"][1] == "C"
		assert ccfg["gui"]["buttons"][2] == "A"
	
	def test_create_config(self):
		with pytest.raises(OSError):
			self.c.get_controller_config("test_notexisting_create")
		ccfg = self.c.create_controller_config("test_notexisting_create")
		ccfg["gui/icon"] = "Changed"
		ccfg.save()
		del ccfg
		
		ccfg = self.c.get_controller_config("test_notexisting_create")
		assert ccfg["gui"]["icon"] == "Changed"
	
	def test_load_invalid(self):
		""" Tests loading file that's not json """
		file("%s/devices/test_notjson.json" % self.prefix, "w").write("X")
		with pytest.raises(OSError):
			ccfg = self.c.get_controller_config("test_notjson")
			print ccfg


if __name__ == "__main__":
	from scc.tools import init_logging, set_logging_level
	init_logging()
	set_logging_level(True, True)
	
	TestControllerConfig.setup_class()
	TestControllerConfig().test_load_invalid()
	TestControllerConfig.teardown_class()

