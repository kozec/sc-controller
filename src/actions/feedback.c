/**
 * SC Controller - Feedback modifier
 *
 * Enables feedback for action if action supports it.
*/

#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"
#include "props.h"
#include <sys/time.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_FEEDBACK = "feedback";

typedef struct {
	Action				action;
	Action*				child;
	ParameterList		params;
	HapticData			hdata;
} FeedbackModifier;

ACTION_MAKE_TO_STRING(FeedbackModifier, feedback, KW_FEEDBACK, &pc);

static char* describe(Action* a, ActionDescContext ctx) {
	FeedbackModifier* f = container_of(a, FeedbackModifier, action);
	return scc_action_get_description(f->child, ctx);
}

static void feedback_dealloc(Action* a) {
	FeedbackModifier* f = container_of(a, FeedbackModifier, action);
	list_free(f->params);
	RC_REL(f->child);
	free(f);
}

static Action* compress(Action* a) {
	FeedbackModifier* f = container_of(a, FeedbackModifier, action);
	scc_action_compress(&f->child);
	if (f->child->extended.set_haptic != NULL)
		f->child->extended.set_haptic(f->child, f->hdata);
	return f->child;
}

static Action* get_child(Action* a) {
	FeedbackModifier* f = container_of(a, FeedbackModifier, action);
	RC_ADD(f->child);
	return f->child;
}

static Parameter* get_property(Action* a, const char* name) {
	FeedbackModifier* f = container_of(a, FeedbackModifier, action);
	MAKE_HAPTIC_PROPERTY(f->hdata, "haptic");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE feedback_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	FeedbackModifier* f = malloc(sizeof(FeedbackModifier));
	if (f == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&f->action, KW_FEEDBACK, AF_MODIFIER, &feedback_dealloc, &feedback_to_string);
	f->action.describe = &describe;
	f->action.compress = &compress;
	f->action.get_property = &get_property;
	f->action.extended.get_child = &get_child;
	
	const char* pos = scc_parameter_as_string(params->items[0]);
	if (0 == strcmp(pos, "LEFT"))
		f->hdata.pos = HAPTIC_LEFT;
	else if (0 == strcmp(pos, "RIGHT"))
		f->hdata.pos = HAPTIC_RIGHT;
	else if (0 == strcmp(pos, "BOTH"))
		f->hdata.pos = HAPTIC_BOTH;
	else {
		free(f);
		return (ActionOE)scc_new_param_error(AEC_INVALID_VALUE,
			"'%s' cannot take '%s' as 1st parameter", keyword, pos);
	}
	f->hdata.amplitude = scc_parameter_as_int(params->items[1]);
	f->hdata.frequency = 1000.0f * scc_parameter_as_float(params->items[2]);
	f->hdata.period = scc_parameter_as_int(params->items[3]);
	f->child = scc_parameter_as_action(params->items[4]);
	if (f->hdata.frequency < 1.0f) f->hdata.frequency = 1.0f;
	f->params = params;
	
	RC_ADD(f->child);
	return (ActionOE)&f->action;
}


void scc_actions_init_feedback() {
	scc_param_checker_init(&pc, "sc?f?c?a");
	scc_param_checker_set_defaults(&pc, 512, 4.0, 1024);
	scc_action_register(KW_FEEDBACK, &feedback_constructor);
}
