#pragma once
#include <stddef.h>

#ifndef container_of
#define container_of(ptr, type, member) (type *)((char *)(ptr) - offsetof(type, member))
#endif
