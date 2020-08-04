/**
 * SC Controller - Stubs for not-yet-implemented modifiers
 *
 * Everything here is represented by same structure;
 * It has child and that child is called when stuff happens. Modifier by itself does nothing.
*/
#include "scc/utils/logging.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"
#include "macros.h"
#include "props.h"

const char* KW_CIRCULAR = "circular";
const char* KW_CIRCULAR_ABS = "circularabs";
const char* KW_RESETGYRO = "resetgyro";
const char* KW_CLEAROSD = "clearosd";
const char* KW_OSD = "osd";
const char* KW_ROTATE = "rotate";
const char* KW_GESTURES = "gestures";
const char* KW_POSITION = "position";
const char* KW_RESTART = "restart";
const char* KW_SHELL = "shell";
const char* KW_AREA = "area";
const char* KW_REL_AREA = "relarea";
const char* KW_WIN_AREA = "winarea";
const char* KW_REL_WIN_AREA = "relwinarea";
const char* KW_QUICK_MENU = "quickmenu";


static ParamChecker pc_circular;
static ParamChecker pc_osd;
static ParamChecker pc_rotate;
static ParamChecker pc_position;
static ParamChecker pc_shell;
static ParamChecker pc_area;
static ParamChecker pc_no_args;

typedef struct {
	Action				action;
	Action*				child;
	ActionList			children;
	ParameterList		params;
	ParamChecker*		pc;
} Stub;

ACTION_MAKE_TO_STRING(Stub, stub, _a->type, a->pc);

static void stub_dealloc(Action* a) {
	Stub* b = container_of(a, Stub, action);
	if (b->child != NULL) RC_REL(b->child);
	if (b->children != NULL) list_free(b->children);
	list_free(b->params);
	free(b);
}

static Action* compress(Action* a) {
	Stub* b = container_of(a, Stub, action);
	if (b->children)
		compress_actions(b->children);
	if (b->child != NULL) {
		scc_action_compress(&b->child);
		return b->child;
	}
	return a;
}

static Action* get_child(Action* a) {
	Stub* b = container_of(a, Stub, action);
	if (b->child != NULL) {
		RC_ADD(b->child);
		return b->child;
	}
	return NoAction;
}

static ActionList get_children(Action* a) {
	Stub* b = container_of(a, Stub, action);
	return scc_copy_action_list(b->children);
}


static ActionOE stub_constructor(const char* keyword, ParameterList params) {
	ParamChecker* pc;
	ActionFlags flags;
	if (0 == strcmp(KW_CIRCULAR, keyword)) {
		keyword = KW_CIRCULAR;
		flags = AF_ACTION;
		pc = &pc_circular;
	} else if (0 == strcmp(KW_CIRCULAR_ABS, keyword)) {
		keyword = KW_CIRCULAR_ABS;
		flags = AF_ACTION;
		pc = &pc_circular;
	} else if (0 == strcmp(KW_RESETGYRO, keyword)) {
		keyword = KW_RESETGYRO;
		flags = AF_ACTION;
		pc = &pc_no_args;
	} else if (0 == strcmp(KW_CLEAROSD, keyword)) {
		keyword = KW_CLEAROSD;
		flags = AF_ACTION;
		pc = &pc_no_args;
	} else if (0 == strcmp(KW_RESTART, keyword)) {
		keyword = KW_RESTART;
		flags = AF_ACTION;
		pc = &pc_no_args;
	} else if (0 == strcmp(KW_OSD, keyword)) {
		keyword = KW_OSD;
		flags = AF_MODIFIER;
		pc = &pc_osd;
	} else if (0 == strcmp(KW_ROTATE, keyword)) {
		keyword = KW_ROTATE;
		flags = AF_MODIFIER;
		pc = &pc_rotate;
	} else if (0 == strcmp(KW_GESTURES, keyword)) {
		keyword = KW_GESTURES;
		flags = AF_ACTION;
		pc = NULL;
	} else if (0 == strcmp(KW_SHELL, keyword)) {
		keyword = KW_SHELL;
		flags = AF_ACTION;
		pc = &pc_shell;
	} else if (0 == strcmp(KW_POSITION, keyword)) {
		keyword = KW_POSITION;
		flags = AF_ACTION;
		pc = &pc_position;
	} else if (0 == strcmp(KW_AREA, keyword)) {
		keyword = KW_AREA;
		flags = AF_ACTION;
		pc = &pc_area;
	} else if (0 == strcmp(KW_REL_AREA, keyword)) {
		keyword = KW_REL_AREA;
		flags = AF_ACTION;
		pc = &pc_area;
	} else if (0 == strcmp(KW_WIN_AREA, keyword)) {
		keyword = KW_WIN_AREA;
		flags = AF_ACTION;
		pc = &pc_area;
	} else if (0 == strcmp(KW_REL_WIN_AREA, keyword)) {
		keyword = KW_REL_WIN_AREA;
		flags = AF_ACTION;
		pc = &pc_area;
	} else if (0 == strcmp(KW_QUICK_MENU, keyword)) {
		keyword = KW_QUICK_MENU;
		flags = AF_ACTION;
		pc = NULL;
	} else {
		return (ActionOE)scc_new_action_error(AEC_PARSE_ERROR, "Unknown keyword for stub: '%s'", keyword);
	}
	
	if (pc != NULL) {
		ParamError* err = scc_param_checker_check(pc, keyword, params);
		if (err != NULL) return (ActionOE)err;
		params = scc_param_checker_fill_defaults(pc, params);
	} else {
		params = scc_copy_param_list(params);
	}
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	Stub* b = malloc(sizeof(Stub));
	if (b == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&b->action, keyword, flags, &stub_dealloc, &stub_to_string);
	b->action.compress = &compress;
	b->action.extended.get_child = &get_child;
	b->action.extended.get_children = &get_children;
	
	b->params = params;
	b->pc = pc;
	b->child = NULL;
	b->children = NULL;
	
	if ((keyword == KW_CIRCULAR) || (keyword == KW_CIRCULAR_ABS)) {
		b->children = scc_make_action_list(
				scc_parameter_as_action(list_get(params, 0)),
				scc_parameter_as_action(list_get(params, 1)));
	} else if (keyword == KW_OSD) {
		b->child = scc_parameter_as_action(list_get(params, 1));
	} else if (keyword == KW_ROTATE) {
		b->child = scc_parameter_as_action(list_get(params, 1));
	} else if (keyword == KW_POSITION) {
		b->child = scc_parameter_as_action(list_get(params, 2));
	}
	return (ActionOE)&b->action;
}


void scc_actions_init_stub() {
	scc_param_checker_init(&pc_no_args, "");
	
	scc_param_checker_init(&pc_circular, "a?a?");
	scc_param_checker_set_defaults(&pc_circular, NoAction, NoAction);
	
	scc_param_checker_init(&pc_rotate, "fa");
	
	scc_param_checker_init(&pc_shell, "s");
	
	scc_param_checker_init(&pc_position, "iia");
	
	scc_param_checker_init(&pc_area, "ffff");
	
	scc_param_checker_init(&pc_osd, "s?a?");
	scc_param_checker_set_defaults(&pc_osd, "", NoAction);
	
	scc_action_register(KW_CIRCULAR, &stub_constructor);
	scc_action_register(KW_CIRCULAR_ABS, &stub_constructor);
	scc_action_register(KW_RESETGYRO, &stub_constructor);
	scc_action_register(KW_CLEAROSD, &stub_constructor);
	scc_action_register(KW_OSD, &stub_constructor);
	scc_action_register(KW_GESTURES, &stub_constructor);
	scc_action_register(KW_POSITION, &stub_constructor);
	scc_action_register(KW_RESTART, &stub_constructor);
	scc_action_register(KW_SHELL, &stub_constructor);
	scc_action_register(KW_AREA, &stub_constructor);
	scc_action_register(KW_REL_AREA, &stub_constructor);
	scc_action_register(KW_WIN_AREA, &stub_constructor);
	scc_action_register(KW_REL_WIN_AREA, &stub_constructor);
	scc_action_register(KW_QUICK_MENU, &stub_constructor);
}

