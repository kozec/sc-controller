/**
 * SC Controller - Sensitivity modifier
 *
 * Sets input or output sensitivity to if action suppors it.
*/

#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_SENSITIVITY = "sens";

typedef struct {
	Action				action;
	ParameterList		params;
	HapticData			hdata;
} SensitivityModifier;

ACTION_MAKE_TO_STRING(SensitivityModifier, sensitivity, KW_SENSITIVITY, &pc);

static void sensitivity_dealloc(Action* a) {
	SensitivityModifier* s = container_of(a, SensitivityModifier, action);
	list_free(s->params);
	free(s);
}

static Action* compress(Action* a) {
	SensitivityModifier* s = container_of(a, SensitivityModifier, action);
	Action* child = scc_parameter_as_action(s->params->items[3]);
	scc_action_compress(&child);
	if (child->extended.set_sensitivity != NULL) {
		float x = scc_parameter_as_float(s->params->items[0]);
		float y = scc_parameter_as_float(s->params->items[1]);
		float z = scc_parameter_as_float(s->params->items[2]);
		child->extended.set_sensitivity(child, x, y, z);
	}
	return child;
}


static ActionOE sensitivity_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	SensitivityModifier* s = malloc(sizeof(SensitivityModifier));
	if (s == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&s->action, KW_SENSITIVITY, AF_MODIFIER, &sensitivity_dealloc, &sensitivity_to_string);
	s->action.compress = &compress;
	
	s->params = params;
	return (ActionOE)&s->action;
}


void scc_actions_init_sensitivity() {
	scc_param_checker_init(&pc, "ff?f?a");
	scc_param_checker_set_defaults(&pc, 1.0, 1.0);
	scc_action_register(KW_SENSITIVITY, &sensitivity_constructor);
}
