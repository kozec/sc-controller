#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include "scc/action.h"

static char* none_to_string(Parameter* p) {
	return strbuilder_cpy("None");
}

static Action* none_to_action(Parameter* _p) {
	Action* a = NoAction;
	RC_ADD(a);
	return a;
}


Parameter _None = {
	PT_NONE, {0xFFFF, NULL},
	&none_to_string,
	&none_to_action,
	&scc_param_as_string_invalid,
	&scc_param_as_int_invalid,
	&scc_param_as_float_invalid,
};

void scc_initialize_none() {
	None = &_None;
}
