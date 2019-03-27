#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/bindings.h"
#include "scc/parser.h"
#include "scc/action.h"
#include <string.h>


/** Tests reference counting with DPadAction */
void test_dpad_rc(CuTest* tc) {
	ActionOE b = scc_action_new("button",
					scc_inline_param_list(scc_new_int_parameter(11)));
	assert_msg(tc, !IS_ACTION_ERROR(b), ACTION_ERROR(b)->message);
	assert(tc, b.action->_rc.count == 1);
	
	Parameter* pars[] = { scc_new_action_parameter(b.action) };
	assert(tc, b.action->_rc.count == 2);
	assert(tc, pars[0]->_rc.count == 1);
	
	ActionOE dpad = scc_action_new_from_array("dpad", 1, pars);
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

/** Tests case that caused segfault in past */
void test_parser_segfault(CuTest* tc) {
	const uint32_t AF_ERROR = 0b00000001;
	struct CActionOE {
		uint32_t	flags;
		size_t		ref_count;
	};
	
	struct CActionOE* a = (struct CActionOE*)scc_parse_action("reXeased(button(KEY_A))").action;
	assert(tc, (a->flags & AF_ERROR) != 0);
	assert(tc, 0 == strcmp("Unexpected 'reXeased'", scc_error_get_message((APError)(ActionError*)a)));
}

void test_better_segfault(CuTest* tc) {
	Action* a = scc_parse_action("sens(0.3, 1.3, hatright(ABS_X))").action;
	Parameter* pars[] = {
		scc_new_float_parameter(0.3f),
		scc_new_float_parameter(1.3f),
		scc_new_action_parameter(a)
	};
	assert(tc, pars[2]->_rc.count == 1);
	assert(tc, a->_rc.count == 2);
	
	Action* s = scc_action_new_from_array("sens", 3, pars).action;
	assert(tc, pars[2]->_rc.count == 2);
	assert(tc, a->_rc.count == 3);
	scc_action_unref(a);
	scc_parameter_unref(pars[0]);
	scc_parameter_unref(pars[1]);
	scc_parameter_unref(pars[2]);
	assert(tc, pars[2]->_rc.count == 1);
	assert(tc, a->_rc.count == 2);
	
	Action* c = scc_action_get_compressed(s);
	scc_action_unref(s);
	scc_action_to_string(c);
	scc_action_unref(c);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_parser_segfault);
	DEFAULT_SUITE_ADD(test_better_segfault);
	DEFAULT_SUITE_ADD(test_dpad_rc);
	return CuSuiteRunDefault();
}

