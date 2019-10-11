/*
 * SC-Controller - TriggerAction
 *
 * Executes action when trigger finally 'clicks' and then holds it until
 * specified 'release level' is reached.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "scc/tools.h"
#include "props.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_TRIGGER = "trigger";

typedef struct {
	Action			action;
	Action*			child;
	TriggerValue	press_level;
	TriggerValue	release_level;
	HapticData		hdata;
	bool			pressed;
} TriggerAction;


static char* trigger_to_string(Action* a) {
	TriggerAction* t = container_of(a, TriggerAction, action);
	ParameterList params = scc_inline_param_list(
								scc_new_int_parameter(t->press_level),
								scc_new_action_parameter(t->child));
	
	if (params == NULL) return NULL; // OOM
	if (t->press_level != t->release_level) {
		Parameter* param = scc_new_int_parameter(t->release_level);
		if (param == NULL) {
			list_free(params);
			return NULL;
		}
		list_insert(params, 1, scc_new_int_parameter(t->release_level));
	}
	
	char* parmsstr = scc_param_list_to_string(params);
	list_free(params);
	if (parmsstr == NULL) return NULL;	// OOM
	
	char* rv = strbuilder_fmt("trigger(%s)", parmsstr);
	free(parmsstr);
	return rv;
}

static char* describe(Action* a, ActionDescContext ctx) {
	TriggerAction* t = container_of(a, TriggerAction, action);
	return scc_action_get_description(t->child, ctx);
}

static void trigger_dealloc(Action* a) {
	TriggerAction* t = container_of(a, TriggerAction, action);
	RC_REL(t->child);
	free(t);
}


static Action* compress(Action* a) {
	TriggerAction* t = container_of(a, TriggerAction, action);
	scc_action_compress(&t->child);
	return a;
}


/** Called when trigger level enters active zone */
static inline void trigger_press(TriggerAction* t, Mapper* m) {
	t->pressed = true;
	if (HAPTIC_ENABLED(&t->hdata))
		m->haptic_effect(m, &t->hdata);
	if ((t->child->flags & AF_AXIS) == 0)
		t->child->button_press(t->child, m);
}
	
/** Called when trigger level leaves active zone */
static inline void trigger_release(TriggerAction* t, Mapper* m, TriggerValue old_pos, PadStickTrigger what) {
	t->pressed = false;
	if (t->child->flags & AF_AXIS)
		t->child->trigger(t->child, m, old_pos, 0, what);
	else
		t->child->button_release(t->child, m);
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	TriggerAction* t = container_of(a, TriggerAction, action);
	
	// There are 3 modes that TriggerAction can work in
	if (t->release_level > t->press_level) {
		// Mode 1, action is 'pressed' if current level is
		// between press_level and release_level.
		if (!t->pressed && (pos >= t->press_level) && (old_pos < t->press_level))
			trigger_press(t, m);
		else if (t->pressed && (pos > t->release_level) && (old_pos <= t->release_level))
			trigger_release(t, m, old_pos, what);
		else if (t->pressed && (pos < t->press_level) && (old_pos >= t->press_level))
			trigger_release(t, m, old_pos, what);
	}
	if (t->release_level == t->press_level) {
		// Mode 2, there is only press_level and action is 'pressed'
		// while current level is above it.
		if (!t->pressed && (pos >= t->press_level) && (old_pos < t->press_level))
			trigger_press(t, m);
		else if (t->pressed && (pos < t->press_level) && (old_pos >= t->press_level))
			trigger_release(t, m, old_pos, what);
	}
	if (t->release_level < t->press_level) {
		// Mode 3, action is 'pressed' if current level is above 'press_level'
		// and then released when it returns beyond 'release_level'.
		if (!t->pressed && (pos >= t->press_level) && (old_pos < t->press_level))
			trigger_press(t, m);
		else if (!t->pressed && (pos < t->release_level) && (old_pos >= t->release_level))
			trigger_release(t, m, old_pos, what);
	}
	
	// TODO: Check if this works:
	// Having AxisAction as child of TriggerAction is special case,
	// child action recieves trigger events instead of button presses
	// and button_releases.
	if ((t->child->flags & AF_AXIS) && (t->pressed))
		t->child->trigger(t->child, m, old_pos, pos, what);
}

static void set_haptic(Action* a, HapticData hdata) {
	TriggerAction* t = container_of(a, TriggerAction, action);
	t->hdata = hdata;
}

static Parameter* get_property(Action* a, const char* name) {
	TriggerAction* t = container_of(a, TriggerAction, action);
	MAKE_HAPTIC_PROPERTY(t->hdata, "haptic");
	MAKE_ACTION_PROPERTY(t->child, "child");
	MAKE_INT_PROPERTY(t->press_level, "press_level");
	MAKE_INT_PROPERTY(t->release_level, "release_level");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE trigger_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	
	TriggerAction* t = malloc(sizeof(TriggerAction));
	if (t == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&t->action, KW_TRIGGER, AF_ACTION | AF_MOD_FEEDBACK,
					&trigger_dealloc, &trigger_to_string);
	t->action.trigger = &trigger;
	t->action.describe = &describe;
	t->action.compress = &compress;
	t->action.get_property = &get_property;
	t->action.extended.set_haptic = &set_haptic;
	
	t->pressed = false;
	HAPTIC_DISABLE(&t->hdata);
	t->press_level = scc_parameter_as_int(params->items[0]);
	if (list_len(params) == 3) {
		// Includes release_level
		t->release_level = scc_parameter_as_int(params->items[1]);
		t->child = scc_parameter_as_action(params->items[2]);
	} else {
		t->release_level = t->press_level;
		t->child = scc_parameter_as_action(params->items[1]);
	}
	
	RC_ADD(t->child);
	return (ActionOE)&t->action;
}

void scc_actions_init_trigger() {
	scc_param_checker_init(&pc, "ui8ui8?a");
	scc_action_register(KW_TRIGGER, &trigger_constructor);
}
