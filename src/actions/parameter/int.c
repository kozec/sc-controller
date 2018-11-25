#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include "scc/error.h"
#include <stdlib.h>

typedef struct {
	Parameter				parameter;
	int64_t					value;
	bool					is_hex;
	char*					name;
} IntParameter;


static char* int_param_to_string(Parameter* _p) {
	IntParameter* p = container_of(_p, IntParameter, parameter);
	if (p->name == NULL)
		return strbuilder_fmt("%li", p->value);
	return strbuilder_cpy(p->name);
}

static int64_t int_param_as_int(Parameter* _p) {
	IntParameter* p = container_of(_p, IntParameter, parameter);
	return p->value;
}

static float int_param_as_float(Parameter* _p) {
	IntParameter* p = container_of(_p, IntParameter, parameter);
	return p->value;
}

static void free_int_param(void* _p) {
	IntParameter* p = container_of(_p, IntParameter, parameter);
	if (p->name != NULL)
		free(p->name);
	free(p);
}


Parameter* scc_new_int_parameter(int64_t value) {
	IntParameter* p = malloc(sizeof(IntParameter));
	if (p == NULL) return NULL;
	RC_INIT(&p->parameter, &free_int_param);
	p->parameter.type = PT_INT;
	p->value = value;
	p->is_hex = false;
	p->name = NULL;
	
	p->parameter.as_action = &scc_param_as_action_invalid;
	p->parameter.as_string = &scc_param_as_string_invalid;
	p->parameter.as_int = &int_param_as_int;
	p->parameter.as_float = &int_param_as_float;
	p->parameter.to_string = &int_param_to_string;
	return &p->parameter;
}


Parameter* scc_new_const_int_parameter(const char* name, int64_t value) {
	char* name_copy = strbuilder_cpy(name);
	if (name_copy == NULL) return NULL;
	Parameter* p = scc_new_int_parameter(value);
	if (p == NULL) return NULL;
	IntParameter* ip = container_of(p, IntParameter, parameter);
	ip->name = name_copy;
	return p;
}
