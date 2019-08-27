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

/** Tests executing 'type' macro */
void test_type(CuTest* tc) {
	ActionOE aoe = scc_parse_action("type('idD 78  QD')");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	// printf("%s\n", scc_action_to_string(a));
	
	a->button_press(a, m);
	
	assert(tc, 0 == strcmp("23", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 2); testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("23, 32", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == testmapper_get_key_count(m));
	
	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("23, 32, 42, 32", testmapper_get_keylog(m)));
	assert(tc, 2 == testmapper_get_key_count(m));
	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == testmapper_get_key_count(m));

	testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("23, 32, 42, 32, 57", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 2); testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("23, 32, 42, 32, 57, 8", testmapper_get_keylog(m)));
	
	while (testmapper_has_scheduled(m))
		testmapper_run_scheduled(m, 2);
	
	assert(tc, 0 == strcmp("23, 32, 42, 32, 57, 8, 9, 57, 57, 42, 16, 42, 32", testmapper_get_keylog(m)));
	
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

/** Tests cycling */
void test_cycle(CuTest* tc) {
	ActionOE aoe = scc_parse_action("cycle(button(Keys.KEY_Q), button(Keys.KEY_W), button(Keys.KEY_E))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	assert(tc, 0 == strcmp("cycle(button(KEY_Q), button(KEY_W), button(KEY_E))",
						scc_action_to_string(ACTION(aoe))));
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	
	a->button_press(a, m);
	a->button_release(a, m);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));
	
	a->button_press(a, m);
	a->button_release(a, m);
	a->button_press(a, m);
	a->button_release(a, m);
	assert(tc, 0 == strcmp("16, 17, 18", testmapper_get_keylog(m)));
	
	a->button_press(a, m);
	a->button_release(a, m);
	assert(tc, 0 == strcmp("16, 17, 18, 16", testmapper_get_keylog(m)));
	
	RC_REL(a);
	testmapper_free(m);
}

/** Tests multiaction ("and")  */
void test_multiaction(CuTest* tc) {
	ActionOE aoe = scc_parse_action("button(Keys.KEY_LEFTSHIFT)    and button(KEY_RIGHTCTRL) and button(KEY_E)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	assert(tc, 0 == strcmp("button(KEY_LEFTSHIFT) and button(KEY_RIGHTCTRL) and button(KEY_E)",
						scc_action_to_string(ACTION(aoe))));
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	
	a->button_press(a, m);
	assert(tc, 0 == strcmp("42, 97, 18", testmapper_get_keylog(m)));
	assert(tc, testmapper_get_key_count(m) == 3);
	a->button_release(a, m);
	assert(tc, testmapper_get_key_count(m) == 0);
	testmapper_reset(m);
	RC_REL(a);
	
	aoe = scc_parse_action("XY(None, axis(ABS_Z)) and XY(axis(ABS_Y), raxis(ABS_X))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	testmapper_set_buttons(m, B_RPADTOUCH);
	a->whole(a, m, 1500, 20199, PST_RPAD);
	
	assert(tc, testmapper_get_axis_position(m, ABS_X) == -20200);
	assert(tc, testmapper_get_axis_position(m, ABS_Y) == 1500);
	assert(tc, testmapper_get_axis_position(m, ABS_Z) != 0);

	testmapper_free(m);
}

/** Tests press & release combinations */
void test_press_release(CuTest* tc) {
	ActionOE aoe = scc_parse_action("press(button(Keys.KEY_Q)); button(KEY_W);release(KEY_M); release(KEY_Q)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	
	a->button_press(a, m);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 2); testmapper_run_scheduled(m, 2);		// release Q & press W
	
	assert(tc, 0 == strcmp("16, 17", testmapper_get_keylog(m)));
	assert(tc, testmapper_get_key_count(m) == 2);
	testmapper_run_scheduled(m, 2);										// release W
	assert(tc, testmapper_get_key_count(m) == 1);
	
	// This step releases 'M', which was not pressed
	testmapper_run_scheduled(m, 2); testmapper_run_scheduled(m, 2);		// press M & release M
	assert(tc, 0 == strcmp("16, 17", testmapper_get_keylog(m)));
	assert(tc, testmapper_get_key_count(m) == 1);
	
	// Last step releases 'Q' key
	testmapper_run_scheduled(m, 2);										// press Q
	assert(tc, testmapper_get_key_count(m) == 1);
	testmapper_run_scheduled(m, 2);										// release Q
	assert(tc, 0 == strcmp("16, 17", testmapper_get_keylog(m)));
	assert(tc, testmapper_get_key_count(m) == 0);
	
	RC_REL(a);
	testmapper_free(m);
}


/** Tests 'tap' */
void test_tap(CuTest* tc) {
	ActionOE aoe = scc_parse_action("tap(Keys.KEY_Q)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	assert(tc, 0 == strcmp("tap(KEY_Q)", scc_action_to_string(ACTION(aoe))));

	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	
	// Simple tap
	a->button_press(a, m);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));
	assert(tc, testmapper_get_key_count(m) == 1);
	while (testmapper_has_scheduled(m))
		testmapper_run_scheduled(m, 2);
	assert(tc, !m->is_virtual_key_pressed(m, KEY_Q));
	assert(tc, testmapper_get_key_count(m) == 0);
	a->button_release(a, m);
	assert(tc, testmapper_get_key_count(m) == 0);
	
	// Tap when target button is already pressed
	testmapper_reset(m);
	m->key_press(m, KEY_Q, false);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("16, 16", testmapper_get_keylog(m)));
	assert(tc, testmapper_get_key_count(m) == 1);
	while (testmapper_has_scheduled(m))
		testmapper_run_scheduled(m, 2);
	a->button_release(a, m);
	assert(tc, m->is_virtual_key_pressed(m, KEY_Q));
	assert(tc, testmapper_get_key_count(m) == 1);
	RC_REL(a);
	
	// Tap that taps multiple times
	aoe = scc_parse_action("tap(Keys.KEY_Q, 5)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	assert(tc, 0 == strcmp("tap(KEY_Q, 5)", scc_action_to_string(ACTION(aoe))));
	a = ACTION(aoe);
	scc_action_compress(&a);
	
	// ... while button is not pressed
	testmapper_reset(m);
	assert(tc, testmapper_get_key_count(m) == 0);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("16", testmapper_get_keylog(m)));
	assert(tc, testmapper_has_scheduled(m));
	testmapper_run_scheduled(m, 2);
	assert(tc, testmapper_get_key_count(m) == 0);
	testmapper_run_scheduled(m, 2);
	assert(tc, testmapper_get_key_count(m) == 1);
	assert(tc, 0 == strcmp("16, 16", testmapper_get_keylog(m)));

	while (testmapper_has_scheduled(m))
		testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("16, 16, 16, 16, 16", testmapper_get_keylog(m)));
	assert(tc, testmapper_get_key_count(m) == 0);
	
	// ... while button _is_ pressed
	testmapper_reset(m);
	m->key_press(m, KEY_Q, false);
	a->button_press(a, m);
	assert(tc, testmapper_get_key_count(m) == 1);
	assert(tc, 0 == strcmp("16, 16", testmapper_get_keylog(m)));
	while (testmapper_has_scheduled(m))
		testmapper_run_scheduled(m, 2);
	assert(tc, 0 == strcmp("16, 16, 16, 16, 16, 16", testmapper_get_keylog(m)));
	assert(tc, testmapper_get_key_count(m) == 1);
	assert(tc, m->is_virtual_key_pressed(m, KEY_Q));
	
	// printf("[%lu] %s\n", testmapper_get_key_count(m), testmapper_get_keylog(m));
	RC_REL(a);
	testmapper_free(m);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_macro);
	DEFAULT_SUITE_ADD(test_type);
	DEFAULT_SUITE_ADD(test_sleep);
	DEFAULT_SUITE_ADD(test_repeat);
	DEFAULT_SUITE_ADD(test_cycle);
	DEFAULT_SUITE_ADD(test_multiaction);
	DEFAULT_SUITE_ADD(test_press_release);
	DEFAULT_SUITE_ADD(test_tap);
	
	return CuSuiteRunDefault();
}
