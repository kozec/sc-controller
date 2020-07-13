/**
 * SC Controller - Rotate Input modifier
 *
 * Rotates touch or stick input along 'Z' axis
*/
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"
#include "props.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_ROTATE = "rotate";

typedef struct {
	Action				action;
	Action*				child;
	ParameterList		params;
	float				angle;
} RotateInputModifier;

ACTION_MAKE_TO_STRING(RotateInputModifier, rotate_input, KW_ROTATE, &pc);

static char* describe(Action* a, ActionDescContext ctx) {
	RotateInputModifier* r = container_of(a, RotateInputModifier, action);
	return scc_action_get_description(r->child, ctx);
}

static void rotate_input_dealloc(Action* a) {
	RotateInputModifier* r = container_of(a, RotateInputModifier, action);
	list_free(r->params);
	RC_REL(r->child);
	free(r);
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	RotateInputModifier* r = container_of(a, RotateInputModifier, action);
	float angle = r->angle * M_PI / -180.0;
	float rx = (float)x * cos(angle) - (float)y * sin(angle);
	float ry = (float)x * sin(angle) + (float)y * cos(angle);
	if (r->child->whole != NULL)
		r->child->whole(r->child, m, rx, ry, what);
}

static Action* compress(Action* a) {
	RotateInputModifier* r = container_of(a, RotateInputModifier, action);
	scc_action_compress(&r->child);
	return a;
}

static Action* get_child(Action* a) {
	RotateInputModifier* r = container_of(a, RotateInputModifier, action);
	RC_ADD(r->child);
	return r->child;
}

static Parameter* get_property(Action* a, const char* name) {
	RotateInputModifier* r = container_of(a, RotateInputModifier, action);
	MAKE_FLOAT_PROPERTY(r->angle, "angle");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE rotate_input_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	RotateInputModifier* r = malloc(sizeof(RotateInputModifier));
	if (r == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&r->action, KW_ROTATE, AF_MODIFIER,
				&rotate_input_dealloc, &rotate_input_to_string);
	r->action.get_property = &get_property;
	r->action.compress = &compress;
	r->action.describe = &describe;
	r->action.whole = &whole;
	r->action.extended.get_child = &get_child;
	
	r->child = scc_parameter_as_action(list_get(params, 1));
	r->angle = scc_parameter_as_float(list_get(params, 0));
	r->params = params;
	RC_ADD(r->child);
	return (ActionOE)&r->action;
}


void scc_actions_init_rotate_input() {
	scc_param_checker_init(&pc, "fa");
	scc_action_register(KW_ROTATE, &rotate_input_constructor);
}

