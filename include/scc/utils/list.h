/*
SC Controller - utils - list

Generic list that automatically allocates more memory as items are added.
Usable for any kind of pointer and compatible with get_iter macro from iterable.h.
*/

#pragma once
#include "scc/utils/iterable.h"
#include <stdbool.h>
#include <stdlib.h>
#include <stddef.h>

typedef struct _List_data {
	size_t				size;
	size_t				allocation;
	void(*dealloc_cb)(void*);
} _List_data;

#define LIST_TYPE(tpe)											\
	struct List_ ## tpe {										\
		tpe** items;											\
		_List_data _data;										\
		struct _ListIterator*(*iter_get)(void* obj);			\
		FOREACHIN_HEADER(tpe);									\
	}*

typedef void(*list_foreach_cb)(void* item);
typedef bool(*list_filter_cb)(void* item, void* userdata);
typedef int(*comparison_fn_t)(const void* i1, const void* i2);

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

/**
 * Adds new item to list. Both list should be of same type.
 * Returns false on out-of-memory error.
 */
bool list_add(void* list, void* item);

/**
 * Adds all items from list2. NULLs are ignored (skipped over.)
 * Returns false on out-of-memory error. List is not modified in such case.
 */
bool list_add_all(void* list, void* list2);

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

/** Returns index of intem in list or -1 if item is not found */
int list_index(void* list, void* item);

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

/**
 * Pops last item from list or NULL if list is empty.
 * Allocation is not decreased and so it's safe to add one item for every item
 * poped out of list.
 */
#define list_pop(list) ((typeof(list->items[0]))_list_pop(list))
void* _list_pop(void* list);

/** As list_pop, but pops first item */
#define list_unshift(list) ((typeof(list->items[0]))_list_unshift(list))
void* _list_unshift(void* list);

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
void list_filter(void* list, list_filter_cb cb, void* userdata);

/**
 * Sorts list using 'compare' function. List size is not changed and so
 * this cannot fail.
 */
void list_sort(void* list, comparison_fn_t compare);

/**
 * Deallocates list and returns pointer to first item in it.
 * Returned pointer has to be freed manually.
 */
void** list_consume(void* list);

/** Deallocates list */
void list_free(void* list);

