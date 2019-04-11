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


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_find_icon);
	
	return CuSuiteRunDefault();
}
