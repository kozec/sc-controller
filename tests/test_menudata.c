#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/utils/rc.h"
#include "scc/menu_data.h"
#include <string.h>
#include <unistd.h>


/** Tests loading menu file */
void test_loading(CuTest* tc) {
	MenuData* m = scc_menudata_from_json("../share/default_menus/Default.menu", NULL);
	assert(tc, m != NULL);
	
	MenuItem* i = scc_menudata_get_by_id(m, "turnoff_item");
	assert(tc, i != NULL);
	assert(tc, strcmp(i->icon, "system/turn-off") == 0);
	
	i = scc_menudata_get_by_id(m, "separator-after-profile-list");
	assert(tc, i != NULL);
	assert(tc, i->type == MI_SEPARATOR);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_loading);
	
	return CuSuiteRunDefault();
}
