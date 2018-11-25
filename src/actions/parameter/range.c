#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include "scc/error.h"
#include <stdlib.h>

typedef struct {
	Parameter				parameter;
	Parameter*				a;
	RangeType				type;
	float					b;
} Range;


static char* range_to_string(Parameter* p) {
	return strbuilder_fmt("<range>");
}


Parameter* scc_new_range_parameter(Parameter* a, RangeType type, float b) {
	Range* p = malloc(sizeof(Range));
	if (p == NULL) return NULL;
	RC_INIT(&p->parameter, &free);
	p->parameter.type = PT_RANGE;
	
	p->parameter.as_action = &scc_param_as_action_invalid;
	p->parameter.as_string = &scc_param_as_string_invalid;
	p->parameter.as_int = &scc_param_as_int_invalid;
	p->parameter.as_float = &scc_param_as_float_invalid;
	p->parameter.to_string = &range_to_string;
	return &p->parameter;
}