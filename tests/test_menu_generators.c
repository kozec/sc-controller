#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/utils/rc.h"
#include "scc/menu_data.h"
#include "scc/config.h"
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <math.h>

static Config* make_cfg(CuTest* tc) {
	const char* recents[] = { "a", "b", "c", "d", "e", "f" };
	Config* cfg = config_init();
	assert(tc, 1 == config_set_strings(cfg, "recent_profiles", recents, 6));
	return cfg;
}

/** Tests loading menu file */
void test_apply_generators(CuTest* tc) {
	Config* cfg = make_cfg(tc);
	MenuData* m = scc_menudata_from_json("share/default_menus/Default.menu", NULL);
	assert(tc, m != NULL);
	assert(tc, 1 == scc_menudata_apply_generators(m, cfg));
	
	MenuItem* i;
	
	ListIterator it = iter_get(m);
	assert(tc, 0 == strcmp("Switch profile", ((MenuItem*)iter_next(it))->name));
	assert(tc, 0 == strcmp("a", ((MenuItem*)iter_next(it))->name));
	assert(tc, 0 == strcmp("b", ((MenuItem*)iter_next(it))->name));
	i = iter_next(it);
	assert(tc, 0 == strcmp("menugen-id-2", i->id));
	assert(tc, 0 == strcmp("c", i->name));
	assert(tc, 0 == strcmp("All Profiles", ((MenuItem*)iter_next(it))->name));
	iter_free(it);
}

void test_recents(CuTest* tc) {
	int error;
	Config* cfg = make_cfg(tc);
	
	MenuData* d = scc_menudata_from_generator("recent", cfg, &error);
	assert(tc, d != NULL);
	ListIterator it = iter_get(d);
	assert(tc, 0 == strcmp("a", ((MenuItem*)iter_next(it))->name));
	assert(tc, 0 == strcmp("b", ((MenuItem*)iter_next(it))->name));
	assert(tc, 0 == strcmp("c", ((MenuItem*)iter_next(it))->name));
	assert(tc, iter_has_next(it));
	iter_free(it);
	
	d = scc_menudata_from_generator("recent(2)", cfg, &error);
	assert(tc, d != NULL);
	it = iter_get(d);
	assert(tc, 0 == strcmp("a", ((MenuItem*)iter_next(it))->name));
	assert(tc, 0 == strcmp("b", ((MenuItem*)iter_next(it))->name));
	assert(tc, !iter_has_next(it));
	iter_free(it);
	
	RC_REL(cfg);
}

void test_profiles(CuTest* tc) {
	int error;
	Config* cfg = make_cfg(tc);
	MenuData* d = scc_menudata_from_generator("profiles", cfg, &error);
	assert(tc, d != NULL);
	
	size_t count = 0;
	ListIterator it = iter_get(d);
	FOREACH(MenuItem*, i, it) {
		count ++;
	}
	assert(tc, count >= 3);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	chdir("..");
	// DEFAULT_SUITE_ADD(test_apply_generators);
	// DEFAULT_SUITE_ADD(test_recents);
	DEFAULT_SUITE_ADD(test_profiles);
	
	return CuSuiteRunDefault();
}
