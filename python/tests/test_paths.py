from scc.paths import *

class TestPaths(object):
	
	def test_stuff(self):
		"""
		Just ensures that all path-related functions are returning
		_some_ meaningful value
		"""
		assert len(get_config_path()) > 1
		assert len(get_profiles_path()) > 1
		assert len(get_menus_path()) > 1
		assert len(get_share_path()) > 1
		assert len(get_default_menus_path()) > 1
		assert len(get_controller_icons_path()) > 1
		assert len(get_default_controller_icons_path()) > 1

