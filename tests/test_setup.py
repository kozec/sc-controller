import scc
import pkgutil

class TestSetup(object):
	"""
	Tests if SCC should be installable.
	"""
	
	def test_packages(self):
		"""
		Tests if every known Action is documentated in docs/actions.md
		"""
		try:
			import gi
			gi.require_version('Gtk', '3.0') 
			gi.require_version('GdkX11', '3.0') 
			gi.require_version('Rsvg', '2.0') 
		except ImportError:
			pass
		
		from setup import packages
		for importer, modname, ispkg in pkgutil.walk_packages(path=scc.__path__, prefix="scc.", onerror=lambda x: None):
			if ispkg:
				assert modname in packages, "Package '%s' is not being installed by setup.py" % (modname,)
