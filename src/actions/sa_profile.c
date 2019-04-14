/**
 * SC Controller - Special actions - Profile
 * 
 * Switches to different profile
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/special_action.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"
#include "props.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_PROFILE = "profile";

typedef struct {
	Action				action;
	ParameterList		params;
} SAProfileAction;


ACTION_MAKE_TO_STRING(SAProfileAction, sa_profile, _a->type, NULL);

static void sa_profile_dealloc(Action* a) {
	SAProfileAction* sa = container_of(a, SAProfileAction, action);
	list_free(sa->params);
	free(sa);
}

// For button press, release and trigger, it's safe to assume that they are being pressed...
static void button_press(Action* a, Mapper* m) {
	SAProfileAction* sa = container_of(a, SAProfileAction, action);
	const char* profile = scc_parameter_as_string(sa->params->items[0]);
	if ((m->special_action == NULL) || !m->special_action(m, SAT_PROFILE, (void*)profile))
		DWARN("Mapper lacks support for 'profile'");
}


static Parameter* get_property(Action* a, const char* name) {
	SAProfileAction* sa = container_of(a, SAProfileAction, action);
	MAKE_PARAM_PROPERTY(sa->params->items[0], "profile");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE sa_profile_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_copy_param_list(params);
	
	SAProfileAction* sa = malloc(sizeof(SAProfileAction));
	if ((sa == NULL) || (params == NULL)) {
		list_free(params);
		free(sa);
		return (ActionOE)scc_oom_action_error();
	}
	scc_action_init(&sa->action, KW_PROFILE, AF_SPECIAL_ACTION, &sa_profile_dealloc, &sa_profile_to_string);
	sa->action.button_press = &button_press;
	sa->action.get_property = &get_property;
	
	sa->params = params;
	return (ActionOE)&sa->action;
}


void scc_actions_init_sa_profile() {
	scc_param_checker_init(&pc, "s");
	scc_action_register(KW_PROFILE, &sa_profile_constructor);
}
