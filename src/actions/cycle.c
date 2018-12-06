/**
 * SC-Controller - Cycle
 *
 * Multiple actions cycling on same button.
 * When button is pressed 1st time, 1st action is executed. 2nd action is
 * executed for 2nd press, 3rd for 3rd, et cetera et cetera.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"
#include "macros.h"

static ParamChecker pc;
const char* KW_CYCLE = "cycle";

typedef struct {
	Action				action;
	ParameterList		params;
	int					next;		// index of next action to be executed
} Cycle;


ACTION_MAKE_TO_STRING(Cycle, cycle, KW_CYCLE, NULL);

static void cycle_dealloc(Action* a) {
	Cycle* c = container_of(a, Cycle, action);
	list_free(c->params);
	free(c);
}

static void button_press(Action* a, Mapper* m) {
	Cycle* c = container_of(a, Cycle, action);
	Action* child = scc_parameter_as_action(list_get(c->params, c->next));
	child->button_press(child, m);
}

static void button_release(Action* a, Mapper* m) {
	Cycle* c = container_of(a, Cycle, action);
	Action* child = scc_parameter_as_action(list_get(c->params, c->next));
	child->button_release(child, m);
	
	c->next ++;
	if (c->next >= list_len(c->params))
		c->next = 0;
}


static ActionOE cycle_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	
	params = scc_copy_param_list(params);
	Cycle* c = malloc(sizeof(Cycle));
	if ((c == NULL) || (params == NULL)) {
		free(c);
		list_free(params);
		return (ActionOE)scc_oom_action_error();
	}
	
	scc_action_init(&c->action, KW_CYCLE, AF_ACTION, &cycle_dealloc, &cycle_to_string);
	c->action.button_press = &button_press;
	c->action.button_release = &button_release;
	// c->action.extended.set_sensitivity = &set_sensitivity;
	// c->action.extended.set_haptic = &set_haptic;
	
	c->next = 0;
	c->params = params;
	return (ActionOE)&c->action;
}


void scc_actions_init_cycle() {
	scc_param_checker_init(&pc, "a*");
	scc_action_register(KW_CYCLE, &cycle_constructor);
}
