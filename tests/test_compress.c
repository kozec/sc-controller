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


/** Tests compressing combination of hold & doubleclick modifier */
void test_hold_dblckick(CuTest* tc) {
	ActionOE aoe;
	
	aoe = scc_parse_action("doubleclick(hold(axis(ABS_RX), axis(ABS_RY)), axis(ABS_Z))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	assert(tc, 0 == strcmp("doubleclick", ACTION(aoe)->type));
	
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	
	Action* hold = scc_parameter_as_action(a->get_property(a, "hold_action"));
	Action* dblc = scc_parameter_as_action(a->get_property(a, "dblclick_action"));
	Action* dflt = scc_parameter_as_action(a->get_property(a, "default_action"));
	
	assert(tc, ABS_RX == scc_parameter_as_int(hold->get_property(hold, "axis")));
	assert(tc, ABS_RY == scc_parameter_as_int(dblc->get_property(dblc, "axis")));
	assert(tc, ABS_Z == scc_parameter_as_int(dflt->get_property(dflt, "axis")));
	
	RC_REL(a);
}

/** Tests compressing sensitivity applied to action deeper in chain of modifiers */
void test_sens(CuTest* tc) {
	ActionOE aoe;
	
	aoe = scc_parse_action("sens(0.5, 7, clicked(mouse()))");
	assert_msg(tc, !IS_ACTION_ERROR(aoe), ACTION_ERROR(aoe)->message);
	assert(tc, 0 == strcmp("sens", ACTION(aoe)->type));
	
	Action* a = ACTION(aoe);
	scc_action_compress(&a);
	Action* mouse = a->extended.get_child(a);
	
	Parameter* sens = mouse->get_property(mouse, "sensitivity");
	assert(tc, 0.5f == scc_parameter_as_float(scc_parameter_tuple_get_child(sens, 0)));
	assert(tc, 7.0f == scc_parameter_as_float(scc_parameter_tuple_get_child(sens, 1)));
	
	RC_REL(a);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_hold_dblckick);
	DEFAULT_SUITE_ADD(test_sens);
	
	return CuSuiteRunDefault();
}
