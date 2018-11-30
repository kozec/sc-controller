#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/mapper.h"
#include "scc/action.h"
#include "scc/parser.h"
#include "testmapper/testmapper.h"
#include <tgmath.h>
#include <string.h>
#include <stdlib.h>


/** Tests executing macro */
void test_macro(CuTest* tc) {
	ActionOE aoe = scc_parse_action("button(Keys.KEY_Q); button(KEY_W);button(KEY_E)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	
	testmapper_set_buttons(m, B_A);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));
	assert(tc, 1 == testmapper_get_key_count(m));
	
	while (testmapper_has_scheduled(m)) {
		testmapper_run_scheduled(m, 2);
		assert(tc, 0 == testmapper_get_key_count(m));
		if (!testmapper_has_scheduled(m))
			break;
		testmapper_run_scheduled(m, 2);
		assert(tc, 1 == testmapper_get_key_count(m));
	}
	
	assert(tc, 0 == strcmp("16, 17, 18", testmapper_get_keylog(m)));
	
	RC_REL(a);
	testmapper_free(m);
}


/** Tests macro with sleep time */
void test_sleep(CuTest* tc) {
	// 0.1 = 10ms = 10 ticks on test mapper
	ActionOE aoe = scc_parse_action("button(Keys.KEY_Q); sleep(0.1);button(KEY_E)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	
	testmapper_set_buttons(m, B_A);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));
	assert(tc, 1 == testmapper_get_key_count(m));
	
	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == testmapper_get_key_count(m));
	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));
	
	testmapper_run_scheduled(m, 8);
	assert(tc, 1 == testmapper_get_key_count(m));
	assert(tc, 0 == strcmp("16, 18", testmapper_get_keylog(m)));
	
	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == testmapper_get_key_count(m));
	RC_REL(a);
	
	// 0.1 + 0.2 = 20ms = 30 ticks on test mapper. Both should be merged
	// to single delay
	aoe = scc_parse_action("button(Keys.KEY_Q); sleep(0.2);sleep(0.1);button(KEY_E)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	a = ACTION(aoe);
	scc_action_compress(&a);
	
	testmapper_reset(m);

	testmapper_set_buttons(m, B_A);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));
	assert(tc, 1 == testmapper_get_key_count(m));

	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == testmapper_get_key_count(m));
	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));

	testmapper_run_scheduled(m, 8);
	assert(tc, 0 == testmapper_get_key_count(m));

	testmapper_run_scheduled(m, 20);
	assert(tc, 1 == testmapper_get_key_count(m));
	assert(tc, 0 == strcmp("16, 18", testmapper_get_keylog(m)));

	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == testmapper_get_key_count(m));
	RC_REL(a);
	
	testmapper_free(m);
}


/** Tests repeating macro  */
void test_repeat(CuTest* tc) {
	ActionOE aoe = scc_parse_action("repeat(button(Keys.KEY_Q))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	
	testmapper_set_buttons(m, B_A);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));
	for (int i=0; i<10; i++)
		testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("16, 16, 16, 16, 16, 16", testmapper_get_keylog(m)));
	
	a->button_release(a, m);
	for (int i=0; i<10; i++)
		testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("16, 16, 16, 16, 16, 16", testmapper_get_keylog(m)));
	
	RC_REL(a);
	testmapper_free(m);
}

int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	// DEFAULT_SUITE_ADD(test_macro);
	// DEFAULT_SUITE_ADD(test_sleep);
	DEFAULT_SUITE_ADD(test_repeat);
	
	return CuSuiteRunDefault();
}
