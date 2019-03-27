#pragma once
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/error.h"
#include <stdint.h>

typedef struct Action Action;

typedef enum {
	// ActionFlags and ParameterType values has to be mutually exclusive,
	// with exception of AF_ERROR / PT_ERROR
	PT_ERROR					= 0b000000001,
	PT_CONSTANT					= 0b000000010,
	PT_ACTION					= 0b000000100,
	PT_RANGE					= 0b000001000,
	// PTNone mask intantionally covers Action
	PT_NONE						= 0b000010100,

	PT_INT						= 0b000100000,
	// PTFLOAT mask intantionally covers Integer
	PT_FLOAT					= 0b001100000,
	PT_STRING					= 0b010000000,
	PT_TUPLE					= 0b100000000,
	// PT_ANY  _has_ to cover all but error
	PT_ANY						= 0b111111110,
	ParameterType_pad_			= 0xFFFFFFFF
} ParameterType;

typedef enum {
	RT_GREATER					= 1,
	RT_LESS						= 2,
	RT_GREATER_OREQUAL 			= 3,
	RT_LESS_OREQUAL				= 4
} RangeType;

typedef struct Parameter Parameter;

// Action, Parameter, ActionError and ParamError begins with same header
// and both ParameterType and ActionFlags have value 1 reserved for error.
//
// This is done this way so type of returned pointer can be determined simply
// by casting it to (uint16_t*) and comparing to 1.
// Only error vs Parameter and error vs Action is interesting check,
// there should be no way to return Action where Parameter is expected.

struct Parameter {
	ParameterType			type;
	RC_HEADER;
	
	/**
	 * Parameter->to_string returns string that can be parsed back to
	 * same parameter. This is not straightforward as some value.ToString()
	 * or it is same thing as Parameter->as_string. For example, for Int
	 * parameter created by parsing one of predefined constants, to_string
	 * should return readable name of that constant, not its value.
	 *
	 * Returned string has to be free'd by caller. Returns NULL on OOM error.
	 */
	char*(*to_string)(Parameter* p);
	/**
	 * Returns action assotiated with parameter. Calling this on non-action
	 * parameter is undefined behaviour and will result in crash.
	 *
	 * Returned Action will have reference counter increased and has to be
	 * dereferenced by caller.
	 */
	Action*(*as_action)(Parameter* p);
	/**
	 * Returns string value of parameter, exactly as it is stored. Using this
	 * on parameter that's not string nor number is undefined behaviour and
	 * will result in crash.
	 *
	 * Returned string is valid has to be valid as long as parameter exists
	 * and caller shall not free it.
	 */
	char*(*as_string)(Parameter* p);
	/**
	 * Returns integer value of parameter. Calling this on non-numeric parameter
	 * is undefined behaviour and will result in crash.
	 */
	int64_t(*as_int)(Parameter* p);
	/**
	 * Returns float value of parameter. Calling this on non-numeric parameter
	 * is undefined behaviour and will result in crash.
	 */
	float(*as_float)(Parameter* p);
};

Parameter* None;

typedef LIST_TYPE(Parameter) ParameterList;

/**
 * Returns new Integer Parameter. Returned value has to be dereferenced manually.
 * May return NULL if memory cannot be allocated.
 */
Parameter* scc_new_int_parameter(int64_t value);
/**
 * Returns new Constant Integer Parameter. Constant Parameter is exactly same
 * as normal Parameter, except it converts back to constant name when converted
 * to string.
 */
Parameter* scc_new_const_int_parameter(const char* name, int64_t value);
/**
 * Returns new Constant String Parameter.
 * String is not copied and should not be deallocated.
 */
Parameter* scc_new_const_string_parameter(const char* name);
/**
 * Returns new Float Parameter. Returned value has to be dereferenced manually.
 * May return NULL if memory cannot be allocated.
 */
Parameter* scc_new_float_parameter(float value);
/**
 * Returns new String Parameter. Returned value has to be dereferenced manually.
 * May return NULL if memory cannot be allocated.
 */
Parameter* scc_new_string_parameter(const char* value);
/**
 * Returns string Parameter that takes 'ownership' of passed string.
 * String will be deallocated automatically.
 * May return NULL if memory cannot be allocated.
 */
Parameter* scc_string_to_parameter(char* value);
/**
 * Returns string Parameter with given value.
 * String will not (and should not) be deallocated
 * May return NULL if memory cannot be allocated.
 */
Parameter* scc_new_const_string(const char* value);
/**
 * Returns new Parameter. Returned value has to be dereferenced manually.
 * May return NULL if memory cannot be allocated.
 */
Parameter* scc_new_action_parameter(Action* a);
/**
 * Returns new Parameter. Returned value has to be dereferenced manually.
 * May return NULL if memory cannot be allocated.
 */
Parameter* scc_new_range_parameter(Parameter* a, RangeType type, float b);
/**
 * Returns new Parameter. Returned value has to be dereferenced manually.
 * Steals references to child parameters.
 * May return NULL if memory cannot be allocated or if any or child parameters
 * is NULL. References to child parameters are stolen even if NULL is returned.
 */
Parameter* scc_new_tuple_parameter(uint8_t count, Parameter* children[]);
/**
 * _Destructivelly_ converts ParameterList into tuple parameter.
 *
 * Returns NULL if allocation fails.
 * Whether this call suceeds or not, ParameterList is deallocated and cannot be used after.
 */
Parameter* scc_param_list_to_tuple(ParameterList lst);
/**
 * Creates param list out of varargs.
 * Reference counter on added parameters is properly increased and decreased
 * when ParameterList is deallocated.
 * Returns NULL (and releases/deallocates everything) if allocation fails
 */
#define scc_make_param_list(...) _scc_make_param_list(__VA_ARGS__, NULL)
ParameterList _scc_make_param_list(Parameter* list, ...);

/**
 * Works as scc_make_param_list with small differences:
 *  - References are not added, but stolen by generated list. That means every
 *    parameter added will lose 1 reference when list is deallocated and may
 *    be deallocated as well.
 *  - If any of passed arguments is NULL, all non-null arguments are
 *    dereferenced, no list is created and NULL is returned
 *  - If list cannot be allocated, all non-null arguments are dereferenced as well.
 */
#define scc_inline_param_list(...) _scc_inline_param_list(__VA_ARGS__, (void*)-1)
ParameterList _scc_inline_param_list(Parameter* list, ...);

/**
 * Creates copy of parameter list. Reference counts on all parameters are
 * properly increased and decreased when ParameterList is deallocated.
 *
 * Returns NULL if allocation fails.
 */
ParameterList scc_copy_param_list(ParameterList lst);

/**
 * Converts list of parameters to string that can be then parsed back to same
 * list of parameters.
 *
 * Returned string has to be deallocated by caller.
 * Returns NULL if lst is NULL or if allocation fails.
 */
char* scc_param_list_to_string(ParameterList lst);

/**
 * Returns string representation of parameter, one that can be parsed back to same parameter using parser.
 * Returned string has to be freed by caller.
 */
char* scc_parameter_to_string(Parameter* p);

/**
 * Returns parameter type (value from ParameterType enum). Use this to check
 * type before calling any of scc_parameter_as_* methods.
 */
#define scc_parameter_type(p) ((p)->type)
/**
 * For action-type parameter, returns Action stored in parameter,
 * without increasing reference counter on returned Action. If caller needs to
 * store returned Action for use after Parameter is de-referenced, it has to
 * add new reference to Action.
 *
 * For non-action-type parameters, this crashes.
 */
#define scc_parameter_as_action(p) ((p)->as_action(p))
/**
 * Returns string value of parameter. Returned string is valid only as long as
 * parameter exists and caller shall not free it.
 */
#define scc_parameter_as_string(p) ((p)->as_string(p))
/** Returns float value of parameter. Works only with float and int, crashes with others */
#define scc_parameter_as_int(p) ((p)->as_int(p))
/** Returns float value of parameter. Works only with float and int, crashes with others */
#define scc_parameter_as_float(p) ((p)->as_float(p))

/** Returns number of children in tuple */
uint8_t scc_parameter_tuple_get_count(Parameter* p);
/** Returns n-th child from tuple. Caller should not dereference returned value */
Parameter* scc_parameter_tuple_get_child(Parameter* p, uint8_t n);

/** Returns formatted "<keyword> cannot take <parameter> as <n>th parameter" error */
ParamError* scc_new_invalid_parameter_type_error(const char* keyword, unsigned int n, Parameter* param);
/** Returns formatted "<parameter> is out of range for <n>th parameter of <keyword>" error */
ParamError* scc_new_parameter_out_of_range_error(const char* keyword, unsigned int n, Parameter* param);
/** Returns formatted "<parameter> is not valid value <n>th parameter of <keyword>" error */
ParamError* scc_new_invalid_parameter_value_error(const char* keyword, unsigned int n, Parameter* param);

/** Default callback used when nonsensical conversion is requested. Calling this intentionally crashes! */
Action* scc_param_as_action_invalid(Parameter* p);
/** Default callback used when nonsensical conversion is requested. Calling this intentionally crashes! */
char* scc_param_as_string_invalid(Parameter* p);
/** Default callback used when nonsensical conversion is requested. Calling this intentionally crashes! */
int64_t scc_param_as_int_invalid(Parameter* p);
/** Default callback used when nonsensical conversion is requested. Calling this intentionally crashes! */
float scc_param_as_float_invalid(Parameter* p);

