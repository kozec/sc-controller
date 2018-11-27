/*
 * SC-Controller - MouseAction
 *
 * Controlls mouse movement in either vertical or horizontal direction,
 * or scroll wheel.
 */
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "wholehaptic.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_MOUSE = "mouse";
static const char* KW_TRACKPAD = "trackpad";
#define MOUSE_FACTOR 0.005	/* Just random number to put default sensitivity into sane range */

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
	if (b->axis == REL_CNT)
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
		change(a, m, 100000, 0, 0);
	else
		change(a, m, 100, 0, 0);
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

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	MouseAction* b = container_of(a, MouseAction, action);
	switch (what) {
	case PST_STICK:
		m->move_mouse(m, (double)x * b->sensitivity.x * 0.01, (double)y * b->sensitivity.y * 0.01);
		// mapper.force_event.add(FE_STICK)
		break;
	case PST_LEFT:
	case PST_CPAD:
		pad(a, m, x, y, what);
		break;
	case PST_RIGHT:
	 	if (m->get_flags(m) & CF_HAS_RSTICK) {
			m->move_mouse(m, (double)x * b->sensitivity.x * 0.01, (double)y * b->sensitivity.y * 0.01);
			// mapper.force_event.add(FE_PAD)
		} else {
			pad(a, m, x, y, what);
		}
		break;
	case PST_GYRO:
		// Not possible
		break;
	}
}

static void set_sensitivity(Action* a, float x, float y, float z) {
	MouseAction* b = container_of(a, MouseAction, action);
	vec_set(b->sensitivity, x, y);
}

static void gyro(Action* a, Mapper* m, GyroValue pitch, GyroValue yaw, GyroValue roll,
					GyroValue q1, GyroValue q2, GyroValue q3, GyroValue q4) {
	// MouseAction* b = container_of(a, MouseAction, action);
	
	// TODO: So, yeah, wtf should I do with yaw?
	// if self._mouse_axis == YAW:
	// 	mapper.mouse_move(yaw * -self.sensitivity[0], pitch * -self.sensitivity[1])
	// else:
	// 	mapper.mouse_move(roll * -self.sensitivity[0], pitch * -self.sensitivity[1])
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	double delta = (double)pos - (double)old_pos;
	// change() will figure out the axis from the action parameters
	change(a, m, delta, delta, 0);
}


static ActionOE mouse_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	MouseAction* b = malloc(sizeof(MouseAction));
	if (b == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&b->action, KW_MOUSE, AF_ACTION, &mouse_dealloc, &mouse_to_string);
	b->action.button_press = &button_press;
	b->action.axis = &axis;
	b->action.whole = &whole;
	b->action.gyro = &gyro;
	b->action.trigger = &trigger;
	b->action.extended.set_sensitivity = &set_sensitivity;
	b->action.extended.set_haptic = &set_haptic;
	b->action.extended.change = &change;
	
	b->old_pos_set = false;
	b->axis = scc_parameter_as_int(params->items[0]);
	b->sensitivity.x = b->sensitivity.y = scc_parameter_as_float(params->items[1]);
	b->params = params;
	wholehaptic_init(&b->whdata);
	
	return (ActionOE)&b->action;
}

void scc_actions_init_mouse() {
	scc_param_checker_init(&pc, "c?f?");
	scc_param_checker_set_defaults(&pc, REL_CNT, 1.0);
	scc_action_register(KW_MOUSE, &mouse_constructor);
	scc_action_register(KW_TRACKPAD, &mouse_constructor);
}
