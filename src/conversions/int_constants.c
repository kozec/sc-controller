/*
 * SC Controller - Conversions.
 *
 * Works with auto-generated list in generated.c and provides
 * function to query those mappings.
 */
#include "scc/utils/hashmap.h"
#include "scc/conversions.h"
#include "conversions.h"
#include <unistd.h>
#include <stdio.h>
#include <stdint.h>

extern struct Item keys[];
extern struct Item rels_and_abses[];
extern size_t rels_and_abses_cnt;

static map_t constants = NULL;	// Basically just cache to get values little faster


static inline void generate_constants() {
	constants = hashmap_new();
	if (constants == NULL) return;
	hashmap_dont_copy_keys(constants);
	for (size_t i=1; i<=SCC_KEYCODE_MAX; i++) {	// intentionalyl skips 0/KEY_RESERVED
		if (keys[i].name != NULL) {
			if (hashmap_put(constants, keys[i].name, &keys[i]) != MAP_OK) {
				hashmap_free(constants);
				constants = NULL;
				return;
			}
		}
	}
	for (size_t i=0; i<=rels_and_abses_cnt; i++) {
		if (rels_and_abses[i].name != NULL) {
			if (hashmap_put(constants, rels_and_abses[i].name, &rels_and_abses[i]) != MAP_OK) {
				hashmap_free(constants);
				constants = NULL;
				return;
			}
		}
	}
}


/** Returns -1 if there is no constant for given name */
int32_t scc_get_int_constant(const char* key) {
	if (constants == NULL) generate_constants();
	if (constants == NULL) return -2;	// OOM happened
	
	struct Item* item;
	if (hashmap_get(constants, key, (any_t)&item) != MAP_OK) {
		return -1;
	}
	return (int32_t)item->value;
}


const char* scc_get_key_name(int32_t code) {
	if ((code < 1) || (code > SCC_KEYCODE_MAX)) return NULL;
	return keys[code].name;
}


uint16_t scc_keycode_to_hw_scan(Keycode code) {
	if ((code <= 0) || (code > SCC_KEYCODE_MAX))
		return 0;
	
	return keys[code].hw_scan;
}


uint16_t scc_keycode_to_x11(Keycode code) {
	if ((code <= 0) || (code > SCC_KEYCODE_MAX))
		return 0;
	
	return keys[code].x11_keycode;
}


#ifdef _WIN32
uint16_t scc_keycode_to_win32_scan(Keycode code) {
	if ((code <= 0) || (code > SCC_KEYCODE_MAX))
		return 0;
	
	return keys[code].win32_scan;
}
#endif

