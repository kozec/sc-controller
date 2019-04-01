/**
 * SC Controller - Clicked modifier
 * 
 * Modifier that restricts action so it's executed only when pad or
 * stick it's associated with is pressed.
 * 
 * Useful, for example, to map left pad
 * to virtual dpad in way that's coser to how real dpad works.
*/
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "scc/tools.h"
#include "tostring.h"
#include "props.h"
#include <sys/time.h>
#include <tgmath.h>
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_CLICKED = "clicked";
static const char* KW_CLICK = "click";		// old name

typedef struct {
	Action				action;
	Action*				child;
} ClickedModifier;


MODIFIER_MAKE_TOSTRING(ClickedModifier, clicked, KW_CLICKED);

MODIFIER_MAKE_DESCRIBE(ClickedModifier, "(if pressed) %s", "(if pressed)\n%s");

static void clicked_dealloc(Action* a) {
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

static Action* get_child(Action* a) {
	ClickedModifier* c = container_of(a, ClickedModifier, action);
	RC_ADD(c->child);
	return c->child;
}


static ActionOE clicked_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	
	ClickedModifier* c = malloc(sizeof(ClickedModifier));
	if (c == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&c->action, KW_CLICKED, AF_MODIFIER, &clicked_dealloc, &clicked_to_string);
	c->action.compress = &compress;
	c->action.describe = &describe;
	c->action.button_press = &button_press;
	c->action.button_release = &button_release;
	c->action.trigger = &trigger;
	c->action.whole = &whole;
	c->action.axis = &axis;
	c->action.extended.get_child = &get_child;
	
	c->child = scc_parameter_as_action(params->items[0]);
	RC_ADD(c->child);
	
	return (ActionOE)&c->action;
}


void scc_actions_init_clicked() {
	scc_param_checker_init(&pc, "a");
	scc_action_register(KW_CLICKED, &clicked_constructor);
	scc_action_register(KW_CLICK, &clicked_constructor);
}
