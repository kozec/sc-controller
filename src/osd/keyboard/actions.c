#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/special_action.h"
#include "scc/parameter.h"
#include "scc/action.h"
#include <string.h>

const char* KW_OSK_CURSOR = "OSK.cursor";
const char* KW_OSK_CLOSE = "OSK.close";
const char* KW_OSK_PRESS = "OSK.press";

typedef struct {
	Action				action;
	ParameterList		params;
	int					index;
} OSKAction;

static char* osk_action_to_string(Action* a) {
	OSKAction* b = container_of(a, OSKAction, action);
	char* parmsstr = scc_param_list_to_string(b->params);
	if (parmsstr == NULL)
		return NULL;
	char* rv = strbuilder_fmt("%s(%s)", a->type, parmsstr);
	free(parmsstr);
	return rv;
}

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	OSKAction* b = container_of(a, OSKAction, action);
	if (a->type == KW_OSK_CURSOR) {
		AxisValue values[3] = { b->index, x, y };
		SAAppDefinedActionData data = { KW_OSK_CURSOR, sizeof(values), &values };
		m->special_action(m, SAT_APP_DEFINED, &data);
	}
}

static void button_press(Action* a, Mapper* m) {
	OSKAction* b = container_of(a, OSKAction, action);
	if (a->type == KW_OSK_CLOSE) {
		SAAppDefinedActionData data = { KW_OSK_CLOSE, 0, NULL };
		m->special_action(m, SAT_APP_DEFINED, &data);
	} else if (a->type == KW_OSK_PRESS) {
		AxisValue values[2] = { b->index, 1 };
		SAAppDefinedActionData data = { KW_OSK_PRESS, sizeof(values), &values };
		m->special_action(m, SAT_APP_DEFINED, &data);
	}
}

static void button_release(Action* a, Mapper* m) {
	OSKAction* b = container_of(a, OSKAction, action);
	if (a->type == KW_OSK_PRESS) {
		AxisValue values[2] = { b->index, 0 };
		SAAppDefinedActionData data = { KW_OSK_PRESS, sizeof(values), &values };
		m->special_action(m, SAT_APP_DEFINED, &data);
	}
}

static void trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	OSKAction* b = container_of(a, OSKAction, action);
	if ((old_pos < TRIGGER_MAX) && (pos == TRIGGER_MAX))
		button_release(a, m);
	else if ((old_pos == TRIGGER_MAX) && (pos < TRIGGER_MAX))
		button_press(a, m);
}

static void osk_action_dealloc(Action* a) {
	OSKAction* b = container_of(a, OSKAction, action);
	list_free(b->params);
	free(b);
}


static ActionOE keyboard_action(const char* keyword, ParameterList params) {
	if ((strcmp(keyword, KW_OSK_CURSOR) == 0) || (strcmp(keyword, KW_OSK_PRESS) == 0)) {
		keyword = (strcmp(keyword, KW_OSK_CURSOR) == 0) ? KW_OSK_CURSOR : KW_OSK_PRESS;
		if (list_len(params) != 1)
			return (ActionOE)scc_new_action_error(AEC_INVALID_VALUE, "%s takes exactly one parameter", keyword);
		if ((list_get(params, 0)->type & PT_STRING) == 0)
			return (ActionOE)scc_new_invalid_parameter_type_error(keyword, 1, list_get(params, 0));
	} else if (strcmp(keyword, KW_OSK_CLOSE) == 0) {
		keyword = KW_OSK_CLOSE;
		if (list_len(params) != 0)
			return (ActionOE)scc_new_action_error(AEC_INVALID_VALUE, "%s takes no parameters", keyword);
	} else {
		return (ActionOE)scc_new_action_error(AEC_INVALID_VALUE, "Unknown keyword '%s'", keyword);
	}
	
	params = scc_copy_param_list(params);
	OSKAction* b = malloc(sizeof(OSKAction));
	if ((b == NULL) || (params == NULL)) {
		free(b);
		list_free(params);
		return (ActionOE)scc_oom_action_error();
	}
	
	scc_action_init(&b->action, keyword, AF_ACTION, &osk_action_dealloc, &osk_action_to_string);
	b->params = params;
	b->index = 0;
	b->action.whole = &whole;
	b->action.trigger = &trigger;
	b->action.button_press = &button_press;
	b->action.button_release = &button_release;
	if ((list_len(params) > 0) && (strcmp("RIGHT", scc_parameter_as_string(list_get(params, 0))) == 0))
		b->index = 1;
	
	return (ActionOE)&b->action;
}


void register_keyboard_actions() {
	if (!scc_action_known(KW_OSK_PRESS)) {
		scc_action_register(KW_OSK_PRESS, &keyboard_action);
		scc_action_register(KW_OSK_CLOSE, &keyboard_action);
		scc_action_register(KW_OSK_CURSOR, &keyboard_action);
	}
}

