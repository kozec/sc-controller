#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include "scc/action.h"
#include "scc/error.h"
#include <stdlib.h>

typedef struct {
	Parameter				parameter;
	Action*					action;
} ActionParameter;


static char* action_param_to_string(Parameter* _p) {
	ActionParameter* p = container_of(_p, ActionParameter, parameter);
	return scc_action_to_string(p->action);
}

static Action* action_param_to_action(Parameter* _p) {
	ActionParameter* p = container_of(_p, ActionParameter, parameter);
	return p->action;
}

static void free_action_param(void* _p) {
	ActionParameter* p = container_of(_p, ActionParameter, parameter);
	RC_REL(p->action);
	free(p);
}


Parameter* scc_new_action_parameter(Action* a) {
	if (a == NULL) return NULL;
	ASSERT(!(a->flags & AF_ERROR));
	ASSERT(!(a->flags & PT_ANY));			// I've managed to mess this up in the past :(
	ActionParameter* p = malloc(sizeof(ActionParameter));
	if (p == NULL) return NULL;
	RC_INIT(&p->parameter, &free_action_param);
	p->parameter.type = PT_ACTION;
	p->action = a;
	RC_ADD(a);
	
	p->parameter.as_action = &action_param_to_action;
	p->parameter.as_string = &scc_param_as_string_invalid;
	p->parameter.as_int = &scc_param_as_int_invalid;
	p->parameter.as_float = &scc_param_as_float_invalid;
	p->parameter.to_string = &action_param_to_string;
	return &p->parameter;
}
