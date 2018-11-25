#pragma once
#include <stdbool.h>

#define ITERATOR_STRUCT_HEADER(tpe)					\
	bool (*has_next)(void* iterator);				\
	tpe (*get_next)(void* iterator);				\
	void (*reset)(void* iterator);

#define FOREACH(tpe, i, it)										\
	for (														\
		tpe i;													\
		iter_has_next(it) && ( (i=iter_next(it)) || true )		\
		; \
	)

#define ITERATOR_INIT(itrb, _has_next, _get_next, _reset) do {	\
	(itrb)->has_next = &_has_next;								\
	(itrb)->get_next = &_get_next;								\
	(itrb)->reset = &_reset;									\
} while(0)

typedef struct _voiditerator {
	ITERATOR_STRUCT_HEADER(void*);
} _voiditerator;

#define iter_get(obj) (((obj) == NULL) ? NULL : ((obj)->iter_get(obj)))

#define iter_free(iter) do { if ((iter) != NULL) ((iter)->free(iter)); } while (0)

#define iter_reset(iter) ((iter)->reset(iter))

#define iter_has_next(itrb) ((itrb)->has_next(itrb))

#define iter_next(itrb) ((itrb)->get_next(itrb))
