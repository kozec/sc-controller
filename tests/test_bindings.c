#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/bindings.h"
#include "scc/action.h"


/** Tests reference counting with DPadAction */
void test_dpad_rc(CuTest* tc) {
	ActionOE b = scc_action_new("button",
					scc_inline_param_list(scc_new_int_parameter(11)));
	assert_msg(tc, !IS_ACTION_ERROR(b), ACTION_ERROR(b)->message);
	assert(tc, b.action->_rc.count == 1);
	
	Parameter* pars[] = { scc_new_action_parameter(b.action) };
	assert(tc, b.action->_rc.count == 2);
	assert(tc, pars[0]->_rc.count == 1);
	
	ActionOE dpad = scc_action_new_from_array("dpad", pars, 1);
	assert_msg(tc, !IS_ACTION_ERROR(dpad), ACTION_ERROR(dpad)->message);
	assert(tc, dpad.action->_rc.count == 1);
	assert(tc, b.action->_rc.count == 3);
	assert(tc, pars[0]->_rc.count == 1);
	
	scc_parameter_unref(pars[0]);
	assert(tc, b.action->_rc.count == 2);
	
	// dpad_to_string was losing references in past
	scc_action_to_string(dpad.action);
	assert(tc, b.action->_rc.count == 2);
	assert(tc, dpad.action->_rc.count == 1);
	
	scc_action_unref(dpad.action);
	assert(tc, b.action->_rc.count == 1);
	scc_action_unref(b.action);
}

int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_dpad_rc);
	
	return CuSuiteRunDefault();
}

