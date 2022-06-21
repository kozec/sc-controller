#pragma once
#include "scc/utils/logging.h"
#include <assert.h>


#define ASSERT(condition) do {								\
	if (!(condition)) {										\
		FATAL("Assertion " #condition " failed at %s:%i",	\
					__FILE__, __LINE__);					\
	}														\
} while (0)


#define COUNT_OF(a) (sizeof(a) / sizeof(a[0]))

