/*
 * SC-Controller - Mode shift
 *
 * Assings multiple actions to same input and choses between them
 * based on condition.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "scc/tools.h"
#include "tostring.h"
#include <stdlib.h>
#include <string.h>

static const char* KW_RING = "ring";
static ParamChecker pc;
#define DEAFAULT_RADIUS		0.5

typedef struct {
	Action				action;
	ParameterList		params;
	double				radius;
	double				radius_m;			// radius, premultiplied
	Action*				inner;
	Action*				outer;
	Action*				active;
} Ring;


ACTION_MAKE_TO_STRING(Ring, ring, KW_RING, NULL);

static void ring_dealloc(Action* a) {
	Ring* r = container_of(a, Ring, action);
	list_free(r->params);
	RC_REL(r->inner);
	RC_REL(r->outer);
	free(r);
}

static Action* compress(Action* a) {
	Ring* r = container_of(a, Ring, action);
	scc_action_compress(&r->inner);
	scc_action_compress(&r->outer);
	return a;
}

static void whole(Action* a, Mapper* m, AxisValue _x, AxisValue _y, PadStickTrigger what) {
	Ring* r = container_of(a, Ring, action);
	double x = (double)_x;
	double y = (double)_y;
	if ((what == PST_STICK) || m->is_touched(m, what)) {
		Action* action  = NULL;
		double angle = atan2(x, y);
		double distance = sqrt(x * x + y * y);
		if (distance < r->radius_m) {
			action = r->inner;
			distance /= r->radius;
		} else {
			action = r->outer;
			distance = (distance - r->radius_m) / (1.0 - r->radius);
		}
		x = distance * sin(angle);
		y = distance * cos(angle);
		if (action == r->active) {
			action->whole(action, m, x, y, what);
		} else if (what == PST_STICK) {
			// Stick has crossed radius border, so active action is changing.
			// Simulate centering stick for former...
			r->active->whole(r->active, m, 0, 0, what);
			// ... and moving it back for new active child action
			action->whole(action, m, x, y, what);
		} else {
			// Finger crossed radius border, so active action is changing.
			// Simulate releasing pad for former...
			// TODO: pressed / not pressed manipulation here
			// TODO: m->set_button(m, what, false);
			r->active->whole(r->active, m, 0, 0, what);
			// ... and touching it for new active child action
			// TODO: bool was = m->was_touched(m, what);
			// TODO: m->set_button(m, what, true);
			// TODO: m->set_was_pressed(m, what, false);
			action->whole(action, m, x, y, what);
			// TODO: m->set_was_pressed(m, what, was);
			r->active = action;
		}
	} else if ((m->was_touched(m, what)) || ((r->active != NULL) && (what == PST_STICK) && (x == 0) && (y == 0))) {
		// Stick is recentered or pad was just released
		r->active->whole(r->active, m, x, y, what);
		r->active = NULL;
	}
}


static void set_haptic(Action* a, HapticData hdata) {
	Ring* r = container_of(a, Ring, action);
	if (r->inner->extended.set_haptic != NULL)
		r->inner->extended.set_haptic(r->inner, hdata);
	if (r->outer->extended.set_haptic != NULL)
		r->outer->extended.set_haptic(r->outer, hdata);
}

static void set_sensitivity(Action* a, float x, float y, float z) {
	Ring* r = container_of(a, Ring, action);
	if (r->inner->extended.set_sensitivity != NULL)
		r->inner->extended.set_sensitivity(r->inner, x, y, z);
	if (r->outer->extended.set_sensitivity != NULL)
		r->outer->extended.set_sensitivity(r->outer, x, y, z);
}

static Parameter* get_property(Action* a, const char* name) {
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE ring_constructor(const char* keyword, ParameterList params) {
	params = scc_param_checker_fill_defaults(&pc, params);
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	
	Ring* r = malloc(sizeof(Ring));	// why don't you give me a call?
	if (r == NULL) {
		list_free(params);
		return (ActionOE)scc_oom_action_error();
	}
	
	scc_action_init(&r->action, KW_RING, AF_ACTION, &ring_dealloc, &ring_to_string);
	
	r->action.compress = &compress;
	r->action.whole = &whole;
	r->action.get_property = &get_property;
	r->action.extended.set_sensitivity = &set_sensitivity;
	r->action.extended.set_haptic = &set_haptic;
	
	r->params = params;
	r->radius = scc_parameter_as_float(params->items[0]);
	r->inner = scc_parameter_as_action(params->items[1]);
	r->outer = scc_parameter_as_action(params->items[2]);
	r->radius_m = STICK_PAD_MAX * r->radius;
	r->active = NULL;
	
	return (ActionOE)&r->action;
}

void scc_actions_init_ring() {
	scc_param_checker_init(&pc, "f? aa?");
	scc_param_checker_set_defaults(&pc, 0.5, NoAction);
	scc_action_register(KW_RING, &ring_constructor);
}

