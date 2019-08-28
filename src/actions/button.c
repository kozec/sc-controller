/*
 * SC-Controller - ButtonAction
 *
 * Action that presses virtual button, be it on keyboard, mouse or gamepad
 *
 * Supported properties:
 *  - keycode	(int)
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/conversions.h"
#include "scc/action.h"
#include "scc/tools.h"
#include "props.h"
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

static char* describe(Action* a, ActionDescContext ctx) {
	ButtonAction* b = container_of(a, ButtonAction, action);
	const char* keyname;
	switch (b->button[0]) {
	case BTN_LEFT:			return strbuilder_cpy("Mouse Left");
	case BTN_MIDDLE:		return strbuilder_cpy("Mouse Middle");
	case BTN_RIGHT:			return strbuilder_cpy("Mouse Right");
	case BTN_SIDE:			return strbuilder_cpy("Mouse 8");
	case BTN_EXTRA:			return strbuilder_cpy("Mouse 9");
	case BTN_TR:			return strbuilder_cpy("Right Bumper");
	case BTN_TL:			return strbuilder_cpy("Left Bumper");
	case BTN_THUMBL:		return strbuilder_cpy("LStick Click");
	case BTN_THUMBR:		return strbuilder_cpy("RStick Click");
	case BTN_START:			return strbuilder_cpy("Start >");
	case BTN_SELECT:		return strbuilder_cpy("< Select");
	case BTN_A:				return strbuilder_cpy("A Button");
	case BTN_B:				return strbuilder_cpy("B Button");
	case BTN_X:				return strbuilder_cpy("X Button");
	case BTN_Y:				return strbuilder_cpy("Y Button");
	case KEY_PREVIOUSSONG:	return strbuilder_cpy("<< Song");
	case KEY_STOP:			return strbuilder_cpy("Stop");
	case KEY_PLAYPAUSE:		return strbuilder_cpy("Play/Pause");
	case KEY_NEXTSONG:		return strbuilder_cpy("Song >>");
	case KEY_VOLUMEDOWN:	return strbuilder_cpy("- Volume");
	case KEY_VOLUMEUP:		return strbuilder_cpy("+ Volume");
	case KEY_LEFTSHIFT:		return strbuilder_cpy((ctx == AC_OSD) ? "Shift" : "LShift");
	case KEY_RIGHTSHIFT:	return strbuilder_cpy((ctx == AC_OSD) ? "Shift" : "RShift");
	case KEY_LEFTALT:		return strbuilder_cpy((ctx == AC_OSD) ? "Alt" : "LAlt");
	case KEY_RIGHTALT:		return strbuilder_cpy((ctx == AC_OSD) ? "Alt" : "RAlt");
	case KEY_LEFTCTRL:		return strbuilder_cpy((ctx == AC_OSD) ? "CTRL" : "LControl");
	case KEY_RIGHTCTRL:		return strbuilder_cpy((ctx == AC_OSD) ? "CTRL" : "RControl");
#ifndef _WIN32
	case KEY_BACKSPACE:		return strbuilder_cpy((ctx == AC_OSD) ? "Bcksp" : "Backspace");
	case KEY_SPACE:			return strbuilder_cpy("Space");
	case KEY_TAB:			return strbuilder_cpy("Tab");
#else
	case KEY_BACKSPACE:		return strbuilder_cpy((ctx == AC_OSD) ? "<-" : "Backspace");
	// case KEY_ENTER:			return strbuilder_cpy((ctx == AC_OSD) ? "↲" : "Enter");
	case KEY_ENTER:			return strbuilder_cpy((ctx == AC_OSD) ? "◄┘" : "Enter");
	case KEY_SPACE:			return strbuilder_cpy((ctx == AC_OSD) ? " " : "Space");
	case KEY_COMMA:			return strbuilder_cpy((ctx == AC_OSD) ? "," : "Comma");
	case KEY_DOT:			return strbuilder_cpy((ctx == AC_OSD) ? "." : "Dot");
	case KEY_SEMICOLON:		return strbuilder_cpy((ctx == AC_OSD) ? ";" : "Semicolon");
	case KEY_GRAVE:			return strbuilder_cpy("`");
	case KEY_EQUAL:			return strbuilder_cpy("=");
	case KEY_MINUS:			return strbuilder_cpy((ctx == AC_OSD) ? "-" : "Minus");
	case KEY_TAB:			return strbuilder_cpy((ctx == AC_OSD) ? "⇥" : "Tab");
	case KEY_APOSTROPHE:	return strbuilder_cpy((ctx == AC_OSD) ? "'" : "Apostrophe");
#endif
	case KEY_LEFTBRACE:		return strbuilder_cpy("[");
	case KEY_RIGHTBRACE:	return strbuilder_cpy("]");
	case KEY_BACKSLASH:		return strbuilder_cpy("\\");
	case KEY_SLASH:			return strbuilder_cpy("/");
	default:
		keyname = scc_get_key_name(b->button[0]);
		if (keyname != NULL)
			return strbuilder_fmt("%s", keyname + 4); // +4 to skip over "KEY_"
		return button_to_string(a);
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
	m->key_press(m, b->button[0], false);
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
			m->key_press(m, b->button[0], false);
			b->pressed_button = b->button[0];
		}
		break;
	case PST_LPAD:
	case PST_RPAD:
		// Possibly special case, pressing with click() on entire pad
		press = scc_what_to_pressed_button(what);
		if (m->is_pressed(m, press) && !m->was_pressed(m, press)) {
			m->key_press(m, b->button[0], false);
		} else if (!m->is_pressed(m, press) && m->was_pressed(m, press)) {
			m->key_release(m, b->button[0]);
		}
		break;
	case PST_CPAD:
		// Entire pad used as one big button
		if (m->is_touched(m, what) && !m->was_touched(m, what)) {
			// Touched the pad
			m->key_press(m, b->button[0], false);
		}
		if (m->was_touched(m, what) && !m->is_touched(m, what)) {
			// Released the pad
			m->key_release(m, b->button[0]);
		}
		break;
	default:
		// trigger / gyro, not possible to reach here
		break;
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

static Parameter* get_property(Action* a, const char* name) {
	ButtonAction* b = container_of(a, ButtonAction, action);
	MAKE_INT_PROPERTY(b->button[0], "button");		// old name
	MAKE_INT_PROPERTY(b->button[0], "keycode");		// better name
	MAKE_HAPTIC_PROPERTY(b->hdata, "haptic");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


Action* scc_button_action_from_keycode(unsigned short keycode) {
	ButtonAction* b = malloc(sizeof(ButtonAction));
	if (b == NULL) return NULL;
	scc_action_init(&b->action, KW_BUTTON, AF_ACTION | AF_KEYCODE,
						&button_dealloc, &button_to_string);
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
	b->action.get_property = &get_property;
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
	scc_action_init(&b->action, KW_BUTTON,
					AF_ACTION | AF_KEYCODE | AF_MOD_FEEDBACK | AF_MOD_OSD,
					&button_dealloc, &button_to_string);
	b->button[0] = scc_parameter_as_int(params->items[0]);
	b->button[1] = scc_parameter_as_int(params->items[1]);
	b->param[0] = params->items[0];
	b->param[1] = params->items[1];
	b->pressed_button = 0;
	HAPTIC_DISABLE(&b->hdata);
	b->action.describe = &describe;
	b->action.whole = &whole;
	b->action.button_press = &button_press;
	b->action.button_release = &button_release;
	b->action.trigger = &trigger;
	b->action.get_property = &get_property;
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

