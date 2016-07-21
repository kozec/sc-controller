from scc.actions import Action, NoAction

class TestBoolean(object):
	
	def test_noaction_is_false(self):
		"""
		Tests if None can be used as False boolean value.
		"""
		assert not NoAction()
		if NoAction():
			raise Exception("NoAction is True :(")
	
	
	def test_action_is_true(self):
		"""
		Tests if random action works as True boolean value.
		"""
		a = Action()
		assert a
		if a:
			return
		raise Exception("Action is False :(")

