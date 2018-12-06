/**
 * SC-Controller - Tap action
 *
 * Presses button for short time.
 * If button is already pressed, generates release-press-release-press
 * events in quick sequence.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"

static ParamChecker pc;

const char* KW_TAP = "tap";
#define PAUSE			1
#define COUNTER_VAL		100

typedef struct {
	Action				action;
	ParameterList		params;
	Keycode				button;
	size_t				count;
	struct {
		size_t			count;
		bool			press;		// as in 'next scheduled action is press'
		bool			keep_pressed;
	} schedule;
} Tap;

ACTION_MAKE_TO_STRING(Tap, tap, _a->type, &pc);

static void tap_dealloc(Action* a) {
	Tap* tap = container_of(a, Tap, action);
	list_free(tap->params);
	free(tap);
}

static void timer(Mapper* m, void* userdata) {
	Tap* t = (Tap*)userdata;
	if (t->schedule.press) {
		m->key_press(m, t->button, true);
		t->schedule.press = false;
		t->schedule.count --;
		m->schedule(m, PAUSE, &timer, t);
	} else if (t->schedule.count > 0) {
		m->key_release(m, t->button);
		t->schedule.press = true;
		m->schedule(m, PAUSE, &timer, t);
	} else { // t->schedule.count == 0
		if (!t->schedule.keep_pressed)
			m->key_release(m, t->button);
	}
}

static void button_press(Action* a, Mapper* m) {
	Tap* t = container_of(a, Tap, action);
	if (t->schedule.count > 0) {
		WARN("You are activating 'tap' faster than it can be processed");
		return;
	}
	if (m->is_virtual_key_pressed(m, t->button)) {
		// Special handling for case when virtual button is alrady pressed
		t->schedule.keep_pressed = true;
		m->key_press(m, t->button, true);
	} else {
		t->schedule.keep_pressed = false;
		m->key_press(m, t->button, false);
	}
	t->schedule.press = false;
	t->schedule.count = t->count - 1;
	m->schedule(m, PAUSE, &timer, t);
}

static void button_release(Action* a, Mapper* m) {
	// Intentionally left blank
}


static ActionOE tap_constructor(const char* keyword, ParameterList params) {
	// Tap constructor builds a tap. Sink is optional.
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	Tap* t = malloc(sizeof(Tap));
	if (t == NULL) {
		list_free(params);
		return (ActionOE)scc_oom_action_error();
	}
	
	scc_action_init(&t->action, KW_TAP, AF_ACTION, &tap_dealloc, &tap_to_string);
	t->action.button_press = &button_press;
	t->action.button_release = &button_release;
	
	t->params = params;
	t->button = scc_parameter_as_int(params->items[0]);
	t->count = scc_parameter_as_int(params->items[1]);
	t->schedule.count = 0;
	return (ActionOE)&t->action;
}


void scc_actions_init_tap() {
	scc_param_checker_init(&pc, "cc?");
	scc_param_checker_set_defaults(&pc, 1);
	scc_action_register(KW_TAP, &tap_constructor);

}
