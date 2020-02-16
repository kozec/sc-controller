/*
 * IntMap. Based on hashmap, but optimized for integer keys
 */
#pragma once
#include "scc/utils/iterable.h"
#include <stdint.h>

#ifndef MAP_MISSING
	#define MAP_MISSING -3  /* No such element */
	#define MAP_FULL -2 	/* Hashmap is full */
	#define MAP_OMEM -1 	/* Out of Memory */
	#define MAP_OK 0 		/* OK */

	typedef void *any_t;

	typedef int (*PFany)(any_t, any_t);
#endif

/*
 * intmap_t is a pointer to an internally maintained data structure.
 */
typedef struct _intmap_map_public {
	struct _IntMapIterator* (*iter_get)(struct _intmap_map_public* m);
} *intmap_t;

/*
 * Return an empty IntMap. Returns NULL on failure.
*/
intmap_t intmap_new();

/*
 * Iteratively call f with argument (item, data) for
 * each element data in the intmap. The function must
 * return a map status code. If it returns anything other
 * than MAP_OK the traversal is terminated. f must
 * not reenter any intmap functions, or deadlock may arise.
 */
int intmap_iterate(intmap_t in, PFany f, any_t item);

/*
 * Add an element to the intmap. Return MAP_OK or MAP_OMEM.
 */
int intmap_put(intmap_t in, intptr_t key, any_t value);

/*
 * Get an element from the intmap. Return MAP_OK or MAP_MISSING.
 */
int intmap_get(intmap_t in, intptr_t key, any_t *arg);

/*
 * Remove an element from the intmap. Return MAP_OK or MAP_MISSING.
 */
int intmap_remove(intmap_t in, intptr_t key);

/*
 * Free the intmap
 */
void intmap_free(intmap_t in);

/*
 * Get the current size of a intmap
 */
uint32_t intmap_length(intmap_t in);


typedef struct _IntMapIterator {
	ITERATOR_STRUCT_HEADER(intptr_t);
	void(*free)(void* iter);
	intmap_t				map;
	int64_t				next;
} *IntMapIterator;

