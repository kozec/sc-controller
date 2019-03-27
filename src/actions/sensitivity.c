/**
 * SC Controller - Sensitivity modifier
 *
 * Sets input or output sensitivity to if action suppors it.
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

static const char* KW_SENSITIVITY = "sens";

typedef struct {
	Action				action;
	Action*				child;
	ParameterList		params;
} SensitivityModifier;

ACTION_MAKE_TO_STRING(SensitivityModifier, sensitivity, KW_SENSITIVITY, &pc);

static char* describe(Action* a, ActionDescContext ctx) {
	SensitivityModifier* s = container_of(a, SensitivityModifier, action);
	return scc_action_get_description(s->child, ctx);
}

static void sensitivity_dealloc(Action* a) {
	SensitivityModifier* s = container_of(a, SensitivityModifier, action);
	list_free(s->params);
	RC_REL(s->child);
	free(s);
}

static Action* compress(Action* a) {
	SensitivityModifier* s = container_of(a, SensitivityModifier, action);
	scc_action_compress(&s->child);
	if (s->child->extended.set_sensitivity != NULL) {
		float x = scc_parameter_as_float(s->params->items[0]);
		float y = scc_parameter_as_float(s->params->items[1]);
		float z = scc_parameter_as_float(s->params->items[2]);
		s->child->extended.set_sensitivity(s->child, x, y, z);
		return s->child;
	} else if (s->child->extended.get_child != NULL) {
		Action* c = s->child;
		RC_ADD(c);
		do {
			Action* next_c = c->extended.get_child(c);
			if (next_c->extended.set_sensitivity != NULL) {
				float x = scc_parameter_as_float(s->params->items[0]);
				float y = scc_parameter_as_float(s->params->items[1]);
				float z = scc_parameter_as_float(s->params->items[2]);
				next_c->extended.set_sensitivity(next_c, x, y, z);
				RC_REL(next_c);
				RC_REL(c);
				return s->child;
			}
			RC_REL(c);
			c = next_c;
		} while (c->extended.get_child != NULL);
		RC_REL(c);
	}
	return a;
}

static Action* get_child(Action* a) {
	SensitivityModifier* s = container_of(a, SensitivityModifier, action);
	RC_ADD(s->child);
	return s->child;
}

static Parameter* get_property(Action* a, const char* name) {
	SensitivityModifier* s = container_of(a, SensitivityModifier, action);
	
	if (0 == strcmp(name, "sensitivity")) {
		static const uint8_t count = 3;
		for (uint8_t i=0; i<count; i++)
			RC_ADD(list_get(s->params, i));
		return scc_new_tuple_parameter(count, s->params->items);
	}
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE sensitivity_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	SensitivityModifier* s = malloc(sizeof(SensitivityModifier));
	if (s == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&s->action, KW_SENSITIVITY, AF_MODIFIER, &sensitivity_dealloc, &sensitivity_to_string);
	s->action.describe = &describe;
	s->action.compress = &compress;
	s->action.get_property = &get_property;
	s->action.extended.get_child = &get_child;
	
	s->params = params;
	s->child = scc_parameter_as_action(list_get(params, 3));
	RC_ADD(s->child);
	return (ActionOE)&s->action;
}


void scc_actions_init_sensitivity() {
	scc_param_checker_init(&pc, "ff?f?a");
	scc_param_checker_set_defaults(&pc, 1.0, 1.0);
	scc_action_register(KW_SENSITIVITY, &sensitivity_constructor);
}
