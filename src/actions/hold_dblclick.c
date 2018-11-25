/**
 * SC Controller - Hold modifier and doubleclick modifier 
 * 
 * Hold modifier executes action if button is held for some time
 * Doubleclick executes it if button is pressed twice in that time
 *
 * Those two are basically the same with small change in condition
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "scc/tools.h"
#include <sys/time.h>
#include <tgmath.h>
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_CLICKED = "clicked";
static const char* KW_CLICK = "click";		// old name

typedef struct {
	Action				action;
	Action*			 	child;
} ClickedModifier;


static char* click_to_string(Action* a) {
	ClickedModifier* c = container_of(a, ClickedModifier, action);
	ParameterList l = scc_inline_param_list(
			scc_new_action_parameter(c->child)
	);
	
	char* strl = scc_param_list_to_string(l);
	char* rv = (strl == NULL) ? NULL : strbuilder_fmt("smooth(%s)", strl);
	list_free(l);
	free(strl);
	return rv;
}

static void click_dealloc(Action* a) {
	ClickedModifier* c = container_of(a, ClickedModifier, action);
	RC_REL(c->child);
	free(c);
}


static Action* compress(Action* a) {
	ClickedModifier* c = container_of(a, ClickedModifier, action);
	scc_action_compress(&c->child);
	return a;
}

// For button press, release and trigger, it's safe to assume that they are being pressed...
static void button_press(Action* a, Mapper* m) {
	ClickedModifier* c = container_of(a, ClickedModifier, action);
	c->child->button_press(c->child, m);
}

static void button_release(Action* a, Mapper* m) {
	ClickedModifier* c = container_of(a, ClickedModifier, action);
	c->child->button_release(c->child, m);
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	ClickedModifier* c = container_of(a, ClickedModifier, action);
	c->child->trigger(c->child, m, old_pos, pos, what);
}

static void axis(Action* a, Mapper* m, AxisValue value, PadStickTrigger what) {
	ClickedModifier* c = container_of(a, ClickedModifier, action);
	SCButton b = scc_what_to_pressed_button(what);
	if (m->is_pressed(m, b)) {
		// if what == STICK: mapper.force_event.add(FE_STICK)
		c->child->axis(c->child, m, value, what);
	} else if (m->was_pressed(m, b)) {
		// Just released
		c->child->axis(c->child, m, 0, what);
	}
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	ClickedModifier* c = container_of(a, ClickedModifier, action);
	SCButton b = scc_what_to_pressed_button(what);
	if (m->is_pressed(m, b)) {
		// if what == STICK: mapper.force_event.add(FE_STICK)
		c->child->whole(c->child, m, x, y, what);
	} else if (m->was_pressed(m, b)) {
		// Just released
		c->child->whole(c->child, m, 0, 0, what);
	}
	
	// TODO: This should call whole_blocked if finger moves over pad while
	// TODO: nothing is pressed. I hope it will not be necessary
	// self.action.whole_blocked(mapper, x, y, what)
}


static ActionOE clicked_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	
	ClickedModifier* c = malloc(sizeof(ClickedModifier));
	if (c == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&c->action, KW_CLICKED, AF_MODIFIER, &click_dealloc, &click_to_string);
	c->action.compress = &compress;
	c->action.button_press = &button_press;
	c->action.button_release = &button_release;
	c->action.trigger = &trigger;
	c->action.whole = &whole;
	c->action.axis = &axis;
	
	c->child = scc_parameter_as_action(params->items[0]);
	RC_ADD(c->child);
	
	return (ActionOE)&c->action;
}


void scc_dontusethis_actions_init_clicked() {
	scc_param_checker_init(&pc, "a");
	scc_action_register(KW_CLICKED, &clicked_constructor);
	scc_action_register(KW_CLICK, &clicked_constructor);
}
