/**
 * Iterable.h
 *
 * This is closest thing to generic iterator class I was able to come with.
 * It defines two headers:
 * - ITERATOR_STRUCT_HEADER	allows using iter_* methods to create iterator object
 *							and use it in similar fashion as iterators are used
 *							in higher level languages (including using FOREACH macro)
 * - FOREACHIN_HEADER		allows using FOREACH_IN macro that iterates object
 *							directly, without having to allocate additional memory
 */
#pragma once
#include <stdint.h>
#include <stdbool.h>

#define ITERATOR_STRUCT_HEADER(tpe)								\
	bool (*has_next)(void* iterator);							\
	tpe (*get_next)(void* iterator);							\
	bool (*remove)(void* iterator);								\
	void (*reset)(void* iterator);

#define FOREACHIN_HEADER(tpe)									\
	/**															\
	 * foreachin sets 'i' to next item in iterable object.		\
	 * 'state' should be used by foreachin to keep position		\
	 * while iterating and it is initailized to 0.				\
	 * foreachin returns true if iteration should continue or	\
	 * false if there are no more items to return.				\
	 */															\
	bool (*foreachin)(void* obj, tpe** i, uintptr_t* state);


/** FOREACH iterates over iterator 'it', supplying 'tpe' objects into 'i' */
#define FOREACH(tpe, i, it)										\
	for (														\
		tpe i;													\
		iter_has_next(it) && ( (i=iter_next(it)) || true )		\
		;														\
	)

/** FOREACH_IN runs loop body for every 'tpe' item in iterable object 'obj' */
#define FOREACH_IN(tpe, i, obj)									\
	for (														\
		tpe i = NULL, *__itrnl_ ## i = NULL;					\
		obj->foreachin((obj), &i, (uintptr_t*)&__itrnl_ ## i)	\
		;														\
	)


/** Initializes iterator. '_remove' may be NULL. */
#define ITERATOR_INIT(itrb, _has_next, _get_next, _reset, _remove) do {		\
	(itrb)->has_next = _has_next;											\
	(itrb)->get_next = _get_next;											\
	(itrb)->reset = _reset;													\
	(itrb)->remove = _remove;												\
} while(0)

typedef struct _voiditerator {
	ITERATOR_STRUCT_HEADER(void*);
} _voiditerator;

#define iter_get(obj) (((obj) == NULL) ? NULL : ((obj)->iter_get(obj)))

#define iter_free(iter) do { if ((iter) != NULL) ((iter)->free(iter)); } while (0)

/** Resets iterator to initial position */
#define iter_reset(iter) ((iter)->reset(iter))

/** Returns true if iterator still has some items available */
#define iter_has_next(iter) ((iter)->has_next(iter))

/** Returns next object and advances iterator */
#define iter_next(iter) ((iter)->get_next(iter))

/**
 * Removes last object returned by iter_next from iterable.
 * Returns true on success, false on failure or if operation is not supported.
 */
#define iter_remove(iter) ( ((iter)->remove == NULL) ? false : (iter)->remove(iter) )

