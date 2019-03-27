#include "scc/utils/assert.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/parameter.h"
#include "scc/action.h"
#include "param_checker.h"
#include <stdarg.h>
#include <stdbool.h>

void scc_actions_init_noaction();

static Parameter* no_action_parameter = NULL;

void scc_param_checker_set_defaults(ParamChecker* pc, ...) {
	ParameterList params = list_new(Parameter, 0);
	ASSERT(params != NULL);
	va_list ap;
	
	va_start(ap, pc);
	for (int i=0; i<pc->length; i++) {
		ParamData* data = pc->data[i];
		if (!data->optional || data->repeating)
			continue;
		
		Parameter *p = NULL;
		if (data->type == PT_INT) {
			int value = va_arg(ap, int);
			ASSERT((value == 0) || ((value >= data->min) && (value <= data->max)));
			//      ^^ special exception for 'c' on button, where default value is zero.
			p = scc_new_int_parameter(value);
		} else if (data->type == PT_FLOAT) {
			float value = va_arg(ap, double);
			ASSERT((value >= data->fmin) && (value <= data->fmax));
			p = scc_new_float_parameter(value);
		} else if (data->type == PT_ACTION) {
			Action* value = va_arg(ap, Action*);
			if (value == NULL) {
				if (no_action_parameter == NULL) {
					// NULL supplies NoAction. This ensures that NoAction is initialized
					scc_actions_init_noaction();
					no_action_parameter = scc_new_action_parameter(NoAction);
					ASSERT(no_action_parameter != NULL);
				}
				p = no_action_parameter;
			} else {
				RC_INIT(value, NULL);				// prevents deallocation
				p = scc_new_action_parameter(value);
			}
		} else if (data->type == PT_STRING) {
			const char* value = va_arg(ap, const char*);
			ASSERT(value);
			p = scc_new_const_string(value);
		}
		ASSERT(p);
		RC_INIT(p, NULL);							// prevents deallocation
		list_add(params, p);
	}
	va_end(ap);
	
	pc->defaults_count = list_len(params);
	pc->defaults = (Parameter**)list_consume(params);
}

ParameterList scc_param_checker_fill_defaults(ParamChecker* pc, ParameterList src) {
	ParameterList params = scc_make_param_list(NULL);
	if (params == NULL) return NULL;
	
	int s = 0;
	int e = 0;
	for (int d = 0; d<pc->length; d++) {
		if (pc->data[d]->repeating) {
			while (s < list_len(src)) {
				if (!is_ok_for(src->items[s], pc->data[d]))
					break;
				if (!list_add(params, src->items[s]))
					goto scc_param_checker_fill_defaults_fail;
				RC_ADD(src->items[s]);
				s ++;
			}
		} else if (pc->data[d]->optional) {
			bool filled_by_user = (s < list_len(src)) && is_ok_for(src->items[s], pc->data[d]);
			if (filled_by_user) {
				if (!list_add(params, src->items[s]))
					goto scc_param_checker_fill_defaults_fail;
				RC_ADD(src->items[s]);
				s ++;
			} else {
				Parameter* pp = pc->defaults[e];
				if (!list_add(params, pp))
					goto scc_param_checker_fill_defaults_fail;
			}
			e ++;
		} else {
			ASSERT(s < list_len(src));
			if (!list_add(params, src->items[s]))
				goto scc_param_checker_fill_defaults_fail;
			RC_ADD(src->items[s]);
			s ++;
		}
	}
	
	return params;
scc_param_checker_fill_defaults_fail:
	// Code jumps here to deallocate created list if memory allocation fails
	list_free(params);
	return NULL;
}

static bool equals(Parameter* p1, Parameter* p2) {
	switch (scc_parameter_type(p1)) {
		case PT_ACTION:
			if (scc_parameter_type(p2) == PT_ACTION) {
				Action* a1 = scc_parameter_as_action(p1);
				Action* a2 = scc_parameter_as_action(p2);
				return (a1 == a2);
			}
			return false;
		case PT_RANGE:
			return false;
		case PT_NONE:
			return (scc_parameter_type(p2) == PT_NONE);
		case PT_INT:
			return (scc_parameter_type(p2) & PT_INT) && \
				scc_parameter_as_int(p1) == scc_parameter_as_int(p2);
		case PT_FLOAT:
			return (scc_parameter_type(p2) & PT_FLOAT) && \
				scc_parameter_as_float(p1) == scc_parameter_as_float(p2);
		case PT_STRING:
			return (scc_parameter_type(p2) & PT_STRING) && \
				(0 == strcmp(scc_parameter_as_string(p1), scc_parameter_as_string(p2)));
		default:
			return false;
	}
}

bool no_nulls(void* x, void* userdata) {
	return x != NULL;
}

/**
 * Optional parameter can be stripped only if following parameter doesn't have
 * compatible type or can be string as well
 */
static bool can_be_stripped(ParamChecker* pc, ParameterList params, int s, int e, int d) {
	if (s >= list_len(params) - 1)
		// Last parameter
		return true;
	if ((params->items[s]->type & params->items[s+1]->type) == 0)
		// Following is not of compatible type
		return true;
	if ((d<pc->length-1) && (pc->data[d+1]->optional))
		// Following may be stripped as well
		if (equals(pc->defaults[e+1], params->items[s+1]))
			return can_be_stripped(pc, params, s+1, e+1, d+1);
	return false;
}

ParameterList scc_param_checker_strip_defaults(ParamChecker* pc, ParameterList params) {
	if (params == NULL) return NULL;
	
	int s = 0;
	int e = 0;
	for (int d = 0; d<pc->length; d++) {
		if (pc->data[d]->repeating) {
			while (s < list_len(params)) {
				if (!is_ok_for(params->items[s], pc->data[d]))
					break;
				s ++;
			}
		} else if (pc->data[d]->optional) {
			if (equals(pc->defaults[e], params->items[s])) {
				if (can_be_stripped(pc, params, s, e, d)) {
					RC_REL(params->items[s]);
					params->items[s] = NULL;
				}
			}
			e ++;
			s ++;
		} else {
			s ++;
		}
	}
	
	list_filter(params, &no_nulls, NULL);
	return params;
}

