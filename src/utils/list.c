#include "scc/utils/iterable.h"
#include "scc/utils/list.h"
#include <string.h>
#include <stdlib.h>

#define ALLOCATION_INCREMENT 10
#define MAX(a, b) ( ((a)>(b)) ? (a) : (b) )
static ListIterator get_list_iterator(void* list);
static bool list_foreachin(void* obj, void** i, uintptr_t* state);

void* _list_new(size_t allocation) {
	_voidlist list = malloc(sizeof(struct List_void));
	if (list == NULL) return NULL;
	if (allocation == 0) {
		list->items = NULL;
	} else {
		list->items = malloc(allocation * sizeof(void*));
		if (list->items == NULL) {
			free(list);
			return NULL;
		}
	}
	list->iter_get = &get_list_iterator;
	list->foreachin = &list_foreachin;
	list->_data.size = 0;
	list->_data.allocation = allocation;
	list->_data.dealloc_cb = NULL;
	return list;
}

void list_free(void* _list) {
	_voidlist list = (_voidlist)_list;
	if (list != NULL) {
		if (list->_data.dealloc_cb != NULL)
			list_foreach(list, list->_data.dealloc_cb);
		free(list->items);
		free(list);
	}
}

void** list_consume(void* _list) {
	_voidlist list = (_voidlist)_list;
	void** items = list->items;
	free(list);
	return items;
}

void list_clear(void* _list) {
	_voidlist list = (_voidlist)_list;
	if (list->_data.dealloc_cb != NULL) {
		for (size_t i=0; i<list->_data.size; i++)
			if (list->items[i] != NULL)
				list->_data.dealloc_cb(list->items[i]);
	}
	
	list->_data.size = 0;
}

/** 
 * Unlike list_allocate which makes space for 'n new items', this makes
 * space for 'n items' _including_ items already in list.
 */
static inline bool _list_allocate(_voidlist list, size_t new_allocation) {
	void** new_items = realloc(list->items, new_allocation * sizeof(void*));
	if (new_items == NULL)
		return false;
	list->items = new_items;
	list->_data.allocation = new_allocation;
	return true;
}

bool list_allocate(void* _list, size_t n) {
	_voidlist list = (_voidlist)_list;
	size_t free = list->_data.allocation - list->_data.size;
	if (n < free)
		return true;
	return _list_allocate(list, list->_data.size + MAX(n - free, ALLOCATION_INCREMENT));
}

bool list_add(void* _list, void* item) {
	_voidlist list = (_voidlist)_list;
	if (list->_data.size == list->_data.allocation)
		if (!_list_allocate(list, list->_data.allocation + ALLOCATION_INCREMENT))
			return false;
	list->items[list->_data.size] = item;
	list->_data.size++;
	return true;
}

bool list_add_all(void* _list, void* _list2) {
	_voidlist list = (_voidlist)_list;
	_voidlist list2 = (_voidlist)_list2;
	if (!list_allocate(_list, list2->_data.size))
		return false;
	
	for (size_t i=0; i<list2->_data.size; i++) {
		list->items[list->_data.size] = list2->items[i];
		list->_data.size ++;
	}
	return true;
}

bool list_insert(void* _list, size_t n, void* item) {
	_voidlist list = (_voidlist)_list;
	if (n >= list->_data.size)
		return list_add(list, item);
	
	if (list->_data.size == list->_data.allocation)
		if (!_list_allocate(list, list->_data.allocation + ALLOCATION_INCREMENT))
			return false;
	
	memmove(list->items + n + 1, list->items + n,  sizeof(void*) * (list->_data.size - n));
	list->_data.size++;
	
	list->items[n] = item;
	return true;
}

bool list_remove(void* _list, void* item) {
	// This is just list_filter with fixed condition
	_voidlist list = (_voidlist)_list;
	size_t i = 0;
	while (i < list->_data.size) {
		if (item == list->items[i]) {
			if (i < list->_data.size - 1)
				memcpy(list->items + i, list->items + i + 1,
							sizeof(list->items[i]) * (list->_data.size - i));
			list->_data.size --;
			return true;
		}
		i++;
	}
	return false;
}

int list_index(void* _list, void* item) {
	_voidlist list = (_voidlist)_list;
	int i = 0;
	while (i < list->_data.size) {
		if (item == list->items[i])
			return i;
		i++;
	}
	return -1;
}

bool list_set(void* _list, size_t n, void* item) {
	_voidlist list = (_voidlist)_list;
	if (n < list->_data.size) {
		// This one is simple, no allocation is needed.
		list->items[n] = item;
		return true;
	} else if (n >= list->_data.allocation) {
		// This one means increasing allocation.
		if (!_list_allocate(list, n + 1))
			return false;
	}
	// Zero everything in freshly created space
	memset(&list->items[list->_data.size], 0, sizeof(void*)* (n + 1 - list->_data.size));
	list->items[n] = item;
	list->_data.size = n + 1;
	return true;
}

void* _list_pop(void* _list) {
	_voidlist list = (_voidlist)_list;
	if (list->_data.size == 0) return NULL;
	void* item = list->items[list->_data.size - 1];
	list->_data.size --;
	return item;
}

void* _list_unshift(void* _list) {
	_voidlist list = (_voidlist)_list;
	if (list->_data.size == 0) return NULL;
	void* item = list->items[0];
	for (size_t i=0; i<list->_data.size-1; i++)
		list->items[i] = list->items[i+1];
	list->_data.size --;
	return item;
}

void list_foreach(void* _list, list_foreach_cb cb) {
	_voidlist list = (_voidlist)_list;
	for(size_t i=0; i<list->_data.size; i++)
		cb(list->items[i]);
}

void list_set_dealloc_cb(void* _list, void(*dealloc_cb)(void*)) {
	_voidlist list = (_voidlist)_list;
	list->_data.dealloc_cb = dealloc_cb;
}

void list_filter(void* _list, bool(*filter_fn)(void* item, void* userdata), void* userdata) {
	_voidlist list = (_voidlist)_list;
	size_t i = 0;
	while (i < list->_data.size) {
		if (filter_fn(list->items[i], userdata)) {
			// keep
			i ++;
		} else {
			// remove
			if (i < list->_data.size - 1)
				memcpy(list->items + i, list->items + i + 1,
							sizeof(list->items[i]) * (list->_data.size - i - 1));
			list->_data.size --;
		}
	}
}

void list_sort(void* _list, comparison_fn_t compare) {
	_voidlist list = (_voidlist)_list;
	qsort(list->items, list->_data.size, sizeof(void*), compare);
}


static bool list_iterator_has_next(void* _iter) {
	ListIterator iter = (ListIterator)_iter;
	return (iter->index < iter->list->_data.size);
}

static void* list_iterator_get_next(void* _iter) {
	ListIterator iter = (ListIterator)_iter;
	return iter->list->items[iter->index++];
}

static void list_iterator_reset(void* _iter) {
	ListIterator iter = (ListIterator)_iter;
	iter->index = 0;
}

static bool list_iterator_remove(void* _iter) {
	ListIterator iter = (ListIterator)_iter;
	iter->index--;
	return list_remove(iter->list, list_get(iter->list, iter->index));
}

static void list_iterator_free(void* _iter) {
	free(_iter);
}

static ListIterator get_list_iterator(void* list) {
	ListIterator iter = malloc(sizeof(struct _ListIterator));
	if (iter == NULL) return NULL;
	ITERATOR_INIT(iter, list_iterator_has_next, list_iterator_get_next,
					list_iterator_reset, list_iterator_remove);
	iter->free = &list_iterator_free;
	iter->list = list;
	iter->index = 0;
	return iter;
}

static bool list_foreachin(void* obj, void** i, uintptr_t* state) {
	_voidlist lst = (_voidlist)obj;
	if (*state >= lst->_data.size)
		return false;
	*i = lst->items[*state];
	(*state) ++;
	return true;
}
