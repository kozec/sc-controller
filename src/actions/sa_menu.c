/**
 * SC Controller - Special actions - Menu
 * 
 * Displays on screen menu, either as defined in profile or loaded from file.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/special_action.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "scc/tools.h"
#include "tostring.h"
#include "props.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;
static ParamChecker pc_short;
#define DEFAULT_POSITION_X		10
#define DEFAULT_POSITION_Y		-10

static const char* KW_MENU = "menu";
static const char* KW_HMENU = "hmenu";
static const char* KW_RADIAL_MENU = "radialmenu";
static const char* KW_GRID_MENU = "gridmenu";

typedef struct {
	Action				action;
	ParameterList		params;
	SAMenuActionData	data;
	double				stick_distance;
} SAMenuAction;


ACTION_MAKE_TO_STRING(SAMenuAction, sa_menu, _a->type, &pc);

static char* describe(Action* a, ActionDescContext ctx) {
	return strbuilder_cpy("Menu");
}

static void sa_menu_dealloc(Action* a) {
	SAMenuAction* sa = container_of(a, SAMenuAction, action);
	list_free(sa->params);
	free(sa);
}

// For button press, release and trigger, it's safe to assume that they are being pressed...
static void button_press(Action* a, Mapper* m) {
	SAMenuAction* sa = container_of(a, SAMenuAction, action);
	sa->data.triggered_by = 0;
	if ((m->special_action == NULL) || !m->special_action(m, SAT_MENU, &sa->data))
		DWARN("Mapper lacks support for 'menu'");
}

static void button_release(Action* a, Mapper* m) { }

static void whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	SAMenuAction* sa = container_of(a, SAMenuAction, action);
	if ((x == 0) && (y == 0))
		return;				// Pad was released - don't show anything
	switch (what) {
		case PST_STICK:
			return;			// No menus on stick
		case PST_LPAD:
		case PST_RPAD:
			if (m->was_touched(m, what))
				return;		// Pad was not pressed just now
			break;
		default:
			break;
	}
	sa->data.triggered_by = what;
	if ((m->special_action == NULL) || !m->special_action(m, SAT_MENU, &sa->data))
		DWARN("Mapper lacks support for 'menu'");
}

static Parameter* get_property(Action* a, const char* name) {
	SAMenuAction* sa = container_of(a, SAMenuAction, action);
	MAKE_HAPTIC_PROPERTY(sa->data.hdata, "haptic");
	MAKE_PARAM_PROPERTY(sa->params->items[0], "menu_id");
	MAKE_PARAM_PROPERTY(sa->params->items[1], "control_with");
	MAKE_PARAM_PROPERTY(sa->params->items[2], "confirm_with");
	MAKE_PARAM_PROPERTY(sa->params->items[3], "cancel_with");
	// TODO: This should return boolean, instead of int, dunno how to do that right now
	MAKE_PARAM_PROPERTY(sa->params->items[4], "show_with_release");
	MAKE_PARAM_PROPERTY(sa->params->items[5], "size");
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}

SCButton string_to_confirm_cancel(const char* s) {
	// TODO: Magic strings here
	if (0 == strcmp("ALWAYS", s))
		return SCC_ALWAYS;
	if (0 == strcmp("DEFAULT", s))
		return SCC_DEFAULT;
	if (0 == strcmp("SAME", s))
		return SCC_SAME;
	return scc_string_to_button(s);
}

PadStickTrigger string_to_control(const char* s) {
	if (0 == strcmp("DEFAULT", s))
		return SCC_DEFAULT;
	
	return scc_string_to_pst(s);
}


static ActionOE sa_menu_constructor(const char* keyword, ParameterList params) {
	// Backwards compatibility / convience thing: Menu can have 'short form'
	// where only menu id and size is specified, eg. menu("some-id", 3) 
	ParamError* err = scc_param_checker_check(&pc_short, keyword, params);
	if (err == NULL) {
		// Short form is used
		Parameter* menu_id = params->items[0];
		Parameter* size = params->items[1];
		params = scc_make_param_list(menu_id, scc_new_int_parameter(SCC_False), size);
		if (params == NULL) return (ActionOE)scc_oom_action_error();
	} else {
		RC_REL(err);
	}
	// Full form is tried
	err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	if (strcmp(keyword, KW_HMENU) == 0) keyword = KW_HMENU;
	else if (strcmp(keyword, KW_GRID_MENU) == 0) keyword = KW_GRID_MENU;
	else if (strcmp(keyword, KW_RADIAL_MENU) == 0) keyword = KW_RADIAL_MENU;
	else keyword = KW_MENU;
	
	SAMenuAction* sa = malloc(sizeof(SAMenuAction));
	if (sa == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&sa->action, keyword, AF_SPECIAL_ACTION, &sa_menu_dealloc, &sa_menu_to_string);
	sa->action.describe = &describe;
	sa->action.button_press = &button_press;
	sa->action.button_release = &button_release;
	sa->action.whole = &whole;
	sa->action.get_property = &get_property;
	
	sa->params = params;
	sa->data.menu_id = scc_parameter_as_string(params->items[0]);
	sa->data.menu_type = keyword;
	sa->data.control_with = string_to_control(scc_parameter_as_string(params->items[1]));
	sa->data.confirm_with = string_to_confirm_cancel(scc_parameter_as_string(params->items[2]));
	sa->data.cancel_with = string_to_confirm_cancel(scc_parameter_as_string(params->items[3]));
	sa->data.show_with_release = scc_parameter_as_int(params->items[4]) ? true: false;
	sa->data.size = scc_parameter_as_int(params->items[5]);
	sa->data.triggered_by = 0;
	sa->stick_distance = 0;
	vec_set(sa->data.position, DEFAULT_POSITION_X, DEFAULT_POSITION_Y);
	
	return (ActionOE)&sa->action;
}


void scc_actions_init_sa_menu() {
	scc_param_checker_init(&pc, "sA+?B+?B+?b?i?");
	scc_param_checker_set_defaults(&pc, "DEFAULT", "DEFAULT", "DEFAULT", SCC_False, 0);
	scc_param_checker_init(&pc_short, "si");
	scc_action_register(KW_MENU, &sa_menu_constructor);
	scc_action_register(KW_HMENU, &sa_menu_constructor);
	scc_action_register(KW_GRID_MENU, &sa_menu_constructor);
	scc_action_register(KW_RADIAL_MENU, &sa_menu_constructor);
}

