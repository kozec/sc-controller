/**
 * SC Controller - Name modifier
 *
 * Simple modifier that stores name (description) for child action.
 * Used by GUI.
*/
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_NAME = "name";

typedef struct {
	Action				action;
	ParameterList		params;
} NameModifier;

ACTION_MAKE_TO_STRING(NameModifier, name, KW_NAME, NULL);

static void name_dealloc(Action* a) {
	NameModifier* n = container_of(a, NameModifier, action);
	list_free(n->params);
	free(n);
}

static Action* compress(Action* a) {
	NameModifier* n = container_of(a, NameModifier, action);
	Action* child = scc_parameter_as_action(n->params->items[1]);
	scc_action_compress(&child);
	return child;
}


static ActionOE name_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_copy_param_list(params);
	
	NameModifier* n = malloc(sizeof(NameModifier));
	if ((n == NULL) || (params == NULL)) {
		list_free(params);
		free(n);
		return (ActionOE)scc_oom_action_error();
	}
	scc_action_init(&n->action, KW_NAME, AF_MODIFIER, &name_dealloc, &name_to_string);
	n->action.compress = &compress;
	
	n->params = params;
	return (ActionOE)&n->action;
}


void scc_actions_init_name() {
	scc_param_checker_init(&pc, "sa");
	scc_action_register(KW_NAME, &name_constructor);
}
