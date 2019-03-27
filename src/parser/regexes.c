/*
 * There are only three uses of regexp in entirety of SCC, so functions here
 * are wrapping them away.
 */
#include "scc/utils/assert.h"
#include "parser.h"
#include <regex.h>

static bool initialized = false;
static regex_t re_int;
static regex_t re_float;

static void init() {
	ASSERT(0 == regcomp(&re_int, "^-?(([1-9][0-9]*)|(0))$", REG_EXTENDED | REG_NOSUB));
	ASSERT(0 == regcomp(&re_float, "^-?[0-9]*\\.[0-9]*$", REG_EXTENDED | REG_NOSUB));
	initialized = true;
}


bool scc_str_is_int(const char* str) {
	if (!initialized) init();
	return regexec(&re_int, str, 0, NULL, 0) == 0;
}

bool scc_str_is_float(const char* str) {
	if (!initialized) init();
	return regexec(&re_float, str, 0, NULL, 0) == 0;
}
