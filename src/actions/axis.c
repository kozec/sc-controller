#include "scc/utils/strbuilder.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/conversions.h"
#include "scc/action.h"
#include "props.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_AXIS = "axis";
static const char* KW_RAXIS = "raxis";
static const char* KW_HATUP = "hatup";
static const char* KW_HATDOWN = "hatdown";
static const char* KW_HATLEFT = "hatleft";
static const char* KW_HATRIGHT = "hatright";


typedef struct {
	Action			action;
	const char*		keyword;
	// With most of other actions, to_string reconstructs parameters
	// on the fly. But Axis is so complicated, it's worth to keep
	// copy of original list instead.
	ParameterList	params;
	Axis			axis;
	float			scale;
	AxisValue		min;
	AxisValue		max;
} AxisAction;

// Axis old_positions[NO_AXIS] = {};

static char* axis_to_string(Action* a) {
	AxisAction* ax = container_of(a, AxisAction, action);
	char* params = scc_param_list_to_string(ax->params);
	if (params != NULL) {
		char* rv = strbuilder_fmt("%s(%s)", ax->keyword, params);
		free(params);
		return rv;
	}
	return NULL;
}

static char* describe(Action* a, ActionDescContext ctx) {
	AxisAction* ax = container_of(a, AxisAction, action);
	return scc_describe_axis(ax->axis, (ax->min < ax->max) ? 1 : -1);
}

static void axis_dealloc(Action* a) {
	AxisAction* ax = container_of(a, AxisAction, action);
	list_free(ax->params);
	free(ax);
}

static bool apply_axis_params(AxisAction* ax, const char* keyword, ParameterList params) {
	ax->axis = (Axis)scc_parameter_as_int(params->items[0]);
	ax->scale = 1.0;
	if (strstr(keyword, "hat") == keyword) {
		ax->min = 0;
		ax->max = STICK_PAD_MIN + 1;
		if ((strstr(keyword, "down") != NULL) || (strstr(keyword, "right") != NULL))
			ax->max = STICK_PAD_MAX - 1;
		
		if (list_len(params) != 1)
			return false;
		if (strcmp(keyword, KW_HATUP) == 0)  ax->keyword = KW_HATUP;
		else if (strcmp(keyword, KW_HATDOWN) == 0)  ax->keyword = KW_HATDOWN;
		else if (strcmp(keyword, KW_HATLEFT) == 0)  ax->keyword = KW_HATLEFT;
		else if (strcmp(keyword, KW_HATRIGHT) == 0) ax->keyword = KW_HATRIGHT;
		else ASSERT(0);
	} else {
		ax->min = STICK_PAD_MIN;
		ax->max = STICK_PAD_MAX;
		if ((ax->axis == ABS_Z) || (ax->axis == ABS_RZ)) {
			// Triggers
			ax->min = TRIGGER_MIN;
			ax->max = TRIGGER_MAX;
		}
		if (list_len(params) > 1) { ax->min = (AxisValue)scc_parameter_as_int(params->items[1]); }
		if (list_len(params) > 2) { ax->max = (AxisValue)scc_parameter_as_int(params->items[2]); }
		
		if (strcmp(keyword, KW_AXIS) == 0) {
			ax->keyword = KW_AXIS;
		} else if (strcmp(keyword, KW_RAXIS) == 0) {
			AxisValue tmp = ax->min;
			ax->keyword = KW_RAXIS;
			ax->min = ax->max;
			ax->max = tmp;
		}
	}
	return true;
}

// clampAxis returns value clamped between min/max allowed for axis
AxisValue clamp_axis(Axis axis, double value) {
	switch (axis) {
	case ABS_Z:
	case ABS_RZ:
		// Triggers
		return max(TRIGGER_MIN, min(TRIGGER_MAX, value));
	case ABS_HAT0X:
	case ABS_HAT0Y:
		// DPAD
		return max(-1, min(1, value));
	default:
		// Everything else
		return max(STICK_PAD_MIN, min(STICK_PAD_MAX, value));
	}
}

static void button_press(Action* a, Mapper* m) {
	AxisAction* ax = container_of(a, AxisAction, action);
	m->set_axis(m, ax->axis, clamp_axis(ax->axis, ax->max));
	// mapper.syn_list.add(mapper.gamepad)
}

static void button_release (Action* a, Mapper* m) {
	AxisAction* ax = container_of(a, AxisAction, action);
	m->set_axis(m, ax->axis, clamp_axis(ax->axis, ax->min));
	// mapper.syn_list.add(mapper.gamepad)
}

static void axis(Action* a, Mapper* m, AxisValue value, PadStickTrigger what) {
	AxisAction* ax = container_of(a, AxisAction, action);
	double p = (((double)value * ax->scale) - (double)STICK_PAD_MIN) / (double)(STICK_PAD_MAX - STICK_PAD_MIN);
	p = (p * (double)(ax->max - ax->min)) + (double)ax->min;
	AxisValue v = clamp_axis(ax->axis, p);
	// AxisAction.old_positions[self.axis] = p
	m->set_axis(m, ax->axis, v);
	// mapper.syn_list.add(mapper.gamepad)
}

static void change(Action* a, Mapper* m, double dx, double dy, PadStickTrigger what) {
	// TODO: This is not enough, see https://github.com/kozec/sc-controller/issues/213
	// TODO: Old solution at https://github.com/kozec/sc-controller/blob/master/scc/actions.py#L698
	// TODO: is also wrong, as it doesn't work with multiple controllers
	axis(a, m, clamp(STICK_PAD_MIN, dx, STICK_PAD_MAX), what);
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	AxisAction* ax = container_of(a, AxisAction, action);
	double p = (((double)pos * ax->scale) - (double)TRIGGER_MIN) / (double)(TRIGGER_MAX - TRIGGER_MIN);
	p = (p * (double)(ax->max - ax->min)) + (double)ax->min;
	AxisValue v = clamp_axis(ax->axis, (AxisValue)p);
	// AxisAction.old_positions[self.axis] = p
	m->set_axis(m, ax->axis, v);
	// mapper.syn_list.add(mapper.gamepad)
}

static void set_sensitivity(Action* a, float x, float y, float z) {
	AxisAction* ax = container_of(a, AxisAction, action);
	ax->scale = x;
}

/** Intended for internal use */
bool scc_action_is_axis(Action* a) {
	return (a->type == KW_AXIS)
			|| (a->type == KW_RAXIS)
			|| (a->type == KW_HATUP)
			|| (a->type == KW_HATDOWN)
			|| (a->type == KW_HATLEFT)
			|| (a->type == KW_HATRIGHT)
	;
}

static Parameter* get_property(Action* a, const char* name) {
	AxisAction* ax = container_of(a, AxisAction, action);
	if (0 == strcmp(name, "sensitivity")) {
		Parameter* params[] = { scc_new_float_parameter(ax->scale) };
		return scc_new_tuple_parameter(1, params);
	}
	MAKE_INT_PROPERTY(ax->axis, "axis");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE axis_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	
	AxisAction* ax = malloc(sizeof(AxisAction));
	params = scc_copy_param_list(params);
	if ((ax == NULL) || (params == NULL)) {
		list_free(params);
		free(ax);
		return (ActionOE)scc_oom_action_error();
	}
	scc_action_init(&ax->action, KW_AXIS, AF_ACTION | AF_AXIS | AF_MOD_DEADZONE,
					&axis_dealloc, &axis_to_string);
	if (!apply_axis_params(ax, keyword, params))
		return (ActionOE)invalid_number_of_parameters(keyword);
	ax->params = params;
	
	ax->action.describe = &describe;
	ax->action.axis = &axis;
	ax->action.trigger = &trigger;
	ax->action.button_press = &button_press;
	ax->action.button_release = &button_release;
	ax->action.get_property = &get_property;
	ax->action.extended.set_sensitivity = &set_sensitivity;
	ax->action.extended.change = &change;
	return (ActionOE)&ax->action;
}

void scc_actions_init_axis() {
	scc_param_checker_init(&pc, "xi16?i16?");
	scc_action_register(KW_AXIS, &axis_constructor);
	scc_action_register(KW_RAXIS, &axis_constructor);
	scc_action_register(KW_HATUP, &axis_constructor);
	scc_action_register(KW_HATDOWN, &axis_constructor);
	scc_action_register(KW_HATLEFT, &axis_constructor);
	scc_action_register(KW_HATRIGHT, &axis_constructor);
}
