#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/utils/assert.h"
#include "scc/utils/rc.h"
#include "scc/controller.h"
#include "scc/profile.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

/** Tests loading profile file */
void test_loading(CuTest* tc) {
	Profile* p = scc_profile_from_json("../share/default_profiles/XBox Controller.sccprofile", NULL);
	assert(tc, p != NULL);
	assert(tc, strcmp(scc_action_to_string(p->get_button(p, B_A)), "button(BTN_A)") == 0);
	// printf("%s\n", scc_action_to_string(p->get_stick(p)));
	
	RC_REL(p);
}


/** Tests loading profile with action set to 'RPAD' instead of 'RPADPRESS' */
void test_load_old_rpad(CuTest* tc) {
	Profile* p = scc_profile_from_json("../share/default_profiles/Desktop.sccprofile", NULL);
	assert(tc, p != NULL);
	assert(tc, strcmp(scc_action_to_string(p->get_button(p, B_RPADPRESS)), "button(BTN_LEFT)") == 0);
	
	RC_REL(p);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	// DEFAULT_SUITE_ADD(test_loading);
	DEFAULT_SUITE_ADD(test_load_old_rpad);
	
	return CuSuiteRunDefault();
}
