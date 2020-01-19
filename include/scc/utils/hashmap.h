/*
 * Generic hashmap manipulation functions
 *
 * Originally by Elliot C Back - http://elliottback.com/wp/hashmap-implementation-in-c/
 *
 * Modified by Pete Warden to fix a serious performance problem, support strings as keys
 * and removed thread synchronization - http://petewarden.typepad.com
 */
#pragma once
#include "scc/utils/iterable.h"
#include <stdint.h>

#ifndef MAP_MISSING
	#define MAP_MISSING -3  /* No such element */
	#define MAP_FULL -2 	/* Hashmap is full */
	#define MAP_OMEM -1 	/* Out of Memory */
	#define MAP_OK 0 		/* OK */

	/*
	 * any_t is a pointer.  This allows you to put arbitrary structures in
	 * the hashmap.
	 */
	typedef void *any_t;

	/*
	 * PFany is a pointer to a function that can take two any_t arguments
	 * and return an integer. Returns status code..
	 */
	typedef int (*PFany)(any_t, any_t);
#endif

/*
 * map_t is a pointer to an internally maintained data structure.
 * Clients of this package do not need to know how hashmaps are
 * represented.  They see and manipulate only map_t's.
 */
typedef struct _hashmap_map_public {
	struct _HashMapIterator* (*iter_get)(struct _hashmap_map_public* m);
} *map_t;

/*
 * Return an empty hashmap. Returns NULL on failure.
*/
map_t hashmap_new();

/*
 * Iteratively call f with argument (item, data) for
 * each element data in the hashmap. The function must
 * return a map status code. If it returns anything other
 * than MAP_OK the traversal is terminated. f must
 * not reenter any hashmap functions, or deadlock may arise.
 */
int hashmap_iterate(map_t in, PFany f, any_t item);

/*
 * Add an element to the hashmap. Return MAP_OK or MAP_OMEM.
 */
int hashmap_put(map_t in, const char* key, any_t value);

/*
 * Normally, hashmap_put creates copy of every key and keeps it in memory until map is deallocated.
 * This disable that behaviour, making hashmap situable for keys that are guaranteed to stay
 * allocated by caller.
 *
 * This has to be called before 1st key is added.
 */
void hashmap_dont_copy_keys(map_t in);

/*
 * Get an element from the hashmap. Return MAP_OK or MAP_MISSING.
 */
int hashmap_get(map_t in, const char* key, any_t *arg);

/*
 * Get a key from the hashmap. Returns key of same value allocated by hashmap
 * or NULL if key is not found.
 */
const char* hashmap_get_key(map_t in, const char* key);

/*
 * Remove an element from the hashmap. Return MAP_OK or MAP_MISSING.
 */
int hashmap_remove(map_t in, const char* key);

/*
 * Get any element. Return MAP_OK or MAP_MISSING.
 * remove - should the element be removed from the hashmap
 */
int hashmap_get_one(map_t in, any_t *arg, int remove);

/*
 * Free the hashmap
 */
void hashmap_free(map_t in);

/*
 * Get the current size of a hashmap
 */
uint32_t hashmap_length(map_t in);


typedef struct _HashMapIterator {
	ITERATOR_STRUCT_HEADER(const char*);
	void(*free)(void* iter);
	map_t				map;
	int64_t				next;
} *HashMapIterator;

