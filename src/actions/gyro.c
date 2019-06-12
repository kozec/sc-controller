/*
 * SC-Controller - GyroAction
 *
 * Uses *relative* gyroscope position as input for emulated axes
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/conversions.h"
#include "scc/action.h"
#include "wholehaptic.h"
#include "tostring.h"
#include "props.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

static ParamChecker pc;

static const char* KW_GYRO = "gyro";
static const char* KW_GYROABS = "gyroabs";

typedef struct {
	ParameterList		params;
	Action				action;
	Axis				axes[3];
	double				sensitivity[3];
	HapticData			hdata;
} GyroAction;


ACTION_MAKE_TO_STRING(GyroAction, gyro, _a->type, &pc);


static char* describe(Action* a, ActionDescContext ctx) {
	GyroAction* g = container_of(a, GyroAction, action);
	
	if ((g->axes[0] >= REL_X) && (g->axes[0] <= REL_MAX))
		return strbuilder_cpy("Mouse");
	
	StrBuilder* sb = strbuilder_new();
	if (sb == NULL) return NULL;
	
	char* descs[3] = { NULL, NULL, NULL };
	for (int i=0; i<3; i++)
		descs[i] = scc_describe_axis(g->axes[i], 0);
	
	bool joined = strbuilder_join(sb, (const char**)descs, 3, "\n");
	for (int i=0; i<3; i++)
		free(descs[i]);
	
	if (joined) {
		return strbuilder_consume(sb);
	} else {
		strbuilder_free(sb);
		return NULL;
	}
}

static void gyro_dealloc(Action* a) {
	GyroAction* g = container_of(a, GyroAction, action);
	list_free(g->params);
	free(g);
}


static void set_sensitivity(Action* a, float x, float y, float z) {
	GyroAction* g = container_of(a, GyroAction, action);
	g->sensitivity[0] = x;
	g->sensitivity[1] = y;
	g->sensitivity[2] = z;
}

static void set_haptic(Action* a, HapticData hdata) {
	GyroAction* g = container_of(a, GyroAction, action);
	g->hdata = hdata;
}

static void gyro(Action* a, Mapper* m, struct GyroInput* value) {
	GyroAction* g = container_of(a, GyroAction, action);
	GyroValue* pyr = &value->gpitch;
	
	for (int i=0; i<3; i++) {
		if (g->axes[i] <= ABS_MAX) {
			double v = (double)pyr[i] * g->sensitivity[i] * -10.0;
			m->set_axis(m, g->axes[i], clamp(STICK_PAD_MIN, v, STICK_PAD_MAX));
		}
	}
}

static Parameter* get_property(Action* a, const char* name) {
	GyroAction* g = container_of(a, GyroAction, action);
	// MAKE_DVEC_PROPERTY(b->sensitivity, "sensitivity");
	// MAKE_INT_PROPERTY(b->axis, "axis");
	MAKE_HAPTIC_PROPERTY(g->hdata, "haptic");
	
	DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


static ActionOE gyro_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_param_checker_fill_defaults(&pc, params);
	if (params == NULL) return (ActionOE)scc_oom_action_error();
	
	GyroAction* g = malloc(sizeof(GyroAction));
	if (g == NULL) return (ActionOE)scc_oom_action_error();
	
	if (strcmp(keyword, KW_GYRO) == 0) {
		scc_action_init(&g->action, KW_GYRO,
						AF_ACTION | AF_MOD_SENSITIVITY | AF_MOD_SENS_Z,
						&gyro_dealloc, &gyro_to_string);
		g->action.gyro = &gyro;
	} else {
		scc_action_init(&g->action, KW_GYROABS,
						AF_MOD_DEADZONE | AF_ACTION | AF_MOD_SENSITIVITY | AF_MOD_SENS_Z,
						&gyro_dealloc, &gyro_to_string);
		g->action.gyro = &gyro;
	}
	
	g->action.describe = &describe;
	g->action.extended.set_sensitivity = &set_sensitivity;
	g->action.get_property = &get_property;
	g->action.extended.set_haptic = &set_haptic;
	
	g->axes[0] = scc_parameter_as_int(params->items[0]);
	g->axes[1] = scc_parameter_as_int(params->items[1]);
	g->axes[2] = scc_parameter_as_int(params->items[2]);
	g->sensitivity[0] = g->sensitivity[1] = g->sensitivity[2] = 1.0;
	HAPTIC_DISABLE(&g->hdata);
	g->params = params;
	
	return (ActionOE)&g->action;
}

void scc_actions_init_gyro() {
	scc_param_checker_init(&pc, "xx+?x+?");
	scc_param_checker_set_defaults(&pc, ABS_CNT, ABS_CNT);
	scc_action_register(KW_GYRO, &gyro_constructor);
	scc_action_register(KW_GYROABS, &gyro_constructor);
}

