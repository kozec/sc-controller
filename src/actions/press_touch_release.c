/**
 * SC-Controller - Press & Release
 *
 * 'press'     presses the button and leaves it pressed.
 * 'release'   releases the button.
 * Both make most sense as part of macro.
 *
 * 'pressed'   creates action that occurs for brief moment when button is pressed
 * 'released'  creates action that occurs after button is released
 * 'touched'   creates action that occurs for when finger touches the pad
 * 'untouched  creates action that occurs after finger is lifted from the pad
 *
 * Internally, all of above is represented by same structure.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "scc/tools.h"
#include "tostring.h"

const char* KW_PRESS = "press";
const char* KW_RELEASE = "release";
const char* KW_PRESSED = "pressed";
const char* KW_RELEASED = "released";
const char* KW_TOUCHED = "touched";
const char* KW_UNTOUCHED = "untouched";

typedef struct {
	Action				action;
	Action*				child;
	ParameterList		params;
} PoR;

ACTION_MAKE_TO_STRING(PoR, por, _a->type, NULL);

static char* describe(Action* a, ActionDescContext ctx) {
	PoR* por = container_of(a, PoR, action);
	char* cdesc = scc_action_get_description(por->child, ctx);
	StrBuilder* sb = strbuilder_new();
	if ((sb == NULL) || (cdesc == NULL)) {
		strbuilder_free(sb);
		free(cdesc);
		return NULL;
	}
	if (a->type == KW_PRESS)
		strbuilder_add(sb, "(pressed)");
	else if (a->type == KW_RELEASE)
		strbuilder_add(sb, "(release)");
	else if (a->type == KW_PRESSED)
		strbuilder_add(sb, "(when pressed)");
	else if (a->type == KW_RELEASED)
		strbuilder_add(sb, "(when released)");
	else if (a->type == KW_TOUCHED)
		strbuilder_add(sb, "(when touched)");
	else if (a->type == KW_UNTOUCHED)
		strbuilder_add(sb, "(when untouched)");
	
	if ((ctx == AC_STICK) || (ctx == AC_PAD))
		strbuilder_add(sb, "\n");
	else
		strbuilder_add(sb, "\n");
	
	strbuilder_add(sb, cdesc);
	return strbuilder_consume(sb);
}

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

static void on_timer(Mapper* m, void* a) {
	PoR* por = container_of(a, PoR, action);
	por->child->button_release(por->child, m);
	RC_REL((Action*)a);
}

static void button_press(Action* a, Mapper* m) {
	PoR* por = container_of(a, PoR, action);
	if (a->type == KW_PRESS) {
		por->child->button_press(por->child, m);
	} else if (a->type == KW_PRESSED) {
		por->child->button_press(por->child, m);
		RC_ADD(a);
		m->schedule(m, 10, on_timer, a);
	}
}

static void button_release(Action* a, Mapper* m) {
	PoR* por = container_of(a, PoR, action);
	if (a->type == KW_RELEASE) {
		por->child->button_release(por->child, m);
	} else if (a->type == KW_RELEASED) {
		por->child->button_press(por->child, m);
		RC_ADD(a);
		m->schedule(m, 10, on_timer, a);
	}
}

static void whole(Action* a, Mapper* m, AxisValue _x, AxisValue _y, PadStickTrigger what) {
	SCButton b = scc_what_to_touch_button(what);
	PoR* por = container_of(a, PoR, action);
	if (a->type == KW_TOUCHED) {
		if (!m->was_pressed(m, b) && m->is_pressed(m, b)) {
			// Just touched the pad
			por->child->button_press(por->child, m);
			RC_ADD(a);
			m->schedule(m, 10, on_timer, a);
		}
	} else if (a->type == KW_UNTOUCHED) {
		if (m->was_pressed(m, b) && !m->is_pressed(m, b)) {
			// Just released the pad
			por->child->button_press(por->child, m);
			RC_ADD(a);
			m->schedule(m, 10, on_timer, a);
		}
	}
}


static ActionOE por_constructor(const char* keyword, ParameterList params) {
	if (0 == strcmp(keyword, KW_PRESS))
		keyword = KW_PRESS;
	else if (0 == strcmp(keyword, KW_RELEASE))
		keyword = KW_RELEASE;
	else if (0 == strcmp(keyword, KW_PRESSED))
		keyword = KW_PRESSED;
	else if (0 == strcmp(keyword, KW_RELEASED))
		keyword = KW_RELEASED;
	else if (0 == strcmp(keyword, KW_TOUCHED))
		keyword = KW_TOUCHED;
	else
		keyword = KW_UNTOUCHED;
	
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
	por->action.describe = &describe;
	por->action.button_press = &button_press;
	por->action.button_release = &button_release;
	por->action.whole = &whole;
	
	por->params = params;
	por->child = child;
	return (ActionOE)&por->action;
}


void scc_actions_init_por() {
	scc_action_register(KW_PRESS, &por_constructor);
	scc_action_register(KW_RELEASE, &por_constructor);
	scc_action_register(KW_RELEASED, &por_constructor);
	scc_action_register(KW_PRESSED, &por_constructor);
	scc_action_register(KW_TOUCHED, &por_constructor);
	scc_action_register(KW_UNTOUCHED, &por_constructor);
}

