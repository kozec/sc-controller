/**
 * SC-Controller - Repeat & sleep
 *
 * These two just to modify behaviour of macro. Sleep is never really executed
 * (unless used outside of macro, what makes no sense anyway) and repeat
 * just sets flag on Macro when button is pressed.
 *
 * Internally, both are represented by same structure.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"
#include "macros.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc_sleep;
static ParamChecker pc_repeat;

const char* KW_REPEAT = "repeat";
const char* KW_SLEEP = "sleep";

typedef struct {
	Action				action;
	ParameterList		params;
	Action*				macro;		// set only when repeat has to generate its own macro
} SoR;

ACTION_MAKE_TO_STRING(SoR, sor, _a->type, NULL);

static void sor_dealloc(Action* a) {
	SoR* sor = container_of(a, SoR, action);
	list_free(sor->params);
	RC_REL(sor->macro);
	free(sor);
}

static Action* compress(Action* a) {
	SoR* sor = container_of(a, SoR, action);
	if ((a->type == KW_REPEAT) && (sor->macro == NULL)) {
		Action* c = scc_parameter_as_action(sor->params->items[0]);
		if (c->type == KW_MACRO) {
			sor->macro = c;
			RC_ADD(c);
		} else {
			// Repeat needs its child action to be macro, so when it's used
			// on anything else, new, single-action macro is crated internally.
			sor->macro = scc_macro_new(&c, 1);
			if (sor->macro == NULL) {
				// OOM. Compress can't really fail, so when this happens,
				// it just logs error and causes repeating to not work at all.
				LERROR("Out of memory while processing repeat()");
				return c;
			}
		}
		scc_action_compress(&sor->macro);
	}
	return a;
}

static void button_press(Action* a, Mapper* m) {
	if (a->type == KW_REPEAT) {
		SoR* sor = container_of(a, SoR, action);
		if (sor->macro != NULL) {
			macro_set_repeat(sor->macro, true);
			sor->macro->button_press(sor->macro, m);
		}
	} else {
		WARN("'sleep' used outside of macro");
	}
}

static void button_release(Action* a, Mapper* m) {
	if (a->type == KW_REPEAT) {
		// When button is released, macro should run to end, but stop repeating
		SoR* sor = container_of(a, SoR, action);
		if (sor->macro != NULL)
			macro_set_repeat(sor->macro, false);
	}
}

static Action* get_child(Action* a) {
	SoR* sor = container_of(a, SoR, action);
	Action* c = scc_parameter_as_action(sor->params->items[0]);
	return c;
}

uint32_t sor_get_sleep_time(Action *a) {
	ASSERT(a->type == KW_SLEEP);
	SoR* sor = container_of(a, SoR, action);
	float time = 100.0 * scc_parameter_as_float(sor->params->items[0]);
	return (uint32_t)time;
}


static ActionOE sor_constructor(const char* keyword, ParameterList params) {
	ParamError* err;
	if (0 == strcmp(keyword, KW_REPEAT)) {
		err = scc_param_checker_check(&pc_repeat, keyword, params);
		keyword = KW_REPEAT;
	} else {
		err = scc_param_checker_check(&pc_sleep, keyword, params);
		keyword = KW_SLEEP;
	}
	if (err != NULL) return (ActionOE)err;
	params = scc_copy_param_list(params);
	
	SoR* sor = malloc(sizeof(SoR));
	if ((sor == NULL) || (params == NULL)) {
		list_free(params);
		free(sor);
		return (ActionOE)scc_oom_action_error();
	}
	scc_action_init(&sor->action, keyword, AF_ACTION, &sor_dealloc, &sor_to_string);
	sor->action.compress = &compress;
	sor->action.button_press = &button_press;
	sor->action.button_release = &button_release;
	sor->action.extended.get_child = &get_child;
	
	sor->params = params;
	sor->macro = NULL;
	return (ActionOE)&sor->action;
}


void scc_actions_init_sor() {
	scc_param_checker_init(&pc_sleep, "f");
	scc_param_checker_init(&pc_repeat, "a");
	scc_action_register(KW_SLEEP, &sor_constructor);
	scc_action_register(KW_REPEAT, &sor_constructor);
}

