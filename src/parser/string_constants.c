/**
 * SC Controller - String parser constants
 *
 * This is manually generated list of strings that action parser recognizes
 * as constants and allows to type without quote marks.
 */

#include "scc/utils/hashmap.h"
#include "scc/utils/assert.h"


static const char* CONSTANTS[] = {
	"A", "B", "X", "Y", "START", "SELECT",
	"LEFT", "RIGHT", NULL
};


/** Returns -1 if there is no constant for given name */
const char* scc_get_string_constant(const char* key) {
	for (size_t i=0; CONSTANTS[i] != NULL; i++)
		if (strcmp(CONSTANTS[i], key) == 0)
			return CONSTANTS[i];
	return false;
}
