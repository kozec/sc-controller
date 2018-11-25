/**
 * Defines callbacks used by all parameter types when nonsensical conversion
 * (ie converting int to Action) is requested to requested.
 */
#include "scc/utils/logging.h"
#include "scc/parameter.h"

struct Action* scc_param_as_action_invalid(Parameter* p) {
	FATAL("Cannot use parameter '%s' as action", scc_parameter_to_string(p));
}

char* scc_param_as_string_invalid(Parameter* p) {
	FATAL("Cannot use parameter '%s' as string", scc_parameter_to_string(p));
}

int64_t scc_param_as_int_invalid(Parameter* p) {
	FATAL("Cannot use parameter '%s' as int", scc_parameter_to_string(p));
}

float scc_param_as_float_invalid(Parameter* p) {
	FATAL("Cannot use parameter '%s' as float", scc_parameter_to_string(p));
}
