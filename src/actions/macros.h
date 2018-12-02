/*
 * SC-Controller - Macros
 *
 * Common code for all macro-like actions and action with multiple child actions.
 */
#pragma once
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include "scc/action.h"
#include <stdlib.h>
#include <stdio.h>

typedef LIST_TYPE(Action) ActionList;

extern const char* KW_MACRO;
extern const char* KW_REPEAT;
extern const char* KW_SLEEP;

uint32_t sor_get_sleep_time(Action *a);

void macro_set_repeat(Action* a, bool repeat);

/**
 * Adds actions form parameter list. Every parameter
 * of list has to be ActionParameter.
 * Returns false if memory cannot be allocated.
 */
bool macro_add_from_params(Action* a, ParameterList lst);

/** Returned string has to be deallocated b caller */
char* actions_to_string(ActionList l, const char* separator);


#define MULTICHILD_DEALLOC(a) do {						\
	list_foreach((a)->children, &deref_action);			\
	list_free((a)->children);							\
} while(0)
