/*
 * SC-Controller - MouseAction
 *
 * Controlls mouse movement in either vertical or horizontal direction,
 * or scroll wheel.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/conversions.h"
#include "scc/action.h"
#include "wholehaptic.h"
#include "internal.h"
#include "tostring.h"
#include "props.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_MOUSE = "mouse";
static const char* KW_TRACKPAD = "trackpad";
static const char* KW_TRACKBALL = "trackball";
#define MOUSE_FACTOR 0.005	/* Just random number to put default sensitivity into sane range */
#define MOUSE_REPEAT_DELAY 5

static int YAW = -1;
static int ROLL = -1;
static struct {
	TaskID		task;
	double		dx;
	double		dy;
} mouse_repeat_data = { 0 };


typedef struct {
	Action				action;
	WholeHapticData		whdata;
	ParameterList		params;
	Axis				axis;
	dvec_t				old_pos;
	bool				old_pos_set;
	dvec_t				sensitivity;
} MouseAction;


ACTION_MAKE_TO_STRING(MouseAction, mouse, KW_MOUSE, &pc);
WHOLEHAPTIC_MAKE_SET_HAPTIC(MouseAction, a->whdata);

static char* describe(Action* a, ActionDescContext ctx) {
	MouseAction* b = container_of(a, MouseAction, action);
	switch (b->axis) {
	case REL_WHEEL:
		return strbuilder_cpy("Wheel");
	case REL_HWHEEL:
		return strbuilder_cpy("Horizontal Wheel");
	default:
		return strbuilder_cpy("Mouse");
	}
}

static void mouse_dealloc(Action* a) {
	MouseAction* b = container_of(a, MouseAction, action);
	list_free(b->params);
	free(b);
}


static void change(Action* a, Mapper* m, double dx, double dy, PadStickTrigger what) {
	MouseAction* b = container_of(a, MouseAction, action);
	wholehaptic_change(&b->whdata, m, dx, dy);
	dx = dx * b->sensitivity.x;
	dy = dy * b->sensitivity.y;
	// TODO: dx & dy conversion here probably breaks on double->int
	if (b->axis == 0)
		m->move_mouse(m, dx, dy);
	else if (b->axis == REL_X)
		m->move_mouse(m, dx, 0);
	else if (b->axis == REL_Y)
		m->move_mouse(m, 0, dx);
	else if (b->axis == REL_WHEEL)
		m->move_wheel(m, 0, dy);
	else if (b->axis == REL_HWHEEL)
		m->move_wheel(m, dx, 0);
}

static void button_press(Action* a, Mapper* m) {
	MouseAction* b = container_of(a, MouseAction, action);
	// This is generaly bad idea...
	if ((b->axis == REL_WHEEL) || (b->axis == REL_HWHEEL))
	{
		double dx = (b->axis == REL_HWHEEL) ? 12000 : 0;
		double dy = (b->axis == REL_WHEEL) ? -12000 : 0;
		change(a, m, dx, dy, 0);
	}
	else
		change(a, m, 100, 0, 0);
}

// Do nothing on button release
static void button_release(Action* a, Mapper* m) {
}

static void axis(Action* a, Mapper* m, AxisValue value, PadStickTrigger what) {
	change(a, m, (double)value * MOUSE_FACTOR, 0, what);
	// mapper.force_event.add(FE_STICK)
}

static void pad(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	MouseAction* b = container_of(a, MouseAction, action);
	if (m->is_touched(m, what)) {
		if (b->old_pos_set && m->was_touched(m, what)) {
			double dx = ((double)x - b->old_pos.x);
			double dy = ((double)y - b->old_pos.y);
			change(a, m, dx, dy, what);
		}
		b->old_pos.x = x;
		b->old_pos.y = y;
		b->old_pos_set = true;
	} else {
		// Pad just released
		b->old_pos_set = false;
	}
}

static void mouse_repeat(Mapper* m, void* trash) {
	if (mouse_repeat_data.task != 0) {
		m->move_mouse(m, mouse_repeat_data.dx, mouse_repeat_data.dy);
		mouse_repeat_data.task = m->schedule(m, MOUSE_REPEAT_DELAY, mouse_repeat, NULL);
	}
}

static inline void mouse_repeat_update(MouseAction* b, AxisValue x, AxisValue y) {
	mouse_repeat_data.dx = (double)x * b->sensitivity.x * 0.01;
	mouse_repeat_data.dy = (double)y * b->sensitivity.y * 0.01;
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	MouseAction* b = container_of(a, MouseAction, action);
	switch (what) {
	case PST_STICK:
		if (mouse_repeat_data.task == 0) {
			mouse_repeat_data.task = m->schedule(m, MOUSE_REPEAT_DELAY, mouse_repeat, NULL);
			mouse_repeat_update(b, x, y);
			mouse_repeat(m, NULL);
		} else if ((x == 0) && (y == 0)) {
			// Stick released
			if (mouse_repeat_data.task != 0) {
				m->cancel(m, mouse_repeat_data.task);
				mouse_repeat_data.task = 0;
			}
		} else {
			mouse_repeat_update(b, x, y);
		}
		break;
	case PST_LPAD:
	case PST_CPAD:
		pad(a, m, x, y, what);
		break;
	case PST_RPAD:
		if (m->get_flags(m) & CF_HAS_RSTICK) {
			m->move_mouse(m, (double)x * b->sensitivity.x * 0.01, (double)y * b->sensitivity.y * 0.01);
			// mapper.force_event.add(FE_PAD)
		} else {
			pad(a, m, x, y, what);
		}
		break;
	default:
		// trigger / gyro, not possible to reach here
		break;
	}
}

static void set_sensitivity(Action* a, float x, float y, float z) {
	MouseAction* b = container_of(a, MouseAction, action);
	vec_set(b->sensitivity, x, y);
}

static void gyro(Action* a, Mapper* m, const struct GyroInput* value) {
	MouseAction* b = container_of(a, MouseAction, action);
	
	if (b->axis == YAW) {
		m->move_mouse(m, (double)value->gyaw * -b->sensitivity.x, (double)value->gpitch * -b->sensitivity.y);
	} else {
		m->move_mouse(m, (double)value->groll * -b->sensitivity.x, (double)value->gpitch * -b->sensitivity.y);
	}
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	double delta = (double)pos - (double)old_pos;
	// change() will figure out the axis from the action parameters
	change(a, m, delta, delta, 0);
}

/** Intended for internal use */
bool scc_action_is_mouse(Action* a) {
	return a->type == KW_MOUSE;
}

static Parameter* get_property(Action* a, const char* name) {
	MouseAction* b = container_of(a, MouseAction, action);
	MAKE_DVEC_PROPERTY(b->sensitivity, "sensitivity");
	MAKE_HAPTIC_PROPERTY(b->whdata.hdata, "haptic");
	MAKE_INT_PROPERTY(b->axis, "axis");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE mouse_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	MouseAction* b = malloc(sizeof(MouseAction));
	if (b == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&b->action, KW_MOUSE,
					AF_ACTION | AF_MOD_SENSITIVITY | AF_MOD_SENS_Z
						| AF_MOD_ROTATE | AF_MOD_SMOOTH | AF_MOD_BALL
						| AF_MOD_FEEDBACK | AF_MOD_DEADZONE,
					&mouse_dealloc, &mouse_to_string);
	b->action.button_press = &button_press;
	b->action.button_release = &button_release;
	b->action.axis = &axis;
	b->action.whole = &whole;
	b->action.gyro = &gyro;
	b->action.trigger = &trigger;
	b->action.describe = &describe;
	b->action.extended.set_sensitivity = &set_sensitivity;
	b->action.extended.set_haptic = &set_haptic;
	b->action.extended.change = &change;
	b->action.get_property = &get_property;
	
	b->old_pos_set = false;
	b->axis = scc_parameter_as_int(params->items[0]);
	b->sensitivity.x = b->sensitivity.y = scc_parameter_as_float(params->items[1]);
	b->params = params;
	wholehaptic_init(&b->whdata);
	
	if (0 == strcmp(KW_TRACKBALL, keyword)) {
		// Backwards compatibility - 'trackball(x)' is translated to 'ball(mouse(x))' internally
		Parameter* p = scc_new_action_parameter(&b->action);
		ParameterList lst = scc_inline_param_list(p);
		RC_REL(&b->action);
		if (lst == NULL) return (ActionOE)scc_oom_action_error();
		ActionOE ball = scc_action_new(KW_BALL, lst);
		list_free(lst);
		return ball;
	}
	
	return (ActionOE)&b->action;
}

void scc_actions_init_mouse() {
	YAW = scc_get_int_constant("YAW");
	ROLL = scc_get_int_constant("ROLL");
	ASSERT((YAW > 0) && (ROLL > 0));
	scc_param_checker_init(&pc, "c?f?");
	scc_param_checker_set_defaults(&pc, 0, 1.0);
	scc_action_register(KW_MOUSE, &mouse_constructor);
	scc_action_register(KW_TRACKPAD, &mouse_constructor);
	scc_action_register(KW_TRACKBALL, &mouse_constructor);
}

