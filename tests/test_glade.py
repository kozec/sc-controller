import xml.etree.cElementTree as ET
import os

def _get_files():
	"""
	Generates list of all glade files in glade/ directory.
	"""
	# TODO: Caching, when there is more than one test using this
	rv = []
	def recursive(path):
		for f in os.listdir(path):
			filename = os.path.join(path, f)
			if os.path.isdir(filename):
				recursive(filename)
			elif filename.endswith(".glade"):
				rv.append(filename)
	
	recursive("glade/")
	return rv


def _check_ids(el, filename, parent_id):
	""" Recursively walks through tree and check if every object has ID """
	for child in el:
		if child.tag == "object":
			msg = "Widget has no ID in %s; class %s; Parent id: %s" % (
					filename,
					child.attrib['class'],
					parent_id
				)
			assert 'id' in child.attrib and child.attrib['id'], msg
			for subel in child:
				if subel.tag == "child":
					_check_ids(subel, filename, child.attrib['id'])

class TestGlade(object):
	"""
	Tests every glade file in glade/ directory (and subdirectories) for known
	problems that may cause GUI to crash in some environments.
	
	(one case on one environment so far)
	"""
	
	def test_every_widget_has_id(self):
		"""
		Tests if every defined widget has ID.
		Dummy widgets without ID are OK, in theory, but Ubuntu version
		of libglade crashes witht them :(
		"""
		for filename in _get_files():
			root = ET.parse(filename).getroot()
			_check_ids(root, filename, "<root element>")
