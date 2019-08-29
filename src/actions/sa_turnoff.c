/**
 * SC Controller - Special actions - Turnoff
 * 
 * Turns controller off.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/list.h"
#include "scc/special_action.h"
#include "scc/action.h"
#include <stdlib.h>
#include <stdio.h>

static const char* KW_TURNOFF = "turnoff";

static char* sa_profile_to_string(Action* a) {
	return strbuilder_fmt("%s()", a->type);
}

static void sa_profile_dealloc(Action* a) {
	free(a);
}

static void button_press(Action* a, Mapper* m) {
	if ((m->special_action == NULL) || !m->special_action(m, SAT_TURNOFF, NULL))
		DWARN("Mapper lacks support for '%s'", a->type);
}


static ActionOE sa_profile_constructor(const char* keyword, ParameterList params) {
	if (list_len(params) != 0) {
		return (ActionOE)scc_new_action_error(AEC_INVALID_NUMBER_OF_PARAMETERS, "'%s' takes no parameters", keyword);
	}
	
	Action* a = malloc(sizeof(Action));
	if (a == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(a, KW_TURNOFF, AF_SPECIAL_ACTION, &sa_profile_dealloc, &sa_profile_to_string);
	a->button_press = &button_press;
	
	return (ActionOE)a;
}


void scc_actions_init_sa_turnoff() {
	scc_action_register(KW_TURNOFF, &sa_profile_constructor);
}

