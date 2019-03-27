#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include <stdlib.h>

typedef struct {
	Parameter				parameter;
	uint8_t					count;
	Parameter**				children;
} Tuple;


static char* tuple_to_string(Parameter* _p) {
	return "(tuple)";	// TODO: Maybe this. I don't really need it now
}

static void free_tuple(void* _p) {
	Tuple* p = container_of(_p, Tuple, parameter);
	for (uint8_t i=0; i<p->count; i++)
		RC_REL(p->children[i]);
	free(p->children);
	free(p);
}

uint8_t scc_parameter_tuple_get_count(Parameter* _p) {
	ASSERT(_p->type == PT_TUPLE);
	Tuple* p = container_of(_p, Tuple, parameter);
	return p->count;
}

Parameter* scc_parameter_tuple_get_child(Parameter* _p, uint8_t n) {
	ASSERT(_p->type == PT_TUPLE);
	Tuple* p = container_of(_p, Tuple, parameter);
	return p->children[n];
}


Parameter* scc_param_list_to_tuple(ParameterList lst) {
	Parameter* p = scc_new_tuple_parameter(list_len(lst), lst->items);
	if (p != NULL)
		// Tuple takes over references, so 'lst' should not release them.
		list_set_dealloc_cb(lst, NULL);
	list_free(lst);
	return p;
}

Parameter* scc_new_tuple_parameter(uint8_t count, Parameter* children[]) {
	Tuple* p = malloc(sizeof(Tuple));
	if (p == NULL) return NULL;
	p->count = count;
	if (count == 0) {
		p->children = NULL;
	} else {
		p->children = malloc(sizeof(Parameter*) * count);
		if (p->children == NULL) {
			free(p);
			return NULL;
		}
	}
	bool failed = false;
	for (uint8_t i=0; i<p->count; i++) {
		if (children[i] == NULL) {
			failed = true;
			p->children[i] = NULL;
		} else {
			RC_ADD(children[i]);
			p->children[i] = children[i];
		}
	}
	
	if (failed) {
		free_tuple(&p->parameter);
		return NULL;
	}
	
	RC_INIT(&p->parameter, &free_tuple);
	p->parameter.type = PT_TUPLE;
	p->parameter.as_action = &scc_param_as_action_invalid;
	p->parameter.as_string = &scc_param_as_string_invalid;
	p->parameter.as_int = &scc_param_as_int_invalid;
	p->parameter.as_float = &scc_param_as_float_invalid;
	p->parameter.to_string = &tuple_to_string;
	return &p->parameter;
}

