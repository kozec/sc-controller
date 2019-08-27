/**
 * SC Controller - Ball modifier
 *
 * Emulates ball-like movement with inertia and friction.
 *
 * Reacts only to 'whole' or 'axis' inputs and sends generated
 * movements using 'extended.change' method.
*/
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "wholehaptic.h"
#include "tostring.h"
#include "internal.h"
#include "props.h"
#include <sys/time.h>
#include <tgmath.h>
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

const char* KW_BALL = "ball";
#define BALL_HAPTIC_FACTOR		60.0		/* Just magic number */
#define BALL_DEFAULT_FRICTION	10.0
#define BALL_DEFAULT_MASS		80.0
#define BALL_DEFAULT_MEAN_LEN	10
// If finger is lifter after movement slower than MIN_LIFT_VELOCITY roll doesn't happens
#define MIN_LIFT_VELOCITY		0.2
bool scc_action_is_mouse(Action* a);
bool scc_action_is_axis(Action* a);
bool scc_action_is_xy(Action* a);

typedef struct {
	Action				action;
	Action*				child;
	ParameterList		params;
	WholeHapticData		whdata;
	PadStickTrigger		what;
	dvec_t				sensitivity;
	dvec_t				velocity;
	double				friction;
	uint32_t			ampli;
	double				degree;
	double				radscale;
	double				mass;
	TaskID				roll_task;
	double				r, i, a;
	Dequeue				dq;
	double				last_time;
	ivec_t				old_pos;
	bool				old_pos_set;
} BallModifier;

ACTION_MAKE_TO_STRING(BallModifier, ball, KW_BALL, &pc);

WHOLEHAPTIC_MAKE_SET_HAPTIC(BallModifier, a->whdata);

static char* describe(Action* a, ActionDescContext ctx) {
	BallModifier* b = container_of(a, BallModifier, action);
	if (scc_action_is_mouse(b->child))
		return strbuilder_cpy("Trackball");
	if (scc_action_is_xy(b->child)) {
		char* rv = NULL;
		Parameter* px = scc_action_get_property_with_type(b->child, "x", PT_ACTION);
		Parameter* py = scc_action_get_property_with_type(b->child, "y", PT_ACTION);
		if ((px != NULL) && (py != NULL)) {
			Action* x = px->as_action(px);
			Action* y = py->as_action(py);
			if ((scc_action_is_axis(x) && scc_action_is_axis(y))
					|| (scc_action_is_mouse(x) && scc_action_is_mouse(y))) {
				Parameter* axis_x = scc_action_get_property_with_type(x, "axis", PT_INT);
				Parameter* axis_y = scc_action_get_property_with_type(y, "axis", PT_INT);
				if ((axis_x != NULL) && (axis_y != NULL)) {
					if ((axis_x->as_int(axis_x) == ABS_X) && (axis_y->as_int(axis_y) == ABS_Y)) {
						rv = strbuilder_cpy("Mouse-like LStick");
					} else if (((axis_x->as_int(axis_x) == REL_WHEEL) || (axis_x->as_int(axis_x) == REL_HWHEEL))
								&& ((axis_y->as_int(axis_y) == REL_WHEEL) || (axis_y->as_int(axis_y) == REL_HWHEEL))) {
						rv = strbuilder_cpy("Mouse Wheel");
					} else {
						rv = strbuilder_cpy("Mouse-like RStick");
					}
				}
				RC_REL(axis_x); RC_REL(axis_y);
			}
		}
		RC_REL(px); RC_REL(py);
		if (rv != NULL)
			return rv;
	}
	char* child_desc = scc_action_get_description(b->child, ctx);
	char* rv = strbuilder_fmt(child_desc ? "Ball(%s)" : "Ball", child_desc);
	free(child_desc);
	return rv;
}

static void ball_dealloc(Action* a) {
	BallModifier* b = container_of(a, BallModifier, action);
	dequeue_deinit(&b->dq);
	list_free(b->params);
	RC_REL(b->child);
	free(b);
}

void scc_ball_replace_child(Action* a, Action* new_child) {
	ASSERT(a->type == KW_BALL);
	BallModifier* b = container_of(a, BallModifier, action);
	RC_ADD(new_child);
	RC_REL(b->child);
	b->child = new_child;
}

static Action* compress(Action* a) {
	BallModifier* b = container_of(a, BallModifier, action);
	scc_action_compress(&b->child);
	// TODO:
	/*
	# ball(circular(...) has to be turned around
		if isinstance(self.action, CircularModifier):
			cm = self.action
			self.action = cm.action
			cm.action = self
			return cm
	*/
	return a;
}

static void set_sensitivity(Action *a, float x, float y, float z) {
	BallModifier* b = container_of(a, BallModifier, action);
	b->sensitivity.x = x;
	b->sensitivity.y = y;
}

/** Stops rolling of the 'ball' */
static void stop(BallModifier* b, Mapper* m) {
	dequeue_clear(&b->dq);
	if (b->roll_task != 0) {
		m->cancel(m, b->roll_task);
		b->roll_task = 0;
	}
}

static void add(BallModifier* b, float dx, float dy) {
	dequeue_avg(&b->dq, &b->velocity.x, &b->velocity.y);
	dequeue_add(&b->dq, dx * b->radscale, dy * b->radscale);
}

static void roll(Mapper* m, BallModifier* b) {
	// Compute time step
	double t = mono_time_d();
	double dt = t - b->last_time;
	b->last_time = t;
	
	// Free movement update velocity and compute movement
	dvec_t a, d, dv, v;
	double hyp = dvec_len(b->velocity);
	if (hyp != 0.0) {
		a.x = b->a * (fabs(b->velocity.x) / hyp);
		a.y = b->a * (fabs(b->velocity.y) / hyp);
	} else {
		a.x = b->a;
		a.y = b->a;
	}
	
	// Cap friction desceleration
	dv.x = fmin(fabs(b->velocity.x), a.x * dt);
	dv.y = fmin(fabs(b->velocity.y), a.y * dt);
	
	// compute new velocity
	v.x = b->velocity.x - copysign(dv.x, b->velocity.x);
	v.y = b->velocity.y - copysign(dv.y, b->velocity.y);
	
	// compute displacement
	d.x = (((v.x + b->velocity.x) / 2.0) * dt) / b->radscale;
	d.y = (((v.y + b->velocity.y) / 2.0) * dt) / b->radscale;
	
	vec_cpy(b->velocity, v);
	
	if (b->child->extended.change != NULL) {
		// TODO: Maybe remember what started rolling
		b->child->extended.change(b->child, m,
			d.x * b->sensitivity.x, d.y * b->sensitivity.y, b->what);
	}
	
	if ((fabs(d.x) > 0.001) || (fabs(d.y) >= 0.001)) {
		wholehaptic_change(&b->whdata, m, d.x, d.y);
		b->roll_task = m->schedule(m, 2, (MapperScheduleCallback)&roll, b);
	}
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	BallModifier* b = container_of(a, BallModifier, action);
	b->what = what;
	if ((what == PST_STICK) || ((m->get_flags(m) & CF_HAS_RSTICK) && (what == PST_RPAD))) {
		// Special case, ball used on physical stick
		b->child->whole(b->child, m, x, y, what);
		return;
	}
	if (m->is_touched(m, what)) {
		double t = mono_time_d();
		if (b->old_pos_set && m->was_touched(m, what)) {
			double dt = t - b->last_time;
			if (dt < 0.0075) return;
			double dx = (double)(x - b->old_pos.x);
			double dy = (double)(y - b->old_pos.y);
			// LOG("Added movement over %g", dt);
			add(b, dx / dt, dy / dt);
			if (b->child->extended.change != NULL) {
				wholehaptic_change(&b->whdata, m, dx, dy);
				b->child->extended.change(b->child, m,
					dx * b->sensitivity.x, dy * b->sensitivity.y, what);
			}
		} else {
			stop(b, m);
		}
		b->old_pos_set = true;
		b->old_pos.x = x;
		b->old_pos.y = y;
		b->last_time = t;
	} else if (m->was_touched(m, what)) {
		b->old_pos_set = false;
		double velocity = dvec_len(b->velocity);
		if (velocity > MIN_LIFT_VELOCITY)
			b->roll_task = m->schedule(m, 2, (MapperScheduleCallback)&roll, b);
	}
}

static Action* get_child(Action* a) {
	BallModifier* b = container_of(a, BallModifier, action);
	RC_ADD(b->child);
	return b->child;
}

static Parameter* get_property(Action* a, const char* name) {
	BallModifier* b = container_of(a, BallModifier, action);
	MAKE_FLOAT_PROPERTY(b->friction, "friction");
	MAKE_DVEC_PROPERTY(b->sensitivity, "sensitivity");
	MAKE_HAPTIC_PROPERTY(b->whdata.hdata, "haptic");
	MAKE_INT_PROPERTY(b->ampli, "ampli");
	MAKE_FLOAT_PROPERTY(b->degree, "degree");
	MAKE_FLOAT_PROPERTY(b->radscale, "radscale");
	MAKE_FLOAT_PROPERTY(b->mass, "mass");
	MAKE_FLOAT_PROPERTY(b->r, "r");
	MAKE_FLOAT_PROPERTY(b->i, "i");
	MAKE_FLOAT_PROPERTY(b->a, "a");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE ball_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	BallModifier* b = malloc(sizeof(BallModifier));
	if (b == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&b->action, KW_BALL,
					AF_MODIFIER | AF_MOD_SENSITIVITY | AF_MOD_FEEDBACK
						| AF_MOD_SMOOTH | AF_MOD_DEADZONE,
					&ball_dealloc, &ball_to_string);
	b->action.compress = &compress;
	b->action.whole = &whole;
	b->action.get_property = &get_property;
	b->action.describe = &describe;
	b->action.extended.get_child = &get_child;
	b->action.extended.set_haptic = &set_haptic;
	b->action.extended.set_sensitivity = &set_sensitivity;
	
	b->friction = scc_parameter_as_float(params->items[0]);
	b->mass = scc_parameter_as_float(params->items[1]);
	b->r = scc_parameter_as_float(params->items[3]);
	b->ampli = scc_parameter_as_int(params->items[4]);
	b->degree = scc_parameter_as_float(params->items[5]);
	b->child = scc_parameter_as_action(params->items[6]);
	
	size_t mean_len = scc_parameter_as_int(params->items[2]);
	double fampli = scc_parameter_as_float(params->items[4]);
	b->radscale = (b->degree * M_PI / 180.0) / fampli;
	b->i = (2.0 * b->mass * (b->r * b->r)) / 5.0;
	b->a = b->r * b->friction / b->i;
	vec_set(b->sensitivity, 1.0, 1.0);
	vec_set(b->velocity, 0, 0);
	vec_set(b->old_pos, 0, 0);
	b->roll_task = 0;
	b->last_time = mono_time_d();
	b->old_pos_set = false;
	
	wholehaptic_init(&b->whdata);
	if (!dequeue_init(&b->dq, mean_len)) {
		free(b);
		list_free(params);
		return (ActionOE)scc_oom_action_error();
	}
	
	b->params = params;
	RC_ADD(b->child);
	
	return (ActionOE)&b->action;
}


void scc_actions_init_ball() {
	scc_param_checker_init(&pc, "f+?f+?c?f+?ui32?f+?a");
	scc_param_checker_set_defaults(&pc, BALL_DEFAULT_FRICTION,
			BALL_DEFAULT_MASS, BALL_DEFAULT_MEAN_LEN,
			// r, ampli, degree - no idea if anyone ever tried to change those
			0.02, 65536, 40.0);
	scc_action_register(KW_BALL, &ball_constructor);
}

