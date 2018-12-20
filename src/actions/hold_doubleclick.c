/*
 * SC-Controller - Hold & Doubleclick
 *
 * Doubleclick modifier executes action only if assinged button is pressed twice
 * in short time.
 * Hold modifier executes action only if assinged button is held for short time.
 *
 * Both are implemented in same class, as they have to be merged together
 * when both are set to same button
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/math.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "scc/tools.h"
#include "tostring.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_HOLD = "hold";
static const char* KW_DBLCLICK = "doubleclick";
#define DEAFAULT_TIMEOUT		0.2

typedef enum {
	S_IDLE,
	S_BUTTON_DOWN_1,
	S_BUTTON_UP_1,
	S_EXECUTING
} HoldDblState;

typedef struct {
	Action				action;
	ParameterList		params;
	Action*				hold_action;
	Action*				dblclick_action;
	Action*				default_action;
	Action*				active;
	uint32_t			timeout;
	HoldDblState		state;
	TaskID				task;
} HoldDblClick;

ACTION_MAKE_TO_STRING(HoldDblClick, holddblclick, KW_HOLD, &pc); // _a->keyword

/** Deallocates HoldDblClick */
static void holddblclick_dealloc(Action* a) {
	HoldDblClick* hdbl = container_of(a, HoldDblClick, action);
	RC_REL(hdbl->dblclick_action);
	RC_REL(hdbl->default_action);
	RC_REL(hdbl->hold_action);
	list_free(hdbl->params);
	free(hdbl);
}

static inline bool mergable(Action* a) {
	if (a == NULL)
		return false;
	if (a->type == KW_HOLD)
		return true;
	if (a->type == KW_DBLCLICK)
		return true;
	return false;
}

static void merge(HoldDblClick* hdbl, Action* a) {
	HoldDblClick* hdbl2 = container_of(a, HoldDblClick, action);
	#define TRY_MERGE(child)													\
		if ((hdbl2->child != NULL) &&											\
					((hdbl->child == NULL) || (hdbl->child == a))) {			\
			Action* old = hdbl->child;											\
			hdbl->child = hdbl2->child;											\
			RC_ADD(hdbl->child);												\
			RC_REL(old);														\
		}
	TRY_MERGE(hold_action);
	TRY_MERGE(dblclick_action);
	TRY_MERGE(default_action);
	if (hdbl->timeout == DEAFAULT_TIMEOUT * 1000.0)
		hdbl->timeout = hdbl2->timeout;
}

static Action* compress(Action* a) {
	HoldDblClick* hdbl = container_of(a, HoldDblClick, action);
	if (hdbl->hold_action != NULL)
		scc_action_compress(&hdbl->hold_action);
	if (hdbl->dblclick_action != NULL)
		scc_action_compress(&hdbl->dblclick_action);
	if (hdbl->default_action != NULL)
		scc_action_compress(&hdbl->default_action);
	
	if (mergable(hdbl->hold_action))
		merge(hdbl, hdbl->hold_action);
	if (mergable(hdbl->dblclick_action))
		merge(hdbl, hdbl->dblclick_action);
	if (mergable(hdbl->default_action))
		merge(hdbl, hdbl->default_action);
	return a;
}

static void release_button(Mapper* m, void* hdbl_) {
	HoldDblClick* hdbl = (HoldDblClick*)hdbl_;
	if (hdbl->active != NULL) {
		hdbl->active->button_release(hdbl->active, m);
		hdbl->active = NULL;
	}
}

static void on_timeout(Mapper* m, void* hdbl_) {
	HoldDblClick* hdbl = (HoldDblClick*)hdbl_;
	hdbl->task = 0;
	
	switch (hdbl->state) {
	case S_BUTTON_DOWN_1:
		// Button was pressed once and then user waited until timeout
		// If there is hold_action, it should be executed, otherwise
		// default_action should be used
		hdbl->active = (hdbl->hold_action != NULL) ? hdbl->hold_action : hdbl->default_action;
		if (hdbl->active != NULL) {
			hdbl->active->button_press(hdbl->active, m);
			hdbl->state = S_EXECUTING;
		} else {
			hdbl->state = S_IDLE;
		}
		break;
	case S_BUTTON_UP_1:
		// Button was pressed & released once and timeout was reached while
		// waiting whether user doubleclicks.
		// hold_action or default action, whatever is set, should be executed
		// for brief moment
		hdbl->active = (hdbl->hold_action != NULL) ? hdbl->hold_action : hdbl->default_action;
		if (hdbl->active != NULL) {
			hdbl->active->button_press(hdbl->active, m);
			m->schedule(m, 1, &release_button, hdbl);
		}
		hdbl->state = S_IDLE;
		break;
	case S_IDLE:
	case S_EXECUTING:
		// Impossible to get timeout in these states
		break;
	}
}

inline static void stop_timer(HoldDblClick* hdbl, Mapper* m) {
	if (hdbl->task == 0) return;
	m->cancel(m, hdbl->task);
	hdbl->task = 0;
}

inline static void start_timer(HoldDblClick* hdbl, Mapper* m) {
	if (hdbl->task != 0) stop_timer(hdbl, m);
	hdbl->task = m->schedule(m, hdbl->timeout, &on_timeout, hdbl);
}

static void button_press(Action* a, Mapper* m) {
	HoldDblClick* hdbl = container_of(a, HoldDblClick, action);
	switch (hdbl->state) {
	case S_IDLE:
		// Just pressed button. Start timer and wait to determine which
		// action is going to be executed
		hdbl->state = S_BUTTON_DOWN_1;
		start_timer(hdbl, m);
		break;
	case S_BUTTON_UP_1:
		// Button pressed twice (doubleclick). If execute doubleclick action,
		// if there is one
		if (hdbl->dblclick_action != NULL) {
			hdbl->active = hdbl->dblclick_action;
			hdbl->active->button_press(hdbl->active, m);
		}
		hdbl->state = S_EXECUTING;
		break;
	case S_BUTTON_DOWN_1:
	case S_EXECUTING:
		// Button presed while it's being pressed - not possible
		break;
	}
}

static void button_release(Action* a, Mapper* m) {
	HoldDblClick* hdbl = container_of(a, HoldDblClick, action);
	switch (hdbl->state) {
	case S_BUTTON_DOWN_1:
		// Button pressed and then released - if there is doubleclick action,
		// wait to check if user is doing doubleclick, otherwise execute default.
		if (hdbl->dblclick_action != NULL) {
			hdbl->state = S_BUTTON_UP_1;
		} else if (hdbl->default_action != NULL) {
			stop_timer(hdbl, m);
			hdbl->active = hdbl->default_action;
			hdbl->active->button_press(hdbl->active, m);
			m->schedule(m, 1, &release_button, hdbl);
			hdbl->state = S_IDLE;
		}
		break;
	case S_EXECUTING:
		// Button released while executing action. 'button_release' on that
		// action should be called
		if (hdbl->active != NULL) {
			hdbl->active->button_release(hdbl->active, m);
			hdbl->active = NULL;
		}
		hdbl->state = S_IDLE;
		break;
	case S_IDLE:
	case S_BUTTON_UP_1:
		// Button released without being pressed - not possible
		break;
	}
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	if ((pos == TRIGGER_MAX) && (old_pos < TRIGGER_MAX))
		button_press(a, m);
	else if ((old_pos == TRIGGER_MAX) && (pos < TRIGGER_MAX))
		button_release(a, m);
}

Parameter* get_property(Action* a, const char* name) {
	HoldDblClick* hdbl = container_of(a, HoldDblClick, action);
	if (0 == strcmp(name, "hold_action"))
		return scc_new_action_parameter(hdbl->hold_action);
	if (0 == strcmp(name, "dblclick_action"))
		return scc_new_action_parameter(hdbl->dblclick_action);
	if (0 == strcmp(name, "default_action"))
		return scc_new_action_parameter(hdbl->default_action);
	if (0 == strcmp(name, "timeout"))
		return scc_new_float_parameter((float)hdbl->timeout / 1000.0f);
	
	DWARN("Requested unknown property '%s' from 'hold/doubleclick'", name);
	return NULL;
}


static void set_haptic(Action* a, HapticData hdata) {
	HoldDblClick* hdbl = container_of(a, HoldDblClick, action);
	
	if (hdbl->hold_action != NULL)
		if (hdbl->hold_action->extended.set_haptic != NULL)
			hdbl->hold_action->extended.set_haptic(hdbl->hold_action, hdata);
	if (hdbl->dblclick_action != NULL)
		if (hdbl->dblclick_action->extended.set_haptic != NULL)
			hdbl->dblclick_action->extended.set_haptic(hdbl->dblclick_action, hdata);
}

static void set_sensitivity(Action* a, float x, float y, float z) {
	HoldDblClick* hdbl = container_of(a, HoldDblClick, action);
	
	if (hdbl->hold_action != NULL)
		if (hdbl->hold_action->extended.set_sensitivity != NULL)
			hdbl->hold_action->extended.set_sensitivity(hdbl->hold_action, x, y, z);
	if (hdbl->dblclick_action != NULL)
		if (hdbl->dblclick_action->extended.set_sensitivity != NULL)
			hdbl->dblclick_action->extended.set_sensitivity(hdbl->dblclick_action, x, y, z);
}


static ActionOE holddblclick_constructor(const char* keyword, ParameterList params) {
	keyword = (0 == strcmp(keyword, KW_HOLD)) ? KW_HOLD : KW_DBLCLICK;
	
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	HoldDblClick* hdbl = malloc(sizeof(HoldDblClick));
	if (hdbl == NULL) return (ActionOE)scc_oom_action_error();
	
	scc_action_init(&hdbl->action, keyword, AF_ACTION, &holddblclick_dealloc, &holddblclick_to_string);
	hdbl->action.compress = &compress;
	hdbl->action.button_press = &button_press;
	hdbl->action.button_release = &button_release;
	hdbl->action.get_property = &get_property;
	hdbl->action.extended.set_sensitivity = &set_sensitivity;
	hdbl->action.extended.set_haptic = &set_haptic;

	hdbl->hold_action = (keyword == KW_HOLD) ? scc_parameter_as_action(params->items[0]) : NULL;
	hdbl->dblclick_action = (keyword == KW_DBLCLICK) ? scc_parameter_as_action(params->items[0]) : NULL;
	hdbl->default_action = scc_parameter_as_action(params->items[1]);
	hdbl->timeout = (uint32_t)(scc_parameter_as_float(params->items[2]) * 1000.0);
	hdbl->params = params;
	hdbl->state = S_IDLE;
	hdbl->active = NULL;
	hdbl->task = 0;
	
	return (ActionOE)&hdbl->action;
}

void scc_actions_init_holddblclick() {
	scc_param_checker_init(&pc, "aa?f?");
	scc_param_checker_set_defaults(&pc, NULL, DEAFAULT_TIMEOUT);
	
	scc_action_register(KW_HOLD, &holddblclick_constructor);
	scc_action_register(KW_DBLCLICK, &holddblclick_constructor);
}
