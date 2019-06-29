/*
 * SC-Controller - Tilt
 *
 * Activates one of 6 defined actions based on direction in
 * which controller is tilted or rotated.
 *
 * Order of actions / parameters:
 *   - Front faces down
 *   - Front faces up
 *   - Tilted left
 *   - Tilted right
 *   - Rotated left
 *   - Rotated right
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/action.h"
#include "tostring.h"
#include "props.h"
static ParamChecker pc;

static const char* KW_TILT = "tilt";

#define MIN 0.75

typedef struct {
	Action				action;
	ParameterList		params;
	Action*				actions[6];
	bool				states[6];
	double				sensitivity[3];
} TiltAction;


ACTION_MAKE_TO_STRING(TiltAction, tilt, _a->type, &pc);


static char* describe(Action* a, ActionDescContext ctx) {
	// DPadAction* dpad = container_of(a, DPadAction, action);
	// TODO: This
	return strbuilder_cpy("tilt");
}

static void tilt_dealloc(Action* a) {
	TiltAction* t = container_of(a, TiltAction, action);
	for (uint8_t i=0; i<6; i++) {
		RC_REL(t->actions[i]);
	}
	list_free(t->params);
	free(t);
}


static void gyro(Action* a, Mapper* m, const struct GyroInput* value) {
	TiltAction* t = container_of(a, TiltAction, action);
	double pyr[3];
	quat2euler(pyr, value->q0 / 32768.0, value->q1 / 32768.0,
					value->q2 / 32768.0, value->q3 / 32768.0);
	
	for (int j=0; j<3; j++) {
		int i = j * 2;
		if (t->actions[i]) {
			if (pyr[j] < MIN * -1 / t->sensitivity[j]) {
				// Side faces down
				if (!t->states[i]) {
					t->actions[i]->button_press(t->actions[i], m);
					t->states[i] = true;
				} else if (t->states[i]) {
					t->actions[i]->button_release(t->actions[i], m);
					t->states[i] = false;
				}
			}
		}
		if (t->actions[i]) {
			if (pyr[j] > MIN / t->sensitivity[j]) {
				// Side faces up
				if (!t->states[i+1]) {
					t->actions[i+1]->button_press(t->actions[i+1], m);
					t->states[i+1] = true;
				} else if (t->states[i+1]) {
					t->actions[i+1]->button_release(t->actions[i+1], m);
					t->states[i+1] = false;
				}
			}
		}
	}
}


static ActionList get_children(Action* a) {
	TiltAction* t = container_of(a, TiltAction, action);
	ActionList lst = scc_make_action_list(NULL);
	if (lst == NULL) return NULL;
	for (size_t i=0; i<6; i++) {
		if (t->actions[i] != NoAction) {
			if (!list_add(lst, t->actions[i])) {
				list_free(lst);
				return NULL;
			}
			RC_ADD(t->actions[i]);
		}
	}
	return lst;
}

static Parameter* get_property(Action* a, const char* name) {
	TiltAction* t = container_of(a, TiltAction, action);
	if (0 == strcmp(name, "sensitivity")) {
		Parameter* xyz[] = {
			scc_new_float_parameter(t->sensitivity[0]),
			scc_new_float_parameter(t->sensitivity[1]),
			scc_new_float_parameter(t->sensitivity[2])
		};
		if ((xyz[0] == NULL) || (xyz[1] == NULL) || (xyz[2] == NULL)) {
			free(xyz[0]); free(xyz[1]); free(xyz[2]);
			return NULL;
		}
		return scc_new_tuple_parameter(3, xyz);
	}
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}

static void set_sensitivity(Action* a, float x, float y, float z) {
	TiltAction* t = container_of(a, TiltAction, action);
	t->sensitivity[0] = x;
	t->sensitivity[1] = y;
	t->sensitivity[2] = z;
}


static ActionOE tilt_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	TiltAction* t = malloc(sizeof(TiltAction));
	if (t == NULL) return (ActionOE)scc_oom_action_error();
	
	scc_action_init(&t->action, KW_TILT,
					AF_ACTION | AF_MOD_SENSITIVITY | AF_MOD_SENS_Z,
					&tilt_dealloc, &tilt_to_string);
	
	t->action.gyro = &gyro;
	t->action.describe = &describe;
	t->action.get_property = &get_property;
	t->action.extended.get_children = &get_children;
	t->action.extended.set_sensitivity = &set_sensitivity;
	
	for (uint8_t i=0; i<6; i++) {
		t->actions[i] = scc_parameter_as_action(params->items[i]);
		t->states[i] = false;
		RC_ADD(t->actions[i]);
	}
	t->sensitivity[0] = t->sensitivity[1] = t->sensitivity[2] = 1.0;
	t->params = params;
	
	return (ActionOE)&t->action;
}

void scc_actions_init_tilt() {
	scc_param_checker_init(&pc, "a?a?a a?a?a?");
	scc_param_checker_set_defaults(&pc, NULL, NULL, NULL, NULL, NULL, NULL);
	scc_action_register(KW_TILT, &tilt_constructor);
}

