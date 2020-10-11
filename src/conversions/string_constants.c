/**
 * SC Controller - String parser constants
 *
 * This is manually generated list of strings that action parser recognizes
 * as constants and allows to type without quote marks.
 */

#include "scc/utils/hashmap.h"
#include "scc/utils/assert.h"


static const char* CONSTANTS[] = {
	// Buttons
	"A", "B", "X", "Y", "START", "C", "BACK", "LRPADTOUCH", "RPADTOUCH",
	"LPADPRESS", "RPADPRESS", "STICKPRESS",
	// Bumpers
	"LB", "RB",
	// Triggers
	"LT", "RT",
	// Grips
	"LGRIP", "RGRIP",
	// Deadzone modes
	"CUT", "ROUND", "LINEAR", "MINIMUM",
	// Haptic positions
	"LEFT", "RIGHT", "BOTH",
	// Stuff used by menus
	"SAME", "DEFAULT",
	// Terminator
	NULL
};


/** Returns NULL if there is no constant for given name */
const char* scc_get_string_constant(const char* key) {
	for (size_t i=0; CONSTANTS[i] != NULL; i++)
		if (strcmp(CONSTANTS[i], key) == 0)
			return CONSTANTS[i];
	return NULL;
}

