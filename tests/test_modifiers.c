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
	a->whole(a, m, 0, 0, PST_RIGHT);
	testmapper_set_buttons(m, B_RPADTOUCH);
	a->whole(a, m, 10, -100, PST_RIGHT);
	
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
	a->whole(a, m, 0, 0, PST_RIGHT);
	testmapper_set_buttons(m, B_RPADTOUCH);
	a->whole(a, m, 10, -100, PST_RIGHT);
	
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
			a->whole(a, m, inputs[j][0], inputs[j][1], PST_RIGHT);
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

int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_sensitivity_mouse);
	DEFAULT_SUITE_ADD(test_sensitivity_axis);
	DEFAULT_SUITE_ADD(test_deadzone);
	
	return CuSuiteRunDefault();
}
