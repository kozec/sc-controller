/*
 * SC-Controller - MouseAbsAction
 *
 * Maps gyro rotation or position on pad to immediate mouse movement, similary
 * to how GyroAbsAction maps gyro rotation to gamepad stick.
 *
 * Controlls mouse movement in either vertical or horizontal direction
 * or scroll wheel.
 */
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_MOUSEABS = "mouseabs";
#define MOUSE_ABS_FACTOR 0.005	/* Just random number to put default sensitivity into sane range */

typedef struct {
	Action				action;
	Parameter*			param;
	Axis				axis;
	dvec_t				sensitivity;
} MouseAbsAction;


static char* mouseabs_to_string(Action* a) {
	MouseAbsAction* b = container_of(a, MouseAbsAction, action);
	ParameterList params = scc_make_param_list(b->param);
	if (params == NULL) return NULL; // OOM
	char* parmsstr = scc_param_list_to_string(params);
	list_free(params);
	if (parmsstr == NULL) return NULL;	// OOM
	
	char* rv = strbuilder_fmt("mouseabs(%s)", parmsstr);
	free(parmsstr);
	return rv;
}

static void mouseabs_dealloc(Action* a) {
	MouseAbsAction* b = container_of(a, MouseAbsAction, action);
	RC_REL(b->param);
	free(b);
}

static void axis(Action* a, Mapper* m, AxisValue value, PadStickTrigger what) {
	MouseAbsAction* b = container_of(a, MouseAbsAction, action);
	double d = (double)value * b->sensitivity.x * MOUSE_ABS_FACTOR;
	if (b->axis == REL_X)
		m->move_mouse(m, d, 0);
	else if (b->axis == REL_Y)
		m->move_mouse(m, 0, d);
	else if (b->axis == REL_WHEEL)
		m->move_wheel(m, 0, -d);
	else if (b->axis == REL_HWHEEL)
		m->move_wheel(m, d, 0);
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	MouseAbsAction* b = container_of(a, MouseAbsAction, action);
	double dx = (double)x * b->sensitivity.x * MOUSE_ABS_FACTOR;
	double dy = (double)y * b->sensitivity.y * MOUSE_ABS_FACTOR;
	m->move_mouse(m, dx, dy);
}


static ActionOE mouseabs_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	MouseAbsAction* b = malloc(sizeof(MouseAbsAction));
	if (b == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&b->action, KW_MOUSEABS,
					AF_ACTION | AF_MOD_SENSITIVITY | AF_MOD_SENS_Z | AF_MOD_DEADZONE,
					&mouseabs_dealloc, &mouseabs_to_string);
	b->action.axis = &axis;
	b->action.whole = &whole;
	
	b->axis = scc_parameter_as_int(params->items[0]);
	b->sensitivity.x = b->sensitivity.y = scc_parameter_as_float(params->items[1]);
	b->param = params->items[0];
	
	RC_ADD(b->param);
	list_free(params);
	return (ActionOE)&b->action;
}

void scc_actions_init_mouseabs() {
	// 1024 == REL_X
	scc_param_checker_init(&pc, "i(1024,1039)?f?");
	scc_param_checker_set_defaults(&pc, 1024, 1.0);
	scc_action_register(KW_MOUSEABS, &mouseabs_constructor);
}

