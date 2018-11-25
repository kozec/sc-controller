#pragma once
#include "scc/utils/logging.h"

#define ASSERT(condition) do {								\
	if (!(condition)) {										\
		FATAL("Assertion " #condition " failed at %s:%i",	\
					__FILE__, __LINE__);					\
	}														\
} while (0)
