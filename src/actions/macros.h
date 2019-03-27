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


////// Common code for Macro and Multiaction

/** Common for scc_macro_combine and scc_multiaction_combine */
Action* combine(const char* keyword, Action* a1, Action* a2, ActionList (*get_children)(Action*), Action* (*constructor)(Action**, size_t));

/** Common for compress methods */
void compress_actions(ActionList lst);

#define ALWAYS (void*)1
#define FOR_ALL_CHILDREN(when, input, ...) do {					\
	for(size_t i=0; i<list_len(ma->children); i++) {			\
		Action* c = list_get(ma->children, i);					\
		if (when)										\
			c->input(c, __VA_ARGS__);							\
	}															\
} while(0)

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"

/** Situable as callback for list_foreach */
static void deref_action(void* _a) {
	Action* a = (Action*)_a;
	RC_REL(a);
}

/** Situable as callback for list_foreach */
static void ref_action(void* _a) {
	Action* a = (Action*)_a;
	RC_ADD(a);
}

#define MULTICHILD_DEALLOC(a) do {						\
	list_foreach((a)->children, &deref_action);			\
	list_free((a)->children);							\
} while(0)

#pragma GCC diagnostic pop
