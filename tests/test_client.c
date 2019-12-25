#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/client.h"
#include <string.h>
#include <stdlib.h>

/**
 * Tests if sccc_parse works as described
 */
void test_sccc_parse(CuTest* tc) {
	StringList lst;
	lst = sccc_parse("hello world");
	assert(tc, 2 == list_len(lst));
	lst = sccc_parse("hello \"world with\" space");
	assert(tc, 0 == strcmp("world with", list_get(lst, 1)));
	assert(tc, 3 == list_len(lst));
	lst = sccc_parse("hello ran!dom+ characters");
	assert(tc, 3 == list_len(lst));
	lst = sccc_parse("hello (parentheses) and [stuff]");
	assert(tc, 4 == list_len(lst));
	lst = sccc_parse("hello escaped\\ space");
	assert(tc, 3 == list_len(lst));
	assert(tc, 0 == strcmp("escaped\\", list_get(lst, 1)));
	lst = sccc_parse("qoutes \"without\" space");
	assert(tc, 0 == strcmp("without", list_get(lst, 1)));
	assert(tc, 3 == list_len(lst));
	lst = sccc_parse("qoutes at \"end\"");
	assert(tc, 0 == strcmp("end", list_get(lst, 2)));
	assert(tc, 3 == list_len(lst));
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_sccc_parse);
	
	return CuSuiteRunDefault();
}

