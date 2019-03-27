from scc.parser import ActionParser

parser = ActionParser()

def _parses_as_itself(action):
	"""
	Tests if provided action can be converted to string and
	parsed back to same action.
	"""
	# Simple
	a_str = action.to_string()
	assert parser.restart(a_str).parse().to_string() == a_str
	# Multiline
	m_str = action.to_string(True)
	assert parser.restart(m_str).parse().to_string() == a_str
	return True

def _parse_compressed(a_str):
	return parser.restart(a_str).parse().compress()

