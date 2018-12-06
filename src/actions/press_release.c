/**
 * SC-Controller - Press & Release
 *
 * 'press' presses the button and leaves it pressed.
 * 'release' releases button.
 * Both make most sense as part of macro.
 *
 * Internally, both are represented by same structure.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"

const char* KW_PRESS = "press";
const char* KW_RELEASE = "release";

typedef struct {
	Action				action;
	Action*				child;
	ParameterList		params;
} PoR;

ACTION_MAKE_TO_STRING(PoR, por, _a->type, NULL);

static void por_dealloc(Action* a) {
	PoR* por = container_of(a, PoR, action);
	list_free(por->params);
	RC_REL(por->child);
	free(por);
}

static Action* compress(Action* a) {
	PoR* por = container_of(a, PoR, action);
	scc_action_compress(&por->child);
	return a;
}

static void button_press(Action* a, Mapper* m) {
	if (a->type == KW_PRESS) {
		PoR* por = container_of(a, PoR, action);
		por->child->button_press(por->child, m);
	}
}

static void button_release(Action* a, Mapper* m) {
	if (a->type == KW_RELEASE) {
		PoR* por = container_of(a, PoR, action);
		por->child->button_release(por->child, m);
	}
}


static ActionOE por_constructor(const char* keyword, ParameterList params) {
	keyword = (0 == strcmp(keyword, KW_PRESS)) ? KW_PRESS : KW_RELEASE;
	if (list_len(params) != 1) {
		return (ActionOE)scc_new_param_error(AEC_INVALID_NUMBER_OF_PARAMETERS,
								"Invalid number of parameters for '%s'", keyword);
	}
	
	Parameter* p = list_get(params, 0);
	Action* child = NULL;
	switch (scc_parameter_type(p)) {
		case PT_INT:
		case PT_FLOAT:
			child = scc_button_action_from_keycode(scc_parameter_as_int(p));
			break;
		case PT_ACTION:
			child = scc_parameter_as_action(p);
			RC_ADD(child);
			break;
		default:
			return (ActionOE)scc_new_invalid_parameter_type_error(keyword, 0, p);
	}
	
	params = scc_copy_param_list(params);
	PoR* por = malloc(sizeof(PoR));
	if ((por == NULL) || (params == NULL) || (child == NULL)) {
		list_free(params);
		RC_REL(child);
		free(por);
		return (ActionOE)scc_oom_action_error();
	}
	scc_action_init(&por->action, keyword, AF_ACTION, &por_dealloc, &por_to_string);
	por->action.compress = &compress;
	por->action.button_press = &button_press;
	por->action.button_release = &button_release;
	
	por->params = params;
	por->child = child;
	return (ActionOE)&por->action;
}


void scc_actions_init_por() {
	scc_action_register(KW_PRESS, &por_constructor);
	scc_action_register(KW_RELEASE, &por_constructor);
}
