/**
 * SC-Controller - Multiaction
 *
 * Multiaction is not registered through keyword, but generated when goes over
 * keyword 'and'
 *
 * Internally, it works similarly to Macro, but executes all actions at once.
 */
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/action.h"
#include "macros.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

const char* KW_MULTIACTION = "and";	// not used normally

typedef struct {
	Action			action;
	ActionList		children;
} Multiaction;

static char* multiaction_to_string(Action* a) {
	Multiaction* x = container_of(a, Multiaction, action);
	return actions_to_string(x->children, " and ");
}

static char* describe(Action* a, ActionDescContext ctx) {
	Multiaction* x = container_of(a, Multiaction, action);
	// TODO: Quite a lot here
	/*
	 if self.is_key_combination():
			rv = []
			for a in self.actions:
				if isinstance(a, ButtonAction):
					rv.append(a.describe_short())
			return "+".join(rv)
	*/
	/*
	 if len(self.actions) >= 2 and isinstance(self.actions[1], RingAction):
			# Special case, should be multiline
			return "\n".join([ x.describe(context) for x in self.actions ])
	 */
	StrBuilder* sb = strbuilder_new();
	if (sb != NULL) {
		bool needs_separator = false;
		FOREACH_IN(Action*, c, x->children) {
			char* cdesc = scc_action_get_description(c, ctx);
			if (cdesc != NULL) {
				if (needs_separator) strbuilder_add(sb, " and ");
				strbuilder_add(sb, cdesc);
				free(cdesc);
				needs_separator = true;
			}
		}
		return strbuilder_consume(sb);
	}
	return NULL;
}

static void multiaction_dealloc(Action* a) {
	Multiaction* x = container_of(a, Multiaction, action);
	MULTICHILD_DEALLOC(x);
	free(x);
}

static Action* compress(Action* a) {
	Multiaction* x = container_of(a, Multiaction, action);
	compress_actions(x->children);
	return a;
}

static void button_press(Action* a, Mapper* m) {
	Multiaction* ma = container_of(a, Multiaction, action);
	FOR_ALL_CHILDREN(ALWAYS, button_press, m);
}

static void button_release(Action* a, Mapper* m) {
	Multiaction* ma = container_of(a, Multiaction, action);
	FOR_ALL_CHILDREN(ALWAYS, button_release, m);
}

static void axis(Action* a, Mapper* m, AxisValue value, PadStickTrigger what) {
	Multiaction* ma = container_of(a, Multiaction, action);
	FOR_ALL_CHILDREN(ALWAYS, axis, m, value, what);
}

static void gyro(Action* a, Mapper* m, const struct GyroInput* value) {
	Multiaction* ma = container_of(a, Multiaction, action);
	FOR_ALL_CHILDREN(ALWAYS, gyro, m, value);
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	Multiaction* ma = container_of(a, Multiaction, action);
	FOR_ALL_CHILDREN(ALWAYS, whole, m, x, y, what);
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	Multiaction* ma = container_of(a, Multiaction, action);
	FOR_ALL_CHILDREN(ALWAYS, trigger, m, old_pos, pos, what);
}


static void set_sensitivity(Action* a, float x, float y, float z) {
	Multiaction* ma = container_of(a, Multiaction, action);
	FOR_ALL_CHILDREN(c->extended.set_sensitivity, extended.set_sensitivity, x, y, z);
}

static void set_haptic(Action* a, HapticData hdata) {
	Multiaction* ma = container_of(a, Multiaction, action);
	FOR_ALL_CHILDREN(c->extended.set_haptic, extended.set_haptic, hdata);
}


static ActionList get_children(Action* a) {
	Multiaction* x = container_of(a, Multiaction, action);
	return scc_copy_action_list(x->children);
}


Action* scc_multiaction_new(Action** actions, size_t action_count) {
	ActionList lst = list_new(Action, action_count);
	Multiaction* x = malloc(sizeof(Multiaction));
	if ((x == NULL) || (lst == NULL)) {
		free(x);
		list_free(lst);
		return NULL;
	}
	
	scc_action_init(&x->action, KW_MULTIACTION, AF_ACTION, &multiaction_dealloc, &multiaction_to_string);
	x->action.compress = &compress;
	x->action.describe = &describe;
	x->action.button_press = &button_press;
	x->action.button_release = &button_release;
	x->action.axis = &axis;
	x->action.gyro = &gyro;
	x->action.whole = &whole;
	x->action.trigger = &trigger;
	
	x->action.extended.set_sensitivity = &set_sensitivity;
	x->action.extended.get_children = &get_children;
	x->action.extended.set_haptic = &set_haptic;
	
	x->children = lst;
	for (size_t i=0; i<action_count; i++) {
		list_add(lst, actions[i]);
		RC_ADD(actions[i]);
	}
	
	return &x->action;
}

Action* scc_multiaction_combine(Action* a1, Action* a2) {
	return combine(KW_MULTIACTION, a1, a2, &get_children, &scc_multiaction_new);
}
