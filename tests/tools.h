/** Random stuff used by tests */
#include "scc/utils/rc.h"

/**
 * Allows to verify that given object (compatible with reference counting as
 * defined in rc.h) is deallocated.
 * Once that happens, *flag is set to true.
 */
#define check_deallocated(rcc, flag) _check_deallocated((void*)(rcc), &((rcc)->_rc), (flag))
void _check_deallocated(void* obj, struct _RC* rc, bool* flag);
