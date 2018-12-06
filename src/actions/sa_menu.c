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
#include "tostring.h"
#include <stdlib.h>
#include <stdio.h>

static ParamChecker pc;
#define DEFAULT_POSITION_X		10
#define DEFAULT_POSITION_Y		-10

static const char* KW_MENU = "menu";

typedef enum {
	MT_MENU,			// Default type
	MT_HORIZONTAL,		// Same as default, but prefers packing items into row
	MT_GRID,			// Packs items into grid
	MT_QUICK,			// Quickmenu. Max.6 items, controller by buttons
	MT_RADIAL,			// Big (and ugly) wheel of items
} MenuType;

typedef struct {
	Action				action;
	ParameterList		params;
	SAMenuActionData	data;
	double				stick_distance;
} SAMenuAction;


ACTION_MAKE_TO_STRING(SAMenuAction, sa_menu, _a->type, &pc);

static void sa_menu_dealloc(Action* a) {
	SAMenuAction* sa = container_of(a, SAMenuAction, action);
	list_free(sa->params);
	free(sa);
}

// For button press, release and trigger, it's safe to assume that they are being pressed...
static void button_press(Action* a, Mapper* m) {
	SAMenuAction* sa = container_of(a, SAMenuAction, action);
	if ((m->special_action == NULL) || !m->special_action(m, SAT_MENU, &sa->data))
		DWARN("Mapper lacks support for 'menu'");
}

static void button_release(Action* a, Mapper* m) {
	SAMenuAction* sa = container_of(a, SAMenuAction, action);
}


static ActionOE sa_menu_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	SAMenuAction* sa = malloc(sizeof(SAMenuAction));
	if (sa == NULL) return (ActionOE)scc_oom_action_error();
	scc_action_init(&sa->action, KW_MENU, AF_SPECIAL_ACTION, &sa_menu_dealloc, &sa_menu_to_string);
	sa->action.button_press = &button_press;
	sa->action.button_release = &button_release;
	
	sa->params = params;
	sa->data.menu_id = scc_parameter_as_string(params->items[0]);	// this string will be kept in mem until sa->params is freed
	sa->data.control_with = scc_parameter_as_int(params->items[1]);
	sa->data.confirm_with = scc_parameter_as_int(params->items[2]);
	sa->data.cancel_with = scc_parameter_as_int(params->items[3]);
	sa->data.show_with_release = scc_parameter_as_int(params->items[4]) ? true: false;
	sa->data.size = scc_parameter_as_int(params->items[5]);
	sa->stick_distance = 0;
	vec_set(sa->data.position, DEFAULT_POSITION_X, DEFAULT_POSITION_Y);
	
	return (ActionOE)&sa->action;
}


void scc_actions_init_sa_menu() {
	scc_param_checker_init(&pc, "si?i?i?b?i?");
	scc_param_checker_set_defaults(&pc, SCC_DEFAULT, SCC_DEFAULT, SCC_DEFAULT, SCC_False, 0);
	scc_action_register(KW_MENU, &sa_menu_constructor);
}
