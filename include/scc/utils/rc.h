#pragma once
#include "scc/utils/container_of.h"
#include <stddef.h>

typedef void (*_rc_dealloc_fn)(void* obj);

struct _RC {
	size_t				count;
	_rc_dealloc_fn		dealloc;
};

#define RC_HEADER struct _RC _rc

/**
 * Initializes ref-countable object with reference count set to 1.
 * Should be used by method that creates such object.
 */
#define RC_INIT(obj, dealloc_fn) do {									\
	(obj)->_rc.count = 1;												\
	(obj)->_rc.dealloc = (_rc_dealloc_fn)dealloc_fn;					\
} while (0)

/**
 * Turns off reference counton given object, keeping it in memory forever.
 * This can be done simply by setting dealloc function to NULL.
 */
#define RC_STATIC(obj) do {												\
	(obj)->_rc.count = 0xFFFFFF;										\
	(obj)->_rc.dealloc = NULL;											\
} while(0)

/** Increases reference counter */
#define RC_ADD(obj) do { (obj)->_rc.count++; } while (0)

/** Decreases reference counter and, if counter reaches 0, deallocates object */
#define RC_REL(obj) do {												\
		if ((obj) != NULL) {											\
			if (((obj)->_rc.dealloc) != NULL) {							\
				if ((obj)->_rc.count <= 1)								\
					(obj)->_rc.dealloc((obj));							\
				else													\
					(obj)->_rc.count--;									\
			}															\
		}																\
	} while(0)
