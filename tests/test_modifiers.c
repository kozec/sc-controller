#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/mapper.h"
#include "scc/action.h"
#include "scc/parser.h"
#include "testmapper/testmapper.h"
#include <tgmath.h>
#include <string.h>
#include <stdlib.h>

#define IS_AROUND(x, y) ( ((x) > (y) - 0.1) && ((x) < (y) + 0.1) )


void test_sensitivity_mouse(CuTest* tc) {
	ActionOE aoe = scc_parse_action("sens(0.2, 0.85, mouse)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	assert(tc, 0 == strcmp("mouse", a->type));
	
	testmapper_set_buttons(m, B_RPADTOUCH);
	a->whole(a, m, 0, 0, PST_RPAD);
	testmapper_set_buttons(m, B_RPADTOUCH);
	a->whole(a, m, 10, -100, PST_RPAD);
	
	double x, y;
	testmapper_get_mouse_position(m, &x, &y);
	assert(tc, IS_AROUND(x, 0.2 * 10.0));
	assert(tc, IS_AROUND(y, 0.85 * -100.0));
	
	RC_REL(a);
	testmapper_free(m);
}

void test_sensitivity_axis(CuTest* tc) {
	// also tests passing sensitivity through 'xy'
	ActionOE aoe = scc_parse_action("sens(0.2, 0.3, XY(axis(ABS_X), axis(ABS_Y)))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	assert(tc, 0 == strcmp("XY", a->type));
	
	testmapper_set_buttons(m, B_RPADTOUCH);
	a->whole(a, m, 0, 0, PST_RPAD);
	testmapper_set_buttons(m, B_RPADTOUCH);
	a->whole(a, m, 10, -100, PST_RPAD);
	
	assert(tc, testmapper_get_axis_position(m, ABS_X) == (int)(10.0 * 0.2));
	assert(tc, testmapper_get_axis_position(m, ABS_Y) == (int)(-100.0 * 0.3));
	
	RC_REL(a);
	testmapper_free(m);
}

void test_deadzone(CuTest* tc) {
	// also tests passing sensitivity through 'xy'
	ActionOE aoe = scc_parse_action("deadzone(\"ABC\", 200, XY(axis(ABS_X), axis(ABS_Y)))");
	assert(tc, IS_ACTION_ERROR(aoe));
	RC_REL(ACTION_ERROR(aoe));
	
	#define MODES_CNT	4
	#define INPUT_CNT	5
	char* modes[MODES_CNT] = { "CUT", "ROUND", "LINEAR", "MINIMUM" };
	AxisValue inputs[INPUT_CNT][2] = { {100, 45}, {199, 95}, {200, 45}, {7000, 45}, {0x7000, 45} };
	AxisValue results[MODES_CNT][INPUT_CNT][2] = {
		// Following numbers are computed for same inputs by original python code
		{ // CUT
			{ 0, 0 },				// 100, 45
			{ 199, 95 },			// 199, 95
			{ 200, 45 },			// 200, 45
			{ 0, 0 },				// 7000, 45
			{ 0, 0 },				// 0x7000, 45
		},
		{ // ROUND
			{ 0, 0 },				// 100, 45
			{ 199, 95 },			// 199, 95
			{ 200, 45 },			// 200, 45
			{ 32766, 210 },			// 7000, 45
			{ 32766, 51 },			// 0x7000, 45
		},
		{ // LINEAR
			{ 0, 0 },				// 100, 45
			{ 123, 58 },			// 199, 95
			{ 33, 7 },				// 200, 45
			{ 32766, 210 },			// 7000, 45
			{ 32766, 51 },			// 0x7000, 45
		},
		{ // MINIMUM
			{ 197, 88 },			// 100, 45
			{ 209, 100 },			// 199, 95
			{ 224, 50 },			// 200, 45
			{ 1225, 7 },			// 7000, 45
			{ 4400, 6 },			// 0x7000, 45
		},
	};
	
	Mapper* m = testmapper_new();
	testmapper_set_buttons(m, B_RPADTOUCH);
	for (int i=0; i<MODES_CNT; i++) {
		char buffer[1024];
		snprintf(buffer, 1024, "deadzone(%s, 200, 5000, XY(axis(ABS_X), axis(ABS_Y)))", modes[i]);
		aoe = scc_parse_action(buffer);
		assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
		Action* a = ACTION(aoe);
		
		for (int j=0; j<INPUT_CNT; j++) {
			a->whole(a, m, inputs[j][0], inputs[j][1], PST_RPAD);
			AxisValue x = testmapper_get_axis_position(m, ABS_X);
			AxisValue y = testmapper_get_axis_position(m, ABS_Y);
			snprintf(buffer, 1024,
				"For mode %s, input %i,%i: Expected %i,%i got %i,%i",
				modes[i],
				inputs[j][0], inputs[j][1],
				results[i][j][0], results[i][j][1],
				x, y
			);
			assert_msg(tc, (x == results[i][j][0]) && (y == results[i][j][1]), buffer);
			// printf("%s\n", buffer);
			testmapper_reset(m);
		}
		
		RC_REL(a);
	}
	
	testmapper_free(m);
}

/** Tests 'hold' modifier */
void test_hold(CuTest* tc) {
	ActionOE aoe = scc_parse_action("hold(button(KEY_X), button(KEY_Z), 0.45)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	
	// Here, physical button is pressed, causing virtual button to be pressed
	// once it's held long enough
	a->button_press(a, m);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 200);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 300);
	assert(tc, 0 == strcmp("45", testmapper_get_keylog(m)));
	assert(tc, 1 == testmapper_get_key_count(m));
	testmapper_run_scheduled(m, 300);
	// Virtual button should still be pressed and should stay like that until
	// physical button is released
	assert(tc, 1 == testmapper_get_key_count(m));
	a->button_release(a, m);
	assert(tc, 0 == testmapper_get_key_count(m));
	assert(tc, 0 == strcmp("45", testmapper_get_keylog(m)));
	
	// Next, physical button is pressed, but released too soon, so 'default'
	// action will be executed briefly
	testmapper_reset(m);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 200);
	a->button_release(a, m);
	// Default button should be pressed for 1ms and released automatically
	assert(tc, 1 == testmapper_get_key_count(m));
	assert(tc, 0 == strcmp("44", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 1);
	assert(tc, 0 == testmapper_get_key_count(m));
	
	RC_REL(ACTION_ERROR(aoe));
}

/** Tests 'doubleclick' modifier */
void test_doubleclick(CuTest* tc) {
	ActionOE aoe = scc_parse_action("doubleclick(button(KEY_X), button(KEY_Z), 0.3)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	
	Mapper* m = testmapper_new();
	Action* a = ACTION(aoe);
	
	// Pressing physical button just once and holding it down until time
	// runs out with doubleclick modifier shoud execute 'default' action
	// once time runs out.
	a->button_press(a, m);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 200);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 150);
	assert(tc, 0 == strcmp("44", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 200);
	assert(tc, 1 == testmapper_get_key_count(m));
	// 'default' button should be released only now
	a->button_release(a, m);
	assert(tc, 0 == testmapper_get_key_count(m));
	
	// Pressing physical button just once and releasing it right away should
	// execute 'default' action action as well, but just for a short moment.
	testmapper_reset(m);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 100);
	a->button_release(a, m);
	testmapper_run_scheduled(m, 201);
	assert(tc, 1 == testmapper_get_key_count(m));
	testmapper_run_scheduled(m, 1);
	assert(tc, 0 == testmapper_get_key_count(m));
	
	// And finally, double clicking should work as well
	testmapper_reset(m);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 50);
	a->button_release(a, m);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 50);
	a->button_press(a, m);
	assert(tc, 1 == testmapper_get_key_count(m));
	// buttom pressed by double-click should be released only when physical button is
	testmapper_run_scheduled(m, 500);
	assert(tc, 1 == testmapper_get_key_count(m));
	a->button_release(a, m);
	assert(tc, 0 == testmapper_get_key_count(m));
}

/**
 * Compares two parameters, returns true if both are equal.
 * _additionally_, releases one reference from both p1 and p2
 */
static bool compare_paramteters(Parameter* p1, Parameter* p2) {
	if (p1 == NULL) {
		if (p2 == NULL) return true;
		RC_REL(p2);
		return false;
	}
	if (p2 == NULL) {
		if (p1 == NULL) return true;
		RC_REL(p1);
		return false;
	}
	char* s1 = scc_parameter_to_string(p1);
	char* s2 = scc_parameter_to_string(p2);
	bool rv = strcmp(s1, s2) == 0;
	if (!rv)
		printf(">> '%s' '%s'\n", s1, s2);
	free(s1); free(s2);
	RC_REL(p1); RC_REL(p2);
	
	return rv;
}

/** Tests 'hold' and 'doubleclick' used together */
void test_hold_doubleclick(CuTest* tc) {
	// Basically, all of following should be equivalent once compress is called
	ActionOE aoe1 = scc_parse_action("hold(button(KEY_A), doubleclick(button(KEY_X), button(KEY_Z), 0.3))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe1), ACTION_ERROR(aoe1)->message);
	ActionOE aoe2 = scc_parse_action("hold(button(KEY_A), doubleclick(button(KEY_X), button(KEY_Z)), 0.3)");
	assert_msg(tc, !IS_ACTION_ERROR(aoe2), ACTION_ERROR(aoe2)->message);
	ActionOE aoe3 = scc_parse_action("doubleclick(button(KEY_X), hold(button(KEY_A), button(KEY_Z), 0.3))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe3), ACTION_ERROR(aoe3)->message);
	
	Action* a1 = ACTION(aoe1);
	Action* a2 = ACTION(aoe2);
	Action* a3 = ACTION(aoe3);
	scc_action_compress(&a1);
	scc_action_compress(&a2);
	scc_action_compress(&a3);
	
	assert(tc, compare_paramteters(a1->get_property(a1, "hold_action"), a2->get_property(a2, "hold_action")));
	assert(tc, compare_paramteters(a1->get_property(a1, "dblclick_action"), a2->get_property(a2, "dblclick_action")));
	assert(tc, compare_paramteters(a1->get_property(a1, "default_action"), a2->get_property(a2, "default_action")));
	assert(tc, compare_paramteters(a1->get_property(a1, "timeout"), a2->get_property(a2, "timeout")));
	
	assert(tc, compare_paramteters(a1->get_property(a1, "hold_action"), a3->get_property(a3, "hold_action")));
	assert(tc, compare_paramteters(a1->get_property(a1, "dblclick_action"), a3->get_property(a3, "dblclick_action")));
	assert(tc, compare_paramteters(a1->get_property(a1, "default_action"), a3->get_property(a3, "default_action")));
	assert(tc, compare_paramteters(a1->get_property(a1, "timeout"), a3->get_property(a3, "timeout")));
	
	assert(tc, compare_paramteters(a2->get_property(a2, "hold_action"), a3->get_property(a3, "hold_action")));
	assert(tc, compare_paramteters(a2->get_property(a2, "dblclick_action"), a3->get_property(a3, "dblclick_action")));
	assert(tc, compare_paramteters(a2->get_property(a2, "default_action"), a3->get_property(a3, "default_action")));
	assert(tc, compare_paramteters(a2->get_property(a2, "timeout"), a3->get_property(a3, "timeout")));
	
	Mapper* m = testmapper_new();
	Action* a = a1;
	RC_REL(a2); RC_REL(a3);
	
	// For my next trick, I'll verify if action acts as expected
	// hold is KEY_A (30), doubleclick is KEY_X (45) and default is KEY_Z (44)
	
	// Short press should run default action...
	testmapper_reset(m);
	a->button_press(a, m);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 200);
	a->button_release(a, m);
	// .... but only after timeout is expired
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 110);
	assert(tc, 0 == strcmp("30", testmapper_get_keylog(m)));
	assert(tc, 1 == testmapper_get_key_count(m));
	while (testmapper_has_scheduled(m)) testmapper_run_scheduled(m, 1);
	assert(tc, 0 == testmapper_get_key_count(m));
	
	// Doubleclick should just work
	testmapper_reset(m);
	a->button_press(a, m);
	testmapper_run_scheduled(m, 100);
	a->button_release(a, m);
	testmapper_run_scheduled(m, 100);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	a->button_press(a, m);
	testmapper_run_scheduled(m, 500);
	assert(tc, 1 == testmapper_get_key_count(m));
	assert(tc, 0 == strcmp("45", testmapper_get_keylog(m)));
	a->button_release(a, m);
	assert(tc, 0 == testmapper_get_key_count(m));
	
	// And hold should work as well
	testmapper_reset(m);
	a->button_press(a, m);
	testmapper_run_scheduled(m, 200);
	assert(tc, 0 == strcmp("", testmapper_get_keylog(m)));
	assert(tc, 0 == testmapper_get_key_count(m));
	testmapper_run_scheduled(m, 100);
	assert(tc, 1 == testmapper_get_key_count(m));
	assert(tc, 0 == strcmp("30", testmapper_get_keylog(m)));
	testmapper_run_scheduled(m, 500);
	assert(tc, 1 == testmapper_get_key_count(m));
	a->button_release(a, m);
	assert(tc, 0 == testmapper_get_key_count(m));
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_sensitivity_mouse);
	DEFAULT_SUITE_ADD(test_sensitivity_axis);
	DEFAULT_SUITE_ADD(test_deadzone);
	DEFAULT_SUITE_ADD(test_hold);
	DEFAULT_SUITE_ADD(test_doubleclick);
	DEFAULT_SUITE_ADD(test_hold_doubleclick);
	
	return CuSuiteRunDefault();
}
