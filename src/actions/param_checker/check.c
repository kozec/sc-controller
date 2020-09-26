#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/param_checker.h"
#include "scc/error.h"
#include "scc/tools.h"
#include "param_checker.h"
#include <stdbool.h>
#include <stdlib.h>
#include <stdint.h>


ParamError* invalid_number_of_parameters(const char* keyword) {
	return scc_new_param_error(AEC_INVALID_NUMBER_OF_PARAMETERS,
							"Invalid number of parameters for '%s'", keyword);
}


// Returns true if parameter matches paramData type and allowed range.
bool is_ok_for(Parameter* param, ParamData* data) {
	if ((param->type & data->type) == 0)
		return false;
	
	if (data->type == PT_INT) {
		int64_t value = param->as_int(param);
		if ((value < data->min) || (value > data->max))
			return false;
	} else if (data->type == PT_FLOAT) {
		float value = param->as_float(param);
		if ((value < data->fmin) || (value > data->fmax))
			return false;
	} else if (data->type == PT_STRING) {
		if (data->check_value != NULL)
			return data->check_value(param->as_string(param));
	}
	return true;
}


bool check_button_name(const char* value) {
	return scc_string_to_button(value) != 0;
}

bool check_axis_name(const char* value) {
	return scc_string_to_pst(value) != 0;
}

static bool check_plus(const char* value) {
	return (0 == strcmp(value, "DEFAULT"))
			|| (0 == strcmp(value, "ALWAYS"))
			|| (0 == strcmp(value, "SAME"));
}

bool check_button_name_plus(const char* value) {
	return check_plus(value) || check_button_name(value);
}

bool check_axis_name_plus(const char* value) {
	return check_plus(value) || check_axis_name(value);
}


static ParamError* check(ParamChecker* pc, size_t index, const char* keyword, ParameterList params) {
	size_t p = 0;
	size_t d = 0;
	do {
		if (d >= pc->length) {
			// Got all expected parameters
			if (p < list_len(params))
				// ... but there is something left
				return invalid_number_of_parameters(keyword);
			return NULL;
		}
		if (p >= list_len(params)) {
			// Ran out of parameters
			if (pc->data[d]->optional) {
				// ... but currently expected is optional
				index ++;
				d ++;
				continue;
			}
			return invalid_number_of_parameters(keyword);
		}
		
		ParamError* err = NULL;
		if ((params->items[p]->type & pc->data[d]->type) == 0) {
			// Wrong type
			err = scc_new_invalid_parameter_type_error(keyword, index, params->items[p]);
		} else {
			if (!is_ok_for(params->items[p], pc->data[d])) {
				// This should fail only if float or int is out of range, or
				// if string parameter is not one of expected vaues
				if (pc->data[d]->type == PT_STRING)
					return scc_new_invalid_parameter_value_error(keyword, index, params->items[p]);
				else
					return scc_new_parameter_out_of_range_error(keyword, index, params->items[p]);
			}
		}
		// TODO: Move this up, into 'wrong type' check
		if ((err != NULL) && (!pc->data[d]->optional)) {
			// Wrong parameter type and currently expected is _not_ optional
			return err;
		} else if (err != NULL) {
			// Wrong parameter type, but currently expected may be skipped
			// Check if parameter matches anything after
			bool can_skip = false;
			for (size_t next = d; (next < pc->length) && !can_skip; next++) {
				can_skip = is_ok_for(params->items[p], pc->data[next]);
				if (!pc->data[next]->optional) break;
			}
			if (!can_skip) return err;
			RC_REL(err);
		} else {
			// Everything matches. If this is repeating parameter, take as much
			// as possible
			if (pc->data[d]->repeating) {
				for (; (p + 1 < list_len(params)) && is_ok_for(params->items[p + 1], pc->data[d]); )
					p ++;
			}
			index ++;
			p ++;
		}
		d ++;
	} while (1);	// Returns from inside of loop.
}


ParamError* scc_param_checker_check(ParamChecker* pc, const char* keyword, ParameterList params) {
	return check(pc, 0, keyword, params);
}
