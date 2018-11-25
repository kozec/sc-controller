/**
 * SC Controller - Special actions - Turnoff
 * 
 * Turns controller off.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/special_action.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_TURNOFF = "turnoff";

typedef struct {
	Action				action;
	ParameterList		params;
} SATurnoffAction;


ACTION_MAKE_TO_STRING(SATurnoffAction, sa_profile, _a->type, NULL);

static void sa_profile_dealloc(Action* a) {
	SATurnoffAction* sa = container_of(a, SATurnoffAction, action);
	list_free(sa->params);
	free(sa);
}

// For button press, release and trigger, it's safe to assume that they are being pressed...
static void button_press(Action* a, Mapper* m) {
	if ((m->special_action == NULL) || !m->special_action(m, SAT_TURNOFF, NULL))
		DWARN("Mapper lacks support for 'turnoff'");
}


static ActionOE sa_profile_constructor(const char* keyword, ParameterList params) {
	// TODO: Maybe optimize this. Turnoff takes no arguments
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_copy_param_list(params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	SATurnoffAction* sa = malloc(sizeof(SATurnoffAction));
	if (sa == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&sa->action, KW_TURNOFF, AF_SPECIAL_ACTION, &sa_profile_dealloc, &sa_profile_to_string);
	sa->action.button_press = &button_press;
	
	sa->params = params;
	return (ActionOE)&sa->action;
}


void scc_actions_init_sa_turnoff() {
	scc_param_checker_init(&pc, "");
	scc_action_register(KW_TURNOFF, &sa_profile_constructor);
}
