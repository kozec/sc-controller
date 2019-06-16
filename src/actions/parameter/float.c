#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include "scc/error.h"
#include <stdlib.h>
#include <locale.h>

typedef struct {
	Parameter				parameter;
	float					value;
	const char*				constant;
} FloatParameter;


static char* float_param_to_string(Parameter* _p) {
	FloatParameter* p = container_of(_p, FloatParameter, parameter);
	return strbuilder_fmt("%g", p->value);
}

static int64_t float_param_to_int(Parameter* _p) {
	FloatParameter* p = container_of(_p, FloatParameter, parameter);
	return p->value;
}

static float float_param_to_float(Parameter* _p) {
	FloatParameter* p = container_of(_p, FloatParameter, parameter);
	return p->value;
}

static void free_float_param(void* _p) {
	FloatParameter* p = container_of(_p, FloatParameter, parameter);
	free(p);
}


Parameter* scc_new_float_parameter(float value) {
	FloatParameter* p = malloc(sizeof(FloatParameter));
	if (p == NULL) return NULL;
	RC_INIT(&p->parameter, &free_float_param);
	p->parameter.type = PT_FLOAT;
	p->value = value;
	p->constant = NULL;
	
	p->parameter.as_action = &scc_param_as_action_invalid;
	p->parameter.as_string = &scc_param_as_string_invalid;
	p->parameter.as_int = &float_param_to_int;
	p->parameter.as_float = &float_param_to_float;
	p->parameter.to_string = &float_param_to_string;
	return &p->parameter;
}
