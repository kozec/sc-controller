/**
 * SC Controller - Special actions - Show Keyboard
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

static const char* KW_KEYBOARD = "keyboard";

static char* sa_keyboard_to_string(Action* a) {
	return strbuilder_fmt("%s()", a->type);
}

static void sa_keyboard_dealloc(Action* a) {
	free(a);
}

static void button_press(Action* a, Mapper* m) {
	if ((m->special_action == NULL) || !m->special_action(m, SAT_KEYBOARD, NULL))
		DWARN("Mapper lacks support for '%s'", a->type);
}


static ActionOE sa_keyboard_constructor(const char* keyword, ParameterList params) {
	if (list_len(params) != 0) {
		return (ActionOE)scc_new_action_error(AEC_INVALID_NUMBER_OF_PARAMETERS, "'%s' takes no parameters", keyword);
	}
	
	Action* a = malloc(sizeof(Action));
	if (a == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(a, KW_KEYBOARD, AF_SPECIAL_ACTION, &sa_keyboard_dealloc, &sa_keyboard_to_string);
	a->button_press = &button_press;
	
	return (ActionOE)a;
}


void scc_actions_init_sa_keyboard() {
	scc_action_register(KW_KEYBOARD, &sa_keyboard_constructor);
}

