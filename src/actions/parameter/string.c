#include "scc/utils/strbuilder.h"
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include "scc/error.h"
#include <stdlib.h>

typedef struct {
	Parameter				parameter;
	char*					value;
	const char*				name;
} StringParameter;

static char* str_param_to_string(Parameter* _p) {
	StringParameter* p = container_of(_p, StringParameter, parameter);
	if (p->name == NULL) {
		StrBuilder* b = strbuilder_new();
		if (b == NULL) return NULL;
		strbuilder_add(b, p->value);
		strbuilder_escape(b, "\n\t\r\\'", '\\');
		strbuilder_add_char(b, '\'');
		strbuilder_insert_char(b, 0, '\'');
		if (strbuilder_failed(b)) {
			strbuilder_free(b);
			return NULL;
		}
		
		return strbuilder_consume(b);
	}
	return strbuilder_cpy(p->name);
}

static char* str_param_as_string(Parameter* _p) {
	StringParameter* p = container_of(_p, StringParameter, parameter);
	return p->value;
}

static void str_param_dealloc_normal(void* _p) {
	StringParameter* p = container_of(_p, StringParameter, parameter);
	free(p->value);
	free(p);
}

static void str_param_dealloc_non_owned(void* _p) {
	StringParameter* p = container_of(_p, StringParameter, parameter);
	free(p);
}


static Parameter* new_string(char* value, bool owned) {
	if (value == NULL) return NULL;
	StringParameter* p = malloc(sizeof(StringParameter));
	if (p == NULL) return NULL;
	RC_INIT(&p->parameter, owned ? (&str_param_dealloc_normal) : (&str_param_dealloc_non_owned));
	p->parameter.type = PT_STRING;
	p->value = value;
	p->name = NULL;
	
	p->parameter.as_action = &scc_param_as_action_invalid;
	p->parameter.as_string = &str_param_as_string;
	p->parameter.as_int = &scc_param_as_int_invalid;
	p->parameter.as_float = &scc_param_as_float_invalid;
	p->parameter.to_string = &str_param_to_string;
	return &p->parameter;
}

Parameter* scc_new_string_parameter(const char* value) {
	return new_string(strbuilder_cpy(value), true);
}

Parameter* scc_string_to_parameter(char* value) {
	return new_string(value, true);
}

Parameter* scc_new_const_string_parameter(const char* name) {
	if (name == NULL) return NULL;
	Parameter* rv = new_string((char*)name, false);
	if (rv) {
		StringParameter* p = container_of(rv, StringParameter, parameter);
		p->name = name;
	}
	return rv;
}

Parameter* scc_new_const_string(const char* value) {
	if (value == NULL) return NULL;
	return new_string((char*)value, false);
}

