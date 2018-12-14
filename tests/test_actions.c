#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/utils/container_of.h"
#include "scc/mapper.h"
#include "scc/action.h"
#include "scc/parser.h"
#include "testmapper/testmapper.h"
#include "tools.h"
#include <tgmath.h>
#include <string.h>
#include <stdlib.h>

typedef struct {
	Action				action;
	Action*			 	child;
} BallModifierAlike;


/** Tests various ways how to create mouse action */
void test_mouse_trackball_trackpad(CuTest* tc) {
	ActionOE aoe;
	
	aoe = scc_parse_action("mouse");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	assert(tc, 0 == strcmp("mouse", ACTION(aoe)->type));
	RC_REL(ACTION(aoe));
	
	aoe = scc_parse_action("trackpad");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	assert(tc, 0 == strcmp("mouse", ACTION(aoe)->type));
	RC_REL(ACTION(aoe));
	
	aoe = scc_parse_action("trackball");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	assert(tc, 0 == strcmp("ball", ACTION(aoe)->type));
	assert(tc, 0 == strcmp("ball(mouse())", scc_action_to_string(ACTION(aoe))));

	BallModifierAlike* ball = container_of(ACTION(aoe), BallModifierAlike, action);
	Action* mouse = ball->child;
	bool was_deallocated;
	check_deallocated(mouse, &was_deallocated);
	RC_REL(ACTION(aoe));
	assert(tc, was_deallocated);
}

int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_mouse_trackball_trackpad);
	
	return CuSuiteRunDefault();
}
