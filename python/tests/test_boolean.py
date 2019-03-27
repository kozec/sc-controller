from scc.actions import ButtonAction, NoAction

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
		a = ButtonAction(11)
		assert a
		if a:
			return
		raise Exception("Action is False :(")


if __name__ == "__main__":
	TestBoolean().test_noaction_is_false()
	TestBoolean().test_action_is_true()

