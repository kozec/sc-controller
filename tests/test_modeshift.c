#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/mapper.h"
#include "scc/action.h"
#include "scc/parser.h"
#include "testmapper/testmapper.h"
#include <tgmath.h>
#include <string.h>
#include <stdlib.h>


/** Tests parsing of modeshift */
void test_parsing(CuTest* tc) {
	ActionOE aoe = scc_parse_action("mode(A, button(Keys.KEY_Q), X, button(KEY_W), C, button(KEY_A))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);	// should be OK
	RC_REL(aoe.action);
	
	aoe = scc_parse_action("mode('A', button(Keys.KEY_Q), X, button(KEY_W), C, button(KEY_A))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);	// As above, but uses string instead of const
	RC_REL(aoe.action);
	
	aoe = scc_parse_action("mode(button(Keys.KEY_Q), X, button(KEY_W), C, button(KEY_A))");
	assert(tc, strstr(ACTION_ERROR(aoe)->message, "as button/condition") != NULL);	// 1st param. is not a button name
	RC_REL(aoe.action);

	aoe = scc_parse_action("KEY_A, mode(button(Keys.KEY_Q), X, button(KEY_W), C, button(KEY_A))");
	assert(tc, strstr(ACTION_ERROR(aoe)->message, "Unexpected") != NULL);	// syntax error
	RC_REL(aoe.action);
	
	aoe = scc_parse_action("mode(A, button(Keys.KEY_Q), button(KEY_W), C, button(KEY_A))");
	assert(tc, strstr(ACTION_ERROR(aoe)->message, "as button/condition") != NULL);	// random param. is not a button name
	RC_REL(aoe.action);
	
	aoe = scc_parse_action("mode(A, button(Keys.KEY_Q), X, button(KEY_W), button(KEY_A))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);	// Last param that's not a button is used as default instead
	RC_REL(aoe.action);
	
	aoe = scc_parse_action("mode(A, button(Keys.KEY_Q), X, button(KEY_W), C)");
	assert(tc, strstr(ACTION_ERROR(aoe)->message, "after last parameter") != NULL);	// Last is button name, action is missing
	RC_REL(aoe.action);
	
	aoe = scc_parse_action("mode(A, button(Keys.KEY_Q), RT >= 0.21, button(KEY_W))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);	// should be OK, contains range
}


/** Test modeshift bound on button */
void test_button(CuTest* tc) {
	ActionOE aoe = scc_parse_action("mode(A, button(Keys.KEY_Q), X, button(KEY_W), button(KEY_A))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Action* a = ACTION(aoe);
	Mapper* m = testmapper_new();
	scc_action_compress(&a);
	
	// Default action (no button pressed)
	a->button_press(a, m); a->button_release(a, m);
	assert(tc, 0 == strcmp("30", testmapper_get_keylog(m)));
	
	// 'A' is being held
	testmapper_set_buttons(m, B_A);
	a->button_press(a, m); a->button_release(a, m);
	assert(tc, 0 == strcmp("30, 16", testmapper_get_keylog(m)));

	// 'A' and 'X' is being held
	testmapper_set_buttons(m, B_A | B_X);
	a->button_press(a, m); a->button_release(a, m);
	assert(tc, 0 == strcmp("30, 16, 16", testmapper_get_keylog(m)));
	
	// 'X' being held
	testmapper_set_buttons(m, B_X);
	a->button_press(a, m); a->button_release(a, m);
	assert(tc, 0 == strcmp("30, 16, 16, 17", testmapper_get_keylog(m)));
	
	RC_REL(a);
}


/** Test modeshift bound on stick */
void test_stick(CuTest* tc) {
	ActionOE aoe = scc_parse_action("mode(A, XY(axis(ABS_X), axis(ABS_Y)), Y, XY(axis(ABS_Z), axis(ABS_RZ)))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Action* a = ACTION(aoe);
	Mapper* m = testmapper_new();
	scc_action_compress(&a);
	
	// There is no default action, so this should do nothing
	a->whole(a, m, 10, 3000, PST_STICK);
	assert(tc, (testmapper_get_axis_position(m, ABS_X) == 0)
			&& (testmapper_get_axis_position(m, ABS_Y) == 0));
	
	testmapper_set_buttons(m, B_A);
	a->whole(a, m, 10000, 200, PST_STICK);
	assert(tc, (testmapper_get_axis_position(m, ABS_X) == 10000)
			&& (testmapper_get_axis_position(m, ABS_Y) == 200));
	
	testmapper_set_buttons(m, B_Y);
	a->whole(a, m, 10000, 200, PST_STICK);
	assert(tc, (testmapper_get_axis_position(m, ABS_X) == 0)
			&& (testmapper_get_axis_position(m, ABS_Y) == 0));
	assert(tc, (testmapper_get_axis_position(m, ABS_Z) == 166)
			&& (testmapper_get_axis_position(m, ABS_RZ) == 128));
	
	RC_REL(a);
}



int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_parsing);
	DEFAULT_SUITE_ADD(test_button);
	DEFAULT_SUITE_ADD(test_stick);
	// TODO: Test for trigger
	
	return CuSuiteRunDefault();
}
