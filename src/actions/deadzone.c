/**
 * SC Controller - Deadzone modifier
 *
 * Smooths pad movements
*/
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "internal.h"
#include "tostring.h"
#include "props.h"
#include <tgmath.h>
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_DEADZONE = "deadzone";

#define JUMP_HARDCODED_LIMIT	5

typedef struct DeadzoneModifier DeadzoneModifier;
typedef void (*DeadzoneMode)(DeadzoneModifier* d, AxisValue* x, AxisValue* y, AxisValue range);

struct DeadzoneModifier {
	Action				action;
	Action*				child;
	ParameterList		params;
	AxisValue			upper;
	AxisValue			lower;
	Action*				old_child;
	Parameter*			mode_param;
	DeadzoneMode		mode;
};


ACTION_MAKE_TO_STRING(DeadzoneModifier, deadzone, KW_DEADZONE, &pc);

MODIFIER_MAKE_DESCRIBE(DeadzoneModifier, "%s (with deadzone)", "%s\n(with deadzone)");

static void deadzone_dealloc(Action* a) {
	DeadzoneModifier* d = container_of(a, DeadzoneModifier, action);
	list_free(d->params);
	RC_REL(d->child);
	RC_REL(d->old_child);
	free(d);
}


/** If input value is out of deadzone range, output value is zero */
static void mode_cut(DeadzoneModifier* d, AxisValue* x, AxisValue* y, AxisValue range) {
	if (*y == 0) {
		// Small optimalization for 1D input, for example trigger
		if ((abs(*x) < d->lower) || (abs(*x) > d->upper))
			*x = 0;
	} else {
		AxisValue distance = sqrt(POW2(*x) + POW2(*y));
		if ((distance < d->lower) || (distance > d->upper)) {
			*x = 0;
			*y = 0;
		}
	}
}

/**
 * If input value bellow deadzone range, output value is zero
 * If input value is above deadzone range,
 * output value is 1 (or maximum allowed)
 */
static void mode_round(DeadzoneModifier* d, AxisValue* x, AxisValue* y, AxisValue range) {
	if (*y == 0) {
		// Small optimalization for 1D input, for example trigger
		if (abs(*x) > d->upper) {
			*x = copysign(range, *x);
		} else if (abs(*x) < d->lower) {
			*x = 0;
		}
	} else {
		AxisValue distance = sqrt(POW2(*x) + POW2(*y));
		if (distance < d->lower) {
			*x = 0;
			*y = 0;
		} else if (distance > d->upper) {
			double angle = atan2(*x, *y);
			*x = (AxisValue)((double)range * sin(angle));
			*y = (AxisValue)((double)range * cos(angle));
		}
	}
}

/*
 * Input value is scaled, so entire output range is covered by
 * reduced input range of deadzone.
 */
static void mode_linear(DeadzoneModifier* d, AxisValue* x, AxisValue* y, AxisValue range) {
	if (*y == 0) {
		// Small optimalization for 1D input, for example trigger
		double distance = ((double)(*x - d->lower) / (double)(d->upper - d->lower)) * range;
		AxisValue clamped = clamp(0, distance, range);
		*x = copysign(clamped, *x);
	} else {
		double distance = sqrt(POW2(*x) + POW2(*y));
		distance = clamp(d->lower, distance, d->upper);
		distance = (distance - d->lower) / (d->upper - d->lower) * range;
		
		double angle = atan2(*x, *y);
		*x = (AxisValue)(distance * sin(angle));
		*y = (AxisValue)(distance * cos(angle));
	}
}

/**
 * https://github.com/kozec/sc-controller/issues/356
 * Inversion of LINEAR; input value is scaled so entire input range is
 * mapped to range of deadzone.
 */
static void mode_minimum(DeadzoneModifier* d, AxisValue* x, AxisValue* y, AxisValue range) {
	if (*y == 0) {
		// Small optimalization for 1D input, for example trigger
		if (abs(*x) < JUMP_HARDCODED_LIMIT) {
			*x = 0;
		} else {
			double tmp = ((double)abs(*x) / (double)range * (double)(d->upper - d->lower)) + d->lower;
			*x = copysign(tmp, *x);
		}
	} else {
		double distance = sqrt(POW2(*x) + POW2(*y));
		if (distance < JUMP_HARDCODED_LIMIT) {
			*x = 0;
			*y = 0;
		} else {
			distance = (distance / (double)range * (double)(d->upper - d->lower)) + d->lower;
			double angle = atan2(*x, *y);
			*x = distance * sin(angle);
			*y = distance * cos(angle);
		}
	}
}

static Action* compress(Action* a) {
	DeadzoneModifier* d = container_of(a, DeadzoneModifier, action);
	scc_action_compress(&d->child);
	if (d->child->type == KW_BALL) {
		// Special case where BallModifier has to be applied before
		// deadzone is computed
		Action* ball = d->child;
		Action* new_child = ball->extended.get_child(ball);
		scc_ball_replace_child(ball, a);
		d->old_child = d->child;
		d->child = new_child;
		return ball;
	} else if (d->child->type == KW_GYROABS) {
		// Another special case, GyroAbs has to handle deadzone
		// only after math is finished
		scc_gyroabs_set_deadzone_mod(d->child, a);
		return d->child;
	}
	return a;
}

void scc_deadzone_apply(Action* a, AxisValue* value) {
	ASSERT(a->type == KW_DEADZONE);
	DeadzoneModifier* d = container_of(a, DeadzoneModifier, action);
	AxisValue trash = 0;
	d->mode(d, value, &trash, STICK_PAD_MAX);
}

static Parameter* get_property(Action* a, const char* name) {
	DeadzoneModifier* d = container_of(a, DeadzoneModifier, action);
	MAKE_INT_PROPERTY(d->upper, "upper");
	MAKE_INT_PROPERTY(d->lower, "lower");
	MAKE_PARAM_PROPERTY(d->mode_param, "mode");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static void axis(Action* a, Mapper* m, AxisValue value, PadStickTrigger what) {
	DeadzoneModifier* d = container_of(a, DeadzoneModifier, action);
	AxisValue trash = 0;
	d->mode(d, &value, &trash, STICK_PAD_MAX);
	d->child->axis(d->child, m, value, what);
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	DeadzoneModifier* d = container_of(a, DeadzoneModifier, action);
	AxisValue ax_pos = pos;
	AxisValue ax_old_pos = old_pos;
	AxisValue trash = 0;
	
	d->mode(d, &ax_pos, &trash, TRIGGER_MAX);
	d->mode(d, &ax_old_pos, &trash, TRIGGER_MAX);
	
	d->child->trigger(d->child, m, ax_pos, ax_old_pos, what);
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	DeadzoneModifier* d = container_of(a, DeadzoneModifier, action);
	d->mode(d, &x, &y, STICK_PAD_MAX);
	d->child->whole(d->child, m, x, y, what);
}

static void gyro(Action* a, Mapper* m, const struct GyroInput* value) {
	DeadzoneModifier* d = container_of(a, DeadzoneModifier, action);
	d->child->gyro(d->child, m, value);
}

static Action* get_child(Action* a) {
	DeadzoneModifier* d = container_of(a, DeadzoneModifier, action);
	RC_ADD(d->child);
	return d->child;
}


static ActionOE deadzone_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	const char* modestr = scc_parameter_as_string(params->items[0]);
	DeadzoneMode mode;
	if (0 == strcmp("CUT", modestr)) {
		mode = &mode_cut;
	} else if (0 == strcmp("ROUND", modestr)) {
		mode = &mode_round;
	} else if (0 == strcmp("LINEAR", modestr)) {
		mode = &mode_linear;
	} else if (0 == strcmp("MINIMUM", modestr)) {
		mode = &mode_minimum;
	} else {
		ParamError* e = scc_new_invalid_parameter_type_error(KW_DEADZONE, 0, params->items[0]);
		list_free(params);
		return (ActionOE)e;
	}
	
	DeadzoneModifier* d = malloc(sizeof(DeadzoneModifier));
	if (d == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&d->action, KW_DEADZONE, AF_MODIFIER, &deadzone_dealloc, &deadzone_to_string);
	d->action.get_property = &get_property;
	d->action.describe = &describe;
	d->action.compress = &compress;
	d->action.trigger = &trigger;
	d->action.whole = &whole;
	d->action.gyro = &gyro;
	d->action.axis = &axis;
	d->action.extended.get_child = &get_child;
	
	d->lower = max(0, scc_parameter_as_int(params->items[1]));
	d->upper = min(STICK_PAD_MAX, scc_parameter_as_int(params->items[2]));
	d->child = scc_parameter_as_action(params->items[3]);
	d->mode_param = params->items[0];
	d->old_child = NULL;
	d->params = params;
	d->mode = mode;
	
	RC_ADD(d->child);
	return (ActionOE)&d->action;
}


void scc_actions_init_deadzone() {
	scc_param_checker_init(&pc, "s?ii?a");
	scc_param_checker_set_defaults(&pc, "CUT", STICK_PAD_MAX);
	scc_action_register(KW_DEADZONE, &deadzone_constructor);
}

