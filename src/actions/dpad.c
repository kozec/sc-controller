#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "props.h"
#include <stdlib.h>
#include <string.h>
#include <tgmath.h>
#include <stdio.h>

static ParamChecker pc4;
static ParamChecker pc8;
static const char* KW_DPAD4 = "dpad";
static const char* KW_DPAD8 = "dpad8";

// Power of 2 from minimal distance that finger has to be from center
#define MIN_DISTANCE_P2 (double)2000000
#define DEFAULT_DIAGONAL_RANGE ((int64_t)45)
typedef int8_t side;
#ifndef M_PI
#define M_PI		3.14159265358979323846
#endif

typedef struct {
	double			start;
	double			end;
	uint8_t			index;
} DPadRange;

typedef struct {
	Action			action;
	Parameter*		first_param;
	uint8_t			size;
	uint16_t		diagonal_range;
	side			state[2];
	Action*			actions[8];
	DPadRange		ranges[9];
} DPadAction;

const side DPAD_SIDES[9][2] = {
	// Just list of magic numbers that would have
	// to be computed on the fly otherwise
	// 0 - up, 1 - down, 2 - left, 3 - right, -1 - Nothing
	{ -1, 1 },			// Index 0, down
	{ 2,  1 },			// Index 1, down-left
	{ 2, -1 },			// Index 2, left
	{ 2,  0 },			// Index 3, up-left
	{ -1, 0 },			// Index 4, up
	{ 3,  0 },			// Index 5, up-right
	{ 3, -1 },			// Index 6, right
	{ 3,  1 },			// Index 7, down-right
	{ -1, 1 },			// Index 8, same as 0
};

static char* dpad_to_string(Action* a) {
	DPadAction* dpad = container_of(a, DPadAction, action);
	RC_ADD(dpad->first_param);
	ParameterList l =
		scc_inline_param_list(
			dpad->first_param,
			scc_new_action_parameter(dpad->actions[0]),
			scc_new_action_parameter(dpad->actions[1]),
			scc_new_action_parameter(dpad->actions[2]),
			scc_new_action_parameter(dpad->actions[3]),
			scc_new_action_parameter(dpad->actions[4]),
			scc_new_action_parameter(dpad->actions[5]),
			scc_new_action_parameter(dpad->actions[6]),
			scc_new_action_parameter(dpad->actions[7])
		//)
	);
	
	l = scc_param_checker_strip_defaults(&pc8, l);
	
	char* strl = scc_param_list_to_string(l);
	char* rv = (strl == NULL) ? NULL : strbuilder_fmt("dpad(%s)", strl);
	
	list_free(l);
	free(strl);
	return rv;
}

static char* describe(Action* a, ActionDescContext ctx) {
	// DPadAction* dpad = container_of(a, DPadAction, action);
	// TODO: Detect WSAD, detect arrows
	return strbuilder_cpy("DPad");
}

static void dpad_dealloc(Action* a) {
	DPadAction* dpad = container_of(a, DPadAction, action);
	RC_REL(dpad->first_param);
	for (size_t i=0; i<8; i++)
		RC_REL(dpad->actions[i]);
	free(dpad);
}

/** Computes which sides of dpad are supposed to be active */
void compute_side(DPadAction* d, AxisValue x, AxisValue y, side rv[2]) {
	// dpad(up, down, left, right)
	// dpad8(up, down, left, right, upleft, upright, downleft, downright)
	rv[0] = rv[1] = -1;
	double distance = pow(x, 2) + pow(y, 2);
	if (distance > MIN_DISTANCE_P2) {
		// Compute angle from center of pad to finger position
		double angle = (atan2(x, y) * 180.0 / M_PI) + 180.0;
		// Translate it to index
		int8_t index = 0;
		for (uint8_t i=0; i<9; i++) {
			if ((angle >= d->ranges[i].start) && (angle < d->ranges[i].end)) {
				index = d->ranges[i].index;
				break;
			}
		}
		rv[0] = DPAD_SIDES[index][0];
		rv[1] = DPAD_SIDES[index][1];
	}
}

static void whole(Action* _a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	DPadAction* dpad = container_of(_a, DPadAction, action);
	side sides[2];
	compute_side(dpad, x, y, sides);
	
	for (uint8_t i=0; i<=1; i++) {
		if ((sides[i] != dpad->state[i]) && (dpad->state[i] != -1)) {
			Action* a = dpad->actions[dpad->state[i]];
			a->button_release(a, m);
			dpad->state[i] = -1;
		}
		if ((sides[i] != -1) && (sides[i] != dpad->state[i])) {
			Action* a = dpad->actions[sides[i]];
			a->button_press(a, m);
		}
		dpad->state[i] = sides[i];
	}
}

static ActionList get_children(Action* a) {
	DPadAction* dpad = container_of(a, DPadAction, action);
	ActionList lst = scc_make_action_list(NULL);
	if (lst == NULL) return NULL;
	for (size_t i=0; i<8; i++) {
		if (dpad->actions[i] != NoAction) {
			if (!list_add(lst, dpad->actions[i])) {
				list_free(lst);
				return NULL;
			}
			RC_ADD(dpad->actions[i]);
		}
	}
	return lst;
}

static Parameter* get_property(Action* a, const char* name) {
	DPadAction* dpad = container_of(a, DPadAction, action);
	MAKE_INT_PROPERTY(dpad->diagonal_range, "diagonal_range");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE dpad_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc8, keyword, params);
	
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc8, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	DPadAction* dpad = malloc(sizeof(DPadAction));
	if (dpad == NULL) {
		list_free(params);
		return (ActionOE)scc_oom_action_error();
	}
	scc_action_init(&dpad->action, KW_DPAD4,
					AF_ACTION | AF_MOD_CLICK | AF_MOD_ROTATE
						| AF_MOD_DEADZONE | AF_MOD_FEEDBACK,
					&dpad_dealloc, &dpad_to_string);
	dpad->action.describe = &describe;
	dpad->action.whole = &whole;
	dpad->action.get_property = &get_property;
	dpad->action.extended.get_children = &get_children;
	
	dpad->size = 8;			// TODO: Is this needed?
	dpad->state[0] = -1;
	dpad->state[1] = -1;
	dpad->first_param = params->items[0];
	RC_ADD(dpad->first_param);
	for (uint8_t i=0; i<8; i++) {
		dpad->actions[i] = scc_parameter_as_action(params->items[i + 1]);
		RC_ADD(dpad->actions[i]);
	}
	
	dpad->diagonal_range = scc_parameter_as_int(params->items[0]);
	uint16_t normal_range = 90 - dpad->diagonal_range;
	uint16_t i = 360 - (normal_range / 2);
	uint16_t j = 0;
	for (uint8_t x=0; x<9; x++) {
		uint16_t r = normal_range;
		if ((x % 2) == 0) {
			r = dpad->diagonal_range;
		}
		
		j = i;
		i = (i + r) % 360;
		DPadRange range = { (double)j, (double)i, x % 8 };
		dpad->ranges[x] = range;
	}
	
	list_free(params);
	return (ActionOE)&dpad->action;
}

void scc_actions_init_dpad() {
	scc_param_checker_init(&pc4, "c? a?a?a?a?");
	scc_param_checker_init(&pc8, "c? a?a?a?a? a?a?a?a?");
	// pc8 is used to add defaults in both cases, so pc4 defaults are not initialized
	scc_param_checker_set_defaults(&pc8, DEFAULT_DIAGONAL_RANGE,
		NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);	// 8 NULLs
	scc_action_register(KW_DPAD4, &dpad_constructor);
	scc_action_register(KW_DPAD8, &dpad_constructor);		// for backwards compatibility
}

