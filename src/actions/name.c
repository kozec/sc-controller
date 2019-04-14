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
#include "props.h"
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

static char* describe(Action* a, ActionDescContext ctx) {
	NameModifier* n = container_of(a, NameModifier, action);
	return strbuilder_cpy(scc_parameter_as_string(n->params->items[0]));
}

static Action* compress(Action* a) {
	NameModifier* n = container_of(a, NameModifier, action);
	Action* child = scc_parameter_as_action(n->params->items[1]);
	scc_action_compress(&child);
	return child;
}

static Action* get_child(Action* a) {
	NameModifier* n = container_of(a, NameModifier, action);
	Action* child = scc_parameter_as_action(n->params->items[1]);
	RC_ADD(child);
	return child;
}

static Parameter* get_property(Action* a, const char* name) {
	NameModifier* n = container_of(a, NameModifier, action);
	MAKE_PARAM_PROPERTY(n->params->items[0], "name");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
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
	n->action.describe = &describe;
	n->action.get_property = &get_property;
	n->action.extended.get_child = &get_child;
	
	n->params = params;
	return (ActionOE)&n->action;
}


void scc_actions_init_name() {
	scc_param_checker_init(&pc, "sa");
	scc_action_register(KW_NAME, &name_constructor);
}

