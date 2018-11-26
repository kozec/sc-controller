/*
SC Controller - utils - list

Generic list that automatically allocates more memory as items are added.
Usable for any kind of pointer and compatible with get_iter macro from iterable.h.
*/

#pragma once
#include "scc/utils/iterable.h"
#include <stddef.h>
#include <stdbool.h>

typedef struct _List_data {
	size_t				size;
	size_t				allocation;
	void(*dealloc_cb)(void*);
} _List_data;

#define LIST_TYPE(tpe)											\
	struct List_ ## tpe {										\
		tpe**			items;									\
		_List_data		_data;									\
		struct _ListIterator*(*iter_get)(void* obj);		\
	}*

typedef void(*list_foreach_cb)(void*);

typedef LIST_TYPE(void) _voidlist;
typedef LIST_TYPE(char) StringList;


typedef struct _ListIterator {
	ITERATOR_STRUCT_HEADER(void*);
	void(*free)(void* iter);
	_voidlist			list;
	size_t				index;
} *ListIterator;


/** Allocates new list of given type. Returns NULL on out-of-memory error */
#define list_new(tpe, allocation) ((struct List_ ## tpe *)_list_new(allocation));
void* _list_new(size_t allocation);

/** Adds new item to list. Returns false on out-of-memory error */
bool list_add(void* list, void* item);

/**
 * Inserts item to list at specified position. All items from item on given
 * position onwards are moved to right.
 * If 'n' is larger than list size, new item is added to end of list. To
 * intentionally create list with holes, see list_set.
 */
bool list_insert(void* list, size_t n, void* item);

/**
 * Removes signle instance of item from list, moving all following items to left.
 * Does _not_ call dealloc_cb for removed item, even if it's set.
 * Returns true on success or false if item was not found.
 */
bool list_remove(void* list, void* item);

/**
 * Clears list. If dealloc_cb is set, it's called for every removed item.
 */
void list_clear(void* list);

/**
 * Ensures that list has enough space for at least n new items.
 * This is good way to ensure memory is available before creating objects,
 * as it's guaranteed that immediatelly after calling list_allocate for 'n',
 * list_add will succeed n-times.
 *
 * Returns false if allocation fails.
 */
bool list_allocate(void* list, size_t n);

/**
 * Sets n-th element of list.
 * If n is bigger or equal to current size of list lis tsize is increased and
 * padded with NULLs.
 * 
 * Returns false on out-of-memory error
 */
bool list_set(void* list, size_t n, void* item);

/**
 * Returns n-th element of list. 'n' has to be >=0 and < list size
 */
#define list_get(list, n) ((list)->items[(n)])

/** Returns size of list */
#define list_size(list) ((size_t)(((_voidlist)list)->_data.size))

/** Pops last item from list or NULL if list is empty */
#define list_pop(tpe, list) ((tpe*)_list_pop(list))
void* _list_pop(void* list);

/** Returns length of list */
#define list_len(list) ((list)->_data.size)

/** Returns last item in list or NULL if list is empty */
#define list_last(list) ( list_len(list) > 0 ? ((list)->items[list_len(list) - 1]) : NULL )

/** Calls passed function for each item in list */
void list_foreach(void* list, list_foreach_cb cb);

/** Sets callback that will be called for every item in list just before list is deallocated */
void list_set_dealloc_cb(void* list, void(*dealloc_cb)(void*));

/**
 * Calls passed function for each item in list and removes any item for which
 * function returns false.
 *
 * This allocates no additional memory and cannot fail.
 */
void list_filter(void* list, bool(*filter_fn)(void* item, void* userdata), void* userdata);

/**
 * Deallocates list and returns pointer to first item in it.
 * Returned pointer has to be freed manually.
 */
void** list_consume(void* list);

/** Deallocates list */
void list_free(void* list);