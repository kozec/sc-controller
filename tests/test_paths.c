#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/tools.h"
#include <string.h>
#include <stdlib.h>


void test_find_icon(CuTest* tc) {
	const char* paths[] = { "../share/images/menu-icons", NULL };
	bool has_color;
	char* filename = scc_find_icon("system/turn-off", false, &has_color, paths, NULL);
	assert(tc, !has_color);
	assert(tc, 0 == strcmp(filename, "../share/images/menu-icons/system/turn-off.bw.png"));
	free(filename);
	
	filename = scc_find_icon("system/turn-off", true, &has_color, paths, NULL);
	assert(tc, has_color);
	assert(tc, 0 == strcmp(filename, "../share/images/menu-icons/system/turn-off.png"));
	free(filename);
}


void test_get_controller_icons_path(CuTest* tc) {
	/** Basically, this was returning NULL and I had no idea why */
	const char* path = scc_get_controller_icons_path();
	assert(tc, path != NULL);
	assert(tc, strlen(path) > 1);
	
	path = scc_get_default_controller_icons_path();
	assert(tc, path != NULL);
	assert(tc, strlen(path) > 1);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_find_icon);
	DEFAULT_SUITE_ADD(test_get_controller_icons_path);
	
	return CuSuiteRunDefault();
}
