/** Random stuff used by tests */
#include "scc/utils/assert.h"
#include "scc/utils/intmap.h"
#include "scc/utils/rc.h"
#include "tools.h"
#include <stdint.h>

struct dealloc_data {
	_rc_dealloc_fn		dealloc;
	bool*				flag;
};

static intmap_t objects = NULL;

void _check_deallocated_deallocator(void* obj) {
	struct dealloc_data* dd;
	ASSERT(intmap_get(objects, (intptr_t)obj, (any_t*)&dd) == MAP_OK);
	intmap_remove(objects, (intptr_t)obj);
	
	*(dd->flag) = true;
	dd->dealloc(obj);
	
	free(dd);
}

void _check_deallocated(void* obj, struct _RC* rc, bool* flag) {
	struct dealloc_data* dd;
	if (objects == NULL)
		objects = intmap_new();
	ASSERT(objects != NULL);
	ASSERT((dd = malloc(sizeof(struct dealloc_data))) != NULL);
	
	// This overwrites _rc_dealloc_fn on the fly.
	// 'objects' holds mapping to flag and original deallocator.
	ASSERT(intmap_put(objects, (intptr_t)obj, (any_t)dd) == MAP_OK);
	dd->dealloc = rc->dealloc;
	dd->flag = flag;
	rc->dealloc = &_check_deallocated_deallocator;
	*flag = false;
}
