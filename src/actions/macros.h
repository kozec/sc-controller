/*
 * SC-Controller - Macros
 *
 * Common code for all macro-like actions and action with multiple child actions.
 */
#pragma once
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/action.h"
#include <stdlib.h>
#include <stdio.h>

typedef LIST_TYPE(Action) ActionList;


static char* ACTIONS_TO_STRING(ActionList l, const char* separator) {
	StrBuilder* sb = strbuilder_new();
	ListIterator it = iter_get(l);
	if ((sb == NULL) || (it == NULL))
		goto actions_to_string_fail;
	if (!strbuilder_add_all(sb, it, &scc_action_to_string, separator))
		goto actions_to_string_fail;
	iter_free(it);
	return strbuilder_consume(sb);
	
actions_to_string_fail:
	free(sb); iter_free(it);
	return NULL;
}

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
