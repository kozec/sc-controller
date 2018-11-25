#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/utils/rc.h"
#include "scc/menu_data.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

/** Tests loading menu file */
void test_loading(CuTest* tc) {
	MenuData* m = scc_menudata_from_json("../default_menus/Default.menu", NULL);
	assert(tc, m != NULL);
	
	MenuItem* it = scc_menudata_get_by_id(m, "keyboard_item");
	assert(tc, it != NULL);
	assert(tc, strcmp(it->icon, "system/keyboard") == 0);
	
	it = scc_menudata_get_by_id(m, "separator-after-profile-list");
	assert(tc, it != NULL);
	assert(tc, it->rows == 5);	// checks default
	assert(tc, it->type == MI_SEPARATOR);
	
	it = scc_menudata_get_by_id(m, "auto-id-2");
	assert(tc, it != NULL);
	assert(tc, it->type == MI_GENERATOR);
	assert(tc, it->rows == 3);
	assert(tc, strcmp(it->generator, "recent") == 0);
	
	// RC_REL(p);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_loading);
	
	return CuSuiteRunDefault();
}
