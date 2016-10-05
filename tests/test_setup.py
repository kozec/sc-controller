import scc
import os, pkgutil

class TestSetup(object):
	"""
	Tests if SCC should be installable.
	"""
	
	def test_packages(self):
		"""
		Tests if every known Action is documentated in docs/actions.md
		"""
		from setup import packages
		for importer, modname, ispkg in pkgutil.walk_packages(path=scc.__path__, prefix="scc.", onerror=lambda x: None):
			if ispkg:
				assert modname in packages, "Package '%s' is not being installed by setup.py" % (modname,)
