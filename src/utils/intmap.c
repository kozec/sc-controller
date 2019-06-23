/*
 * IntMap implementation.
 */
#include "scc/utils/assert.h"
#include "scc/utils/intmap.h"
#include "scc/utils/iterable.h"

#include <stdlib.h>
#include <stdio.h>

#define INITIAL_SIZE (256)
#define MAX_CHAIN_LENGTH (8)

static IntMapIterator get_intmap_iterator(intmap_t m);

/* We need to keep keys and values */
typedef struct _intmap_element {
	intptr_t key;
	uint8_t in_use;
	any_t data;
} intmap_element;

/* A intmap has some maximum size and current size,
 * as well as the data to hold. */
typedef struct _intmap_map {
	IntMapIterator (*get_intmap_iterator)(intmap_t m);
	uint32_t table_size;
	uint32_t size;
	intmap_element *data;
} intmap_map;

/*
 * Return an empty intmap, or NULL on failure.
 */
intmap_t intmap_new() {
	intmap_map* m = (intmap_map*) malloc(sizeof(intmap_map));
	if(!m) goto err;
	
	m->data = (intmap_element*) calloc(INITIAL_SIZE, sizeof(intmap_element));
	if(!m->data) goto err;
	
	m->get_intmap_iterator = &get_intmap_iterator;
	m->table_size = INITIAL_SIZE;
	m->size = 0;
	
	return (intmap_t)m;
err:
	if (m)
		intmap_free((intmap_t)m);
	return NULL;
}

inline static uint32_t intmap_hash_int(intmap_map * m, intptr_t key) {
	return ((uint32_t)(key * 2147483647)) % m->table_size;
}

/*
 * Return the integer of the location in data
 * to store the point to the item, or MAP_FULL.
 */
int64_t intmap_hash(intmap_t in, intptr_t key) {
	uint32_t curr;
	uint32_t i;
	
	/* Cast the intmap */
	intmap_map* m = (intmap_map *) in;
	
	/* If full, return immediately */
	if(m->size >= (m->table_size/2)) return MAP_FULL;
	
	/* Find the best index */
	curr = intmap_hash_int(m, key);
	
	/* Linear probing */
	for(i = 0; i< MAX_CHAIN_LENGTH; i++){
		if(m->data[curr].in_use == 0) {
			return curr;
		}
		
		if ((m->data[curr].in_use == 1) && (m->data[curr].key == key))
			return curr;
		
		curr = (curr + 1) % m->table_size;
	}
	
	return MAP_FULL;
}

/*
 * Doubles the size of the intmap, and rehashes all the elements
 */
int intmap_rehash(intmap_t in) {
	uint32_t i;
	uint32_t old_size;
	intmap_element* curr;
	
	/* Setup the new elements */
	intmap_map *m = (intmap_map *) in;
	intmap_element* temp = (intmap_element *)
		calloc(2 * m->table_size, sizeof(intmap_element));
	if(!temp) return MAP_OMEM;
	
	/* Update the array */
	curr = m->data;
	m->data = temp;
	
	/* Update the size */
	old_size = m->table_size;
	m->table_size = 2 * m->table_size;
	m->size = 0;
	
	/* Rehash the elements */
	for(i = 0; i < old_size; i++) {
		int status;
		
		if (curr[i].in_use == 0)
			continue;
		
		status = intmap_put((intmap_t)m, curr[i].key, curr[i].data);
		if (status != MAP_OK)
			return status;
	}
	
	free(curr);
	
	return MAP_OK;
}

/*
 * Add a pointer to the intmap with some key
 */
int intmap_put(intmap_t in, intptr_t key, any_t value) {
	int64_t index;
	intmap_map* m;
	
	/* Cast the intmap */
	m = (intmap_map *) in;
	
	/* Find a place to put our value */
	index = intmap_hash(in, key);
	while(index == MAP_FULL){
		if (intmap_rehash(in) == MAP_OMEM) {
			return MAP_OMEM;
		}
		index = intmap_hash(in, key);
	}
	
	/* Set the data */
	m->data[index].data = value;
	m->data[index].key = key;
	m->data[index].in_use = 1;
	m->size++;
	
	return MAP_OK;
}

/*
 * Get your pointer out of the intmap with a key
 */
int intmap_get(intmap_t in, intptr_t key, any_t *arg) {
	uint32_t curr;
	uint32_t i;
	intmap_map* m;
	
	/* Cast the intmap */
	m = (intmap_map *) in;
	
	/* Find data location */
	curr = intmap_hash_int(m, key);
	
	/* Linear probing, if necessary */
	for(i = 0; i<MAX_CHAIN_LENGTH; i++){
		
		uint8_t in_use = m->data[curr].in_use;
		if (in_use) {
			if (m->data[curr].key == key) {
				*arg = (m->data[curr].data);
				return MAP_OK;
			}
		}
		
		curr = (curr + 1) % m->table_size;
	}
	
	*arg = NULL;
	
	/* Not found */
	return MAP_MISSING;
}

/*
 * Iterate the function parameter over each element in the intmap.  The
 * additional any_t argument is passed to the function as its first
 * argument and the intmap element is the second.
 */
int intmap_iterate(intmap_t in, PFany f, any_t item) {
	uint32_t i;
	
	/* Cast the intmap */
	intmap_map* m = (intmap_map*) in;
	
	/* On empty intmap, return immediately */
	if (intmap_length((intmap_t)m) <= 0)
		return MAP_MISSING;	
	
	/* Linear probing */
	for(i = 0; i< m->table_size; i++)
		if(m->data[i].in_use != 0) {
			any_t data = (any_t) (m->data[i].data);
			int status = f(item, data);
			if (status != MAP_OK) {
				return status;
			}
		}
	
	return MAP_OK;
}

/*
 * Remove an element with that key from the map
 */
int intmap_remove(intmap_t in, intptr_t key) {
	uint32_t curr;
	uint32_t i;
	intmap_map* m;
	
	/* Cast the intmap */
	m = (intmap_map *) in;
	
	/* Find key */
	curr = intmap_hash_int(m, key);
	
	/* Linear probing, if necessary */
	for(i = 0; i<MAX_CHAIN_LENGTH; i++){
		uint8_t in_use = m->data[curr].in_use;
		if (in_use == 1){
			if (m->data[curr].key == key) {
				/* Blank out the fields */
				m->data[curr].in_use = 0;
				m->data[curr].data = NULL;
				
				/* Reduce the size */
				m->size--;
				return MAP_OK;
			}
		}
		curr = (curr + 1) % m->table_size;
	}
	
	/* Data not found */
	return MAP_MISSING;
}

/* Deallocate the intmap */
void intmap_free(intmap_t in) {
	intmap_map* m = (intmap_map*) in;
	
	free(m->data);
	free(m);
}

/* Return the length of the intmap */
uint32_t intmap_length(intmap_t in) {
	intmap_map* m = (intmap_map *) in;
	if(m != NULL) return m->size;
	else return 0;
}

static void intmap_iterator_find_next(IntMapIterator iter) {
	intmap_map* m = (intmap_map*)iter->map;
	iter->next ++;
	while (iter->next < m->table_size) {
		if (m->data[iter->next].in_use != 0)
			return;
		iter->next ++;
	}
	iter->next = -1;
}

static bool intmap_iterator_has_next(void* _iter) {
	IntMapIterator iter = (IntMapIterator)_iter;
	return (iter->next >= 0);
}

static intptr_t intmap_iterator_get_next(void* _iter) {
	IntMapIterator iter = (IntMapIterator)_iter;
	intptr_t rv = ((intmap_map*)iter->map)->data[iter->next].key;
	intmap_iterator_find_next(iter);
	return rv;
}

static void intmap_iterator_reset(void* _iter) {
	IntMapIterator iter = (IntMapIterator)_iter;
	iter->next = -1;
	intmap_iterator_find_next(iter);
}

static void intmap_iterator_free(void* _iter) {
	free(_iter);
}

static IntMapIterator get_intmap_iterator(intmap_t m) {
	IntMapIterator iter = malloc(sizeof(struct _IntMapIterator));
	if (iter == NULL) return NULL;
	ITERATOR_INIT(iter, intmap_iterator_has_next,
					intmap_iterator_get_next, intmap_iterator_reset, NULL);
	iter->free = &intmap_iterator_free;
	iter->map = m;
	intmap_iterator_reset(iter);
	return iter;
}
