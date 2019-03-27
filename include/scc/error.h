#pragma once
#include "scc/utils/rc.h"

typedef enum ActionErrorCode {
	AEC_OUT_OF_MEMORY					= 0,
	AEC_PARSE_ERROR						= 1,
	AEC_INVALID_NUMBER_OF_PARAMETERS	= 2,
	AEC_INVALID_VALUE					= 3,
	AEC_INVALID_PARAMETER_TYPE			= 4,
	AEC_PARAMETER_OUT_OF_RANGE			= 5,
	AEC_UNKNOWN_KEYWORD					= 6,
} ActionErrorCode;

typedef uint32_t ErrorFlag;

#define SCC_MAX_ERROR_MSG_LEN 1024

typedef struct ActionError ActionError;

struct ActionError {
	ErrorFlag			flag;
	RC_HEADER;
	ActionErrorCode		code;
	char				message[SCC_MAX_ERROR_MSG_LEN];
};

typedef ActionError ParamError;

struct Action;
struct Parameter;

/**
 * Union returned by many functions to indicate that return value may be error.
 * Action, Parameter, ActionError and ParamError begins with same header
 * and both ParameterType and ActionFlags have value 1 reserved for error.
 * Use IS_ACTION_ERROR() to take advantage of this.
 */
typedef union ActionOE {
	struct Action*		action;
	ActionError*		error;
	struct {
		unsigned short 		flag;
		RC_HEADER;
	}* aoe;
} ActionOE;

/**
 * Same thing as ActionOE, but for Parameters.
 * Use IS_PARAM_ERROR() to make sure.
 */
typedef union ParamOE {
	struct Parameter*	parameter;
	ParamError*			error;
	struct {
		unsigned short 		flag;
		RC_HEADER;
	}* aoe;
} ParamOE;

#define SCC_ERROR 1

/** Is true if parameter represents ActionError */
#define IS_ACTION_ERROR(x) (((ActionOE)(x)).aoe->flag == SCC_ERROR)
/** Converts parameter to ActionError* or NULL, if 'x' doesn't represents error */
#define ACTION_ERROR(x) (IS_ACTION_ERROR(x) ? (((ActionOE)(x)).error) : NULL)
/** Converts parameter to Action* or NULL, if 'x' represents error */
#define ACTION(x) (IS_ACTION_ERROR(x) ? NULL : (((ActionOE)(x)).action))
/** Is true if parameter represents ParamErrorq */
#define IS_PARAM_ERROR(x) (((ParamOE)(x)).aoe->flag == SCC_ERROR)
/** Converts parameter to ParamError* or NULL, if 'x' doesn't represents error */
#define PARAM_ERROR(x) (IS_PARAM_ERROR(x) ? (((ParamOE)(x)).error) : NULL)
/** Converts parameter to Parameter* or NULL, if 'x' represents error */
#define PARAMETER(x) (IS_PARAM_ERROR(x) ? NULL : (((ParamOE)(x)).parameter))
/** Releases reference on ActionOE or ParamOE, no matter what actual value it represents */
#define OE_REL(x) RC_REL((x).aoe);

/** Returns new instance of ActionError, structure used to signalize failure to parse Action */
ActionError* scc_new_action_error(ActionErrorCode code, const char* fmt, ...);
/** Returns ActionError set to out of memory error. Such error is pre-allocated singleton */
ActionError* scc_oom_action_error();

/** Returns new instance of ParamError, structure used to signalize failure to parse Parameter */
#define scc_new_param_error(code, fmt, ...) ((ParamError*)scc_new_action_error((code), (fmt), ##__VA_ARGS__))
/** Returns new instance of ActionError, with error code set to AEC_PARSE_ERROR */
#define scc_new_parse_error(fmt, ...) ((ParamError*)scc_new_action_error(AEC_PARSE_ERROR, (fmt), ##__VA_ARGS__))

