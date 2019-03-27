/*
 * Blah blah
 * For various reasons, errors are returned as special type of Action.
 */
#include "scc/parameter.h"
#include "scc/error.h"
#include <stdlib.h>
#include <stdarg.h>
#include <stdio.h>

static void error_dealloc(void* e);

static ActionError _oom_error = {
	SCC_ERROR, {0xFFFF, NULL}, AEC_OUT_OF_MEMORY,
	"Out of memory"
};

ActionError* scc_oom_action_error() {
	return &_oom_error;
}


static void error_dealloc(void* e) {
	free(e);
}


static char* th(unsigned int n) {
	char* str = malloc(255);
	if (n == 0) { sprintf(str, "1st"); }
	else if (n == 1) { sprintf(str, "2nd"); }
	else if (n == 2) { sprintf(str, "3rd"); }
	else {
		snprintf(str, 254, "%uth", n + 1);
	}
	return str;
}


ActionError* scc_new_action_error(ActionErrorCode code, const char* fmt, ...) {
	va_list args;
	ActionError* e = malloc(sizeof(ActionError));
	if (e == NULL)
		return scc_oom_action_error();
	
	RC_INIT(e, &error_dealloc);
	e->flag = SCC_ERROR;
	e->code = code;
	va_start(args, fmt);
	vsnprintf(&e->message[0], SCC_MAX_ERROR_MSG_LEN - 1, fmt, args);
	va_end(args);
	return e;
}


ParamError* scc_new_invalid_parameter_type_error(const char* keyword, unsigned int n, Parameter* p) {
	char* _p = scc_parameter_to_string(p);
	char* _th = th(n);
	ParamError* e;
	if ((_th == NULL) || (_p == NULL)) {
		e = scc_oom_action_error();
	} else {
		e = scc_new_param_error(AEC_INVALID_PARAMETER_TYPE,
			"'%s' cannot take %s as %s parameter", keyword, _p, _th);
	}
	free(_th);
	free(_p);
	return e;
}


ParamError* scc_new_parameter_out_of_range_error(const char* keyword, unsigned int n, Parameter* p) {
	char* _p = scc_parameter_to_string(p);
	char* _th = th(n);
	ParamError* e;
	if ((_th == NULL) || (_p == NULL)) {
		e = scc_oom_action_error();
	} else {
		e = scc_new_param_error(AEC_PARAMETER_OUT_OF_RANGE,
			"%s is out of range for %s parameter of '%s'", _p, _th, keyword);
	}
	free(_th);
	free(_p);
	return e;	
}


ParamError* scc_new_invalid_parameter_value_error(const char* keyword, unsigned int n, Parameter* p) {
	char* _p = scc_parameter_to_string(p);
	char* _th = th(n);
	ParamError* e;
	if ((_th == NULL) || (_p == NULL)) {
		e = scc_oom_action_error();
	} else {
		e = scc_new_param_error(AEC_PARAMETER_OUT_OF_RANGE,
			"%s is not valid value for %s parameter of '%s'", _p, _th, keyword);
	}
	free(_th);
	free(_p);
	return e;	
}

