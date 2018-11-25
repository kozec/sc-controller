#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "scc/tools.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_BUTTON = "button";
#define BUTTON_CIRCULAR_INTERVAL	1000
#define BUTTON_STICK_DEADZONE		100

typedef struct {
	Action			action;
	Parameter*		param[2];
	Keycode			button[2];
	Keycode			pressed_button;
	HapticData		hdata;
} ButtonAction;


static char* button_to_string(Action* a) {
	ButtonAction* b = container_of(a, ButtonAction, action);
	if (b->param[0] == NULL)
		return strbuilder_fmt("button(%i)", b->button[0]);
	else if (b->button[1] == 0) {
		char* s = scc_parameter_to_string(b->param[0]);
		char* rv = strbuilder_fmt("button(%s)", s);
		free(s);
		return rv;
	} else {
		char* s0 = scc_parameter_to_string(b->param[0]);
		char* s1 = scc_parameter_to_string(b->param[1]);
		char* rv = strbuilder_fmt("button(%s, %s)", s0, s1);
		free(s0); free(s1);
		return rv;
	}
}

static void button_dealloc(Action* a) {
	ButtonAction* b = container_of(a, ButtonAction, action);
	free(b);
}


static void button_press(Action* a, Mapper* m) {
	ButtonAction* b = container_of(a, ButtonAction, action);
	if (HAPTIC_ENABLED(&b->hdata))
		m->haptic_effect(m, &b->hdata);
	m->key_press(m, b->button[0]);
}

static void button_release (Action* a, Mapper* m) {
	ButtonAction* b = container_of(a, ButtonAction, action);
	m->key_release(m, b->button[0]);
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	Keycode press;
	ButtonAction* b = container_of(a, ButtonAction, action);
	switch (what) {
	case PST_STICK:
		// Stick used used as one big button (probably as part of ring bindings)
		if ((abs(x) < BUTTON_STICK_DEADZONE) && (abs(y) < BUTTON_STICK_DEADZONE)) {
			if (b->pressed_button == b->button[0]) {
				m->key_release(m, b->button[0]);
				b->pressed_button = 0;
			}
		} else if (b->pressed_button != b->button[0]) {
			m->key_press(m, b->button[0]);
			b->pressed_button = b->button[0];
		}
		break;
	case PST_LEFT:
	case PST_RIGHT:
		// Possibly special case, pressing with click() on entire pad
		press = scc_what_to_pressed_button(what);
		if (m->is_pressed(m, press) && !m->was_pressed(m, press)) {
			m->key_press(m, b->button[0]);
		} else if (!m->is_pressed(m, press) && m->was_pressed(m, press)) {
			m->key_release(m, b->button[0]);
		}
		break;
	case PST_GYRO:
		// Impossible
	case PST_CPAD:
		// Entire pad used as one big button
		if (m->is_touched(m, what) && !m->was_touched(m, what)) {
			// Touched the pad
			m->key_press(m, b->button[0]);
		}
		if (m->was_touched(m, what) && !m->is_touched(m, what)) {
			// Released the pad
			m->key_release(m, b->button[0]);
		}
	}
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	// TODO: Remove this, convert to TriggerAction internally
	if ((pos >= TRIGGER_HALF) && (old_pos < TRIGGER_HALF)) {
		button_press(a, m);
	} else if ((pos < TRIGGER_HALF) && (old_pos >= TRIGGER_HALF)) {
		button_release(a, m);
	}
}

static void set_haptic(Action* a, HapticData hdata) {
	ButtonAction* b = container_of(a, ButtonAction, action);
	b->hdata = hdata;
}


Action* scc_button_action_from_keycode(unsigned short keycode) {
	ButtonAction* b = malloc(sizeof(ButtonAction));
	if (b == NULL) return NULL;
	scc_action_init(&b->action, KW_BUTTON, AF_ACTION, &button_dealloc, &button_to_string);
	b->action.flags = 0;
	b->button[0] = keycode;
	b->button[1] = 0;
	b->param[0] = NULL;
	b->param[1] = NULL;
	b->pressed_button = 0;
	HAPTIC_DISABLE(&b->hdata);
	b->action.whole = &whole;
	b->action.button_press = &button_press;
	b->action.button_release = &button_release;
	return &b->action;
}

static ActionOE button_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	ButtonAction* b = malloc(sizeof(ButtonAction));
	if (b == NULL) {
		list_free(params);
		return (ActionOE)scc_oom_action_error();
	}
	scc_action_init(&b->action, KW_BUTTON, AF_ACTION, &button_dealloc, &button_to_string);
	b->button[0] = scc_parameter_as_int(params->items[0]);
	b->button[1] = scc_parameter_as_int(params->items[1]);
	b->param[0] = params->items[0];
	b->param[1] = params->items[1];
	b->pressed_button = 0;
	HAPTIC_DISABLE(&b->hdata);
	b->action.whole = &whole;
	b->action.button_press = &button_press;
	b->action.button_release = &button_release;
	b->action.trigger = &trigger;
	b->action.extended.set_haptic = &set_haptic;
	
	RC_ADD(params->items[0]);
	RC_ADD(params->items[1]);
	list_free(params);
	return (ActionOE)&b->action;
}


// TODO: Auto-convert button used on axis to DPAD
// TODO: Auto-convert button used on trigger to TriggerAction
// TODO: change callback
void scc_actions_init_button() {
	scc_param_checker_init(&pc, "cc?");
	scc_param_checker_set_defaults(&pc, 0);
	scc_action_register(KW_BUTTON, &button_constructor);
}
