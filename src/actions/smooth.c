/**
 * SC Controller - Smooth modifier
 *
 * Smooths pad movements
*/
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"
#include "props.h"
#include <sys/time.h>
#include <tgmath.h>
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_SMOOTH = "smooth";

typedef struct {
	Action				action;
	Action*				child;
	double				multiplier;
	double				filter;
	double*				weights;
	double				w_sum;
	Dequeue				dq;
	AxisValue			last_pos_x;
	AxisValue			last_pos_y;
} SmoothModifier;


static char* smooth_to_string(Action* a) {
	SmoothModifier* s = container_of(a, SmoothModifier, action);
	ParameterList l = scc_inline_param_list(
			scc_new_int_parameter(dequeue_len(&s->dq)),
			scc_new_float_parameter(s->multiplier),
			scc_new_float_parameter(s->filter),
			scc_new_action_parameter(s->child)
	);
	
	l = scc_param_checker_strip_defaults(&pc, l);
	char* strl = scc_param_list_to_string(l);
	char* rv = (strl == NULL) ? NULL : strbuilder_fmt("smooth(%s)", strl);
	
	list_free(l);
	free(strl);
	return rv;
}

MODIFIER_MAKE_DESCRIBE(SmoothModifier, "%s (smooth)", "%s (smooth)");

static void smooth_dealloc(Action* a) {
	SmoothModifier* s = container_of(a, SmoothModifier, action);
	RC_REL(s->child);
	free(s->weights);
	free(s);
}


static Action* compress(Action* a) {
	SmoothModifier* s = container_of(a, SmoothModifier, action);
	scc_action_compress(&s->child);
	return a;
}

static Action* get_child(Action* a) {
	SmoothModifier* s = container_of(a, SmoothModifier, action);
	RC_ADD(s->child);
	return s->child;
}

static Parameter* get_property(Action* a, const char* name) {
	SmoothModifier* s = container_of(a, SmoothModifier, action);
	MAKE_FLOAT_PROPERTY(s->multiplier, "multiplier");
	MAKE_FLOAT_PROPERTY(s->filter, "filter");
	MAKE_INT_PROPERTY(dequeue_len(&(s->dq)), "level");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


/** Computes weighted average from all accumulated positions */
static void get_pos(SmoothModifier* s, AxisValue* x, AxisValue* y) {
	double _x = 0;
	double _y = 0;
	for(size_t i=0; i<dequeue_len(&s->dq); i++) {
		_x += s->dq.items[i].x * s->weights[i];
		_y += s->dq.items[i].y * s->weights[i];
	}
	*x = _x / s->w_sum;
	*y = _y / s->w_sum;
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	SmoothModifier* s = container_of(a, SmoothModifier, action);
	if ((what == PST_STICK) || ((m->get_flags(m) & CF_HAS_RSTICK) && (what == PST_RPAD))) {
		s->child->whole(s->child, m, x, y, what);
	} else if (m->is_touched(m, what)) {
		if ((s->last_pos_x == 0) && (s->last_pos_y == 0)) {
			// Just pressed - fill deque with current position
			for(size_t i=0; i<dequeue_len(&s->dq); i++)
				dequeue_add(&s->dq, x, y);
			get_pos(s, &x, &y);
		} else {
			// Pressed for longer time
			dequeue_add(&s->dq, x, y);
			get_pos(s, &x, &y);
		}
		if ((abs(s->last_pos_x - x) + abs(s->last_pos_y - y)) > s->filter)
			s->child->whole(s->child, m, x, y, what);
		s->last_pos_x = x;
		s->last_pos_y = y;
	} else {
		// Pad was just released
		get_pos(s, &x, &y);
		s->child->whole(s->child, m, x, y, what);
		s->last_pos_x = s->last_pos_y = 0;
	}
}


static ActionOE smooth_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	SmoothModifier* s = malloc(sizeof(SmoothModifier));
	if (s == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&s->action, KW_SMOOTH, AF_MODIFIER, &smooth_dealloc, &smooth_to_string);
	s->action.get_property = &get_property;
	s->action.describe = &describe;
	s->action.compress = &compress;
	s->action.whole = &whole;
	s->action.extended.get_child = &get_child;
	
	size_t level = scc_parameter_as_int(params->items[0]);
	s->multiplier = scc_parameter_as_float(params->items[1]);
	s->filter = scc_parameter_as_float(params->items[2]);
	s->child = scc_parameter_as_action(params->items[3]);
	list_free(params);
	s->last_pos_x = s->last_pos_y = 0;
	s->dq.items = NULL;
	s->weights = malloc(sizeof(double) * level);
	if ((s->weights == NULL) || !dequeue_init(&s->dq, level)) {
		dequeue_deinit(&s->dq);
		free(s->weights);
		free(s);
		return (ActionOE)scc_oom_action_error();
	}
	s->w_sum = 0;
	for(size_t i=0; i<level; i++) {
		s->weights[i] = pow(s->multiplier, level-i-1);
		s->w_sum += s->weights[i];
	}
	
	RC_ADD(s->child);
	return (ActionOE)&s->action;
}


void scc_actions_init_smooth() {
	scc_param_checker_init(&pc, "c?f?f?a");
	scc_param_checker_set_defaults(&pc, 8, 0.75, 2.0);
	scc_action_register(KW_SMOOTH, &smooth_constructor);
}

