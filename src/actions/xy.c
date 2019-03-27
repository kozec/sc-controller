/**
 * SC-Controller - XYAction and RelXYAction
 *
 * XYAction splits two axes of stick or pad between two different actions.
 *
 * RelXYAction does the same, but remembers where pad was originally touched
 * and treats that place as center. See https://github.com/kozec/sc-controller/issues/390
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "wholehaptic.h"
#include "props.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

static const char* KW_XY = "XY";
static const char* KW_RELXY = "relXY";
static ParamChecker pc;

typedef struct {
	Action				action;
	HapticData			hdata;
	HapticData			bighaptic;
	dvec_t				haptic_counter;
	ivec_t				old_pos;
	ivec_t				origin;
	bool				is_relative;
	bool				inner_circle;
	Action*				x;
	Action*				y;
} XYAction;


static char* xy_to_string(Action* a) {
	XYAction* xy = container_of(a, XYAction, action);
	ParameterList l = scc_param_checker_strip_defaults(&pc,
		scc_inline_param_list(
			scc_new_action_parameter(xy->x),
			scc_new_action_parameter(xy->y)
		)
	);
	char* strl = scc_param_list_to_string(l);
	char* rv = (strl == NULL) ? NULL : strbuilder_fmt("%s(%s)", KW_XY, strl);
	
	list_free(l);
	free(strl);
	return rv;
}

static char* describe(Action* a, ActionDescContext ctx) {
	XYAction* xy = container_of(a, XYAction, action);
	// TODO: Special cases for default stick bindings
	switch (ctx) {
	case AC_STICK:
	case AC_PAD:
		return strbuilder_fmt("%s\n%s",
			scc_action_get_description(xy->x, ctx),
			scc_action_get_description(xy->y, ctx));
	default:
		return strbuilder_fmt("%s %s",
			scc_action_get_description(xy->x, ctx),
			scc_action_get_description(xy->y, ctx));
	}
}

static void xy_dealloc(Action* a) {
	XYAction* xy = container_of(a, XYAction, action);
	RC_REL(xy->x);
	RC_REL(xy->y);
	free(xy);
}

static inline bool is_inner_circle(AxisValue x, AxisValue y) {
	double distance = sqrt(POW2(x) + POW2(y));
	return distance > (double)STICK_PAD_MAX * 2.0 / 3.0;
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	XYAction* xy = container_of(a, XYAction, action);
	// TODO: if self.haptic:
	if ((m->get_flags(m) & CF_HAS_RSTICK) && (what == PST_RIGHT)) {
		if (xy->x->axis) xy->x->axis(xy->x, m, x, what);
		if (xy->y->axis) xy->y->axis(xy->y, m, y, what);
		// TODO: Is this needed?
		// m.force_event.add(FE_PAD)
	} else if ((what == PST_LEFT) || (what == PST_RIGHT) || (what == PST_CPAD)) {
		// TODO: Special call for PAD as with old stuff?
		if (HAPTIC_ENABLED(&xy->hdata)) {
			if ((xy->is_relative) && (m->is_touched(m, what))) {
				if (!m->was_touched(m, what))
					vec_set(xy->origin, x, y);
				x -= xy->origin.x;
				y -= xy->origin.y;
			}
			
			if (m->was_touched(m, what)) {
				bool inner_circle = is_inner_circle(x, y);
				double distance = dvec_len(xy->haptic_counter);
				xy->haptic_counter.x += x - xy->old_pos.x;
				xy->haptic_counter.y += y - xy->old_pos.y;
				if (xy->inner_circle != inner_circle) {
					xy->inner_circle = inner_circle;
					m->haptic_effect(m, &xy->bighaptic);
				} else if (distance > xy->hdata.frequency) {
					vec_set(xy->haptic_counter, 0, 0);
					m->haptic_effect(m, &xy->hdata);
				}
			} else {
				xy->inner_circle = is_inner_circle(x, y);
			}
			vec_set(xy->old_pos, x, y);
		}
		if (xy->x->axis) xy->x->axis(xy->x, m, x, what);
		if (xy->y->axis) xy->y->axis(xy->y, m, y, what);
	} else {
		if (xy->x->axis) xy->x->axis(xy->x, m, x, what);
		if (xy->y->axis) xy->y->axis(xy->y, m, y, what);
	}
}

static void change(Action* a, Mapper* m, double dx, double dy, PadStickTrigger what) {
	XYAction* xy = container_of(a, XYAction, action);
	if (xy->x->extended.change) xy->x->extended.change(xy->x, m, dx, 0, what);
	if (xy->y->extended.change) xy->y->extended.change(xy->y, m, 0, dy, what);
}

static Action* compress(Action* _a) {
	XYAction* xy = container_of(_a, XYAction, action);
	scc_action_compress(&xy->x);
	scc_action_compress(&xy->y);
	return _a;
}

static void set_haptic(Action* _a, HapticData hdata) {
	XYAction* xy = container_of(_a, XYAction, action);
	if ((xy->x->extended.set_haptic != NULL) || (xy->y->extended.set_haptic != NULL)) {
		if (xy->x->extended.set_haptic != NULL)
			xy->x->extended.set_haptic(xy->x, hdata);
		if (xy->y->extended.set_haptic != NULL)
			xy->y->extended.set_haptic(xy->y, hdata);
	} else {
		// Child actions have no feedback support, so XY will be doing it instead
		xy->hdata = hdata;
		xy->bighaptic = hdata;
		uint64_t amplitude = (uint64_t)hdata.amplitude * 4;
		xy->bighaptic.amplitude = (uint16_t)((amplitude > 0xFFFF) ? 0xFFFF : amplitude);
	}
}

static void set_sensitivity(Action* _a, float x, float y, float z) {
	XYAction* xy = container_of(_a, XYAction, action);
	if (xy->x->extended.set_sensitivity != NULL)
		xy->x->extended.set_sensitivity(xy->x, x, 1, 1);
	if (xy->y->extended.set_sensitivity != NULL)
		xy->y->extended.set_sensitivity(xy->y, y, 1, 1);
}

static Parameter* get_property(Action* a, const char* name) {
	XYAction* xy = container_of(a, XYAction, action);
	if (0 == strcmp(name, "sensitivity")) {
		// Little magic happens here...
		Parameter* params[] = {
			xy->x->get_property == NULL ? NULL : xy->x->get_property(xy->x, "sensitivity"),
			xy->y->get_property == NULL ? NULL : xy->y->get_property(xy->y, "sensitivity")
		};
		for (int i=0; i<2; i++) {
			if ((params[i] != NULL) && ((params[i]->type & PT_TUPLE) != 0)
					&& (scc_parameter_tuple_get_count(params[i]) > 0)) {
				Parameter* child = scc_parameter_tuple_get_child(params[i], 0);
				RC_ADD(child);
				RC_REL(params[i]);
				params[i] = child;
			} else {
				RC_REL(params[i]);
				params[i] = scc_new_float_parameter(1.0);
			}
		}
		return scc_new_tuple_parameter(2, params);
	} else if (0 == strcmp(name, "x")) {
		return scc_new_action_parameter(xy->x);
	} else if (0 == strcmp(name, "y")) {
		return scc_new_action_parameter(xy->y);
	}
	MAKE_HAPTIC_PROPERTY(xy->hdata, "haptic");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE xy_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	XYAction* xy = malloc(sizeof(XYAction));
	if (xy == NULL) {
		list_free(params);
		return (ActionOE)scc_oom_action_error();
	}
	scc_action_init(&xy->action, KW_XY, AF_ACTION, &xy_dealloc, &xy_to_string);
	HAPTIC_DISABLE(&xy->hdata);
	vec_set(xy->old_pos, 0, 0);
	vec_set(xy->origin, 0, 0);
	vec_set(xy->haptic_counter, 0, 0);
	xy->is_relative = (0 == strcmp(keyword, KW_RELXY));
	xy->x = scc_parameter_as_action(params->items[0]);
	xy->y = scc_parameter_as_action(params->items[1]);
	xy->action.describe = &describe;
	xy->action.compress = &compress;
	xy->action.whole = &whole;
	xy->action.get_property = &get_property;
	xy->action.extended.change = &change;
	xy->action.extended.set_haptic = &set_haptic;
	xy->action.extended.set_sensitivity = &set_sensitivity;
	
	RC_ADD(xy->x);
	RC_ADD(xy->y);
	list_free(params);
	return (ActionOE)&xy->action;
}

void scc_actions_init_xy() {
	scc_param_checker_init(&pc, "aa?");
	scc_param_checker_set_defaults(&pc, NULL);
	scc_action_register(KW_XY, &xy_constructor);
	scc_action_register(KW_RELXY, &xy_constructor);
}
