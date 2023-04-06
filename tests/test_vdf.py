from scc.lib.vdf import parse_vdf
from scc.foreign.vdf import VDFProfile
from io import StringIO
import os, pytest

class TestVDF(object):
	""" Tests VDF parser """
	
	def test_parsing(self):
		""" Tests if VDF parser parses VDF """
		sio = StringIO("""
		"data"
		{
			"version" "3"
			"more data" {
				"version" "7"
			}
		}
		""")
		parsed = parse_vdf(sio)
		assert type(parsed["data"]) == dict
		assert parsed["data"]["version"] == "3"
		assert parsed["data"]["more data"]["version"] == "7"
	
	
	def test_dict_without_key(self):
		"""
		Tests if VDF parser throws exception when there is dict with key missing
		"""
		sio = StringIO("""
		"data"
		{
			"version" "3"
			{
				"version" "7"
			}
		}
		""")
		with pytest.raises(ValueError) as excinfo:
			parsed = parse_vdf(sio)
	
	
	def test_unclosed_bracket(self):
		"""
		Tests if VDF parser throws exception when there is unclosed {
		"""
		sio = StringIO("""
		"data"
		{
			"version" "3"
			"more data" {
				"version" "7"
			}
		""")
		with pytest.raises(ValueError) as excinfo:
			parsed = parse_vdf(sio)
	
	
	def test_too_many_brackets(self):
		"""
		Tests if VDF parser throws exception when there is } wihtout matching {
		"""
		sio = StringIO("""
		"data"
		{
			"version" "3"
			"more data" {
				"version" "7"
			}
			}
		}
		""")
		with pytest.raises(ValueError) as excinfo:
			parsed = parse_vdf(sio)
	
	
	def test_import(self):
		"""
		Tests if every *.vdf file in tests/vdfs can be imported.
		"""
		path = "tests/vdfs"
		for f in os.listdir(path):
			filename = os.path.join(path, f)
			print("Testing import of '%s'" % (filename,))
			VDFProfile().load(filename)
