/*
 * SC-Controller - CemuHook
 *
 * Pushes gyrosensor data to emulator (or game) with CemuHook protocol support.
 *
 * UDP server needed to do this is maintained by daemon.
  */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/special_action.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/action.h"
#include "props.h"

static const char* KW_CEMUHOOK = "cemuhook";
#define MAGIC_ACCEL	(2.0 / 32768.0)
#define MAGIC_GYRO	(2000.0 / 32768.0)

typedef struct {
	Action				action;
	double				sensitivity[3];
} CemuHookAction;

char* cemuhook_to_string(Action* a) {
	return strbuilder_cpy(KW_CEMUHOOK);
}

static char* describe(Action* a, ActionDescContext ctx) {
	return strbuilder_cpy("CemuHook");
}

static void cemuhook_dealloc(Action* a) {
	CemuHookAction* c = container_of(a, CemuHookAction, action);
	free(c);
}

static void gyro(Action* a, Mapper* m, const struct GyroInput* value) {
	float sa_data[6];
	
	// if ((m->get_flags(m) & CF_EUREL_GYROS) != 0) {
	// TODO: Check DS4 support here
	sa_data[0] = -(float)(value->accel_x * MAGIC_ACCEL);
	sa_data[1] = -(float)(value->accel_z * MAGIC_ACCEL - 1.0);
	sa_data[2] = (float)(value->accel_y * MAGIC_ACCEL);
	sa_data[3] = (float)(value->gpitch * MAGIC_GYRO);
	sa_data[4] = -(float)(value->gyaw * MAGIC_GYRO);
	sa_data[5] = -(float)(value->groll * MAGIC_GYRO);
	
	if ((m->special_action == NULL) || !m->special_action(m, SAT_CEMUHOOK, sa_data))
		DWARN("Mapper lacks support for 'cemuhook'");
}


static Parameter* get_property(Action* a, const char* name) {
	CemuHookAction* c = container_of(a, CemuHookAction, action);
	if (0 == strcmp(name, "sensitivity")) {
		Parameter* xyz[] = {
			scc_new_float_parameter(c->sensitivity[0]),
			scc_new_float_parameter(c->sensitivity[1]),
			scc_new_float_parameter(c->sensitivity[2])
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
	CemuHookAction* c = container_of(a, CemuHookAction, action);
	c->sensitivity[0] = x;
	c->sensitivity[1] = y;
	c->sensitivity[2] = z;
}


static ActionOE cemuhook_constructor(const char* keyword, ParameterList params) {
	if (list_len(params) != 0) {
		return (ActionOE)scc_new_param_error(AEC_INVALID_NUMBER_OF_PARAMETERS,
							"Invalid number of parameters for '%s'", keyword);
	}
	
	CemuHookAction* c = malloc(sizeof(CemuHookAction));
	if (c == NULL) return (ActionOE)scc_oom_action_error();
	
	scc_action_init(&c->action, KW_CEMUHOOK,
					AF_ACTION | AF_MOD_SENSITIVITY | AF_MOD_SENS_Z,
					&cemuhook_dealloc, &cemuhook_to_string);
	
	c->action.gyro = &gyro;
	c->action.describe = &describe;
	c->action.get_property = &get_property;
	c->action.extended.set_sensitivity = &set_sensitivity;
	
	c->sensitivity[0] = c->sensitivity[1] = c->sensitivity[2] = 1.0;
	
	return (ActionOE)&c->action;
}

void scc_actions_init_cemuhook() {
	scc_action_register(KW_CEMUHOOK, &cemuhook_constructor);
}

