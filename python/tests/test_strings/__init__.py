from scc.parser import ActionParser
from scc.actions import Action
import sys

parser = ActionParser()

def _parses_as(a_str, action):
	"""
	Tests if action parsed from string equals specified action.
	
	Done by parsing string to Action and comparing it using _same_action()
	"""
	parsed = parser.restart(a_str).parse()
	assert _same_action(parsed, action)
	return True


def _same_action(a1, a2):
	"""
	Tests if two actions are the same.
	Done only by comparing .to_string() output.
	"""
	assert a1.to_string() == a2.to_string()
	return True
