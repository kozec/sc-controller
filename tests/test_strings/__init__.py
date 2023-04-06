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
	Done by comparing .parameters list and .to_string() output.
	"""
	assert len(a1.parameters) == len(a2.parameters)
	for i in range(0, len(a1.parameters)):
		if isinstance(a1.parameters[i], Action):
			assert isinstance(a2.parameters[i], Action), "Parameter missmatch"
			assert _same_action(a1.parameters[i], a2.parameters[i])
		else:
			assert a1.parameters[i] == a2.parameters[i], "Parameter missmatch"
	assert a1.to_string() == a2.to_string()
	return True
