/*
 * SC-Controller - props.h
 *
 * Macros used in get_property methods
 */
#pragma once

/** Macro for returning 'x' as float-type property */
#define MAKE_FLOAT_PROPERTY(accessor, prop_name) do {		\
	if (0 == strcmp(name, prop_name))						\
		return scc_new_float_parameter(accessor);			\
	} while (0);

/** Macro for returning 'x' as integer-type property */
#define MAKE_INT_PROPERTY(accessor, prop_name) do {			\
	if (0 == strcmp(name, prop_name))						\
		return scc_new_int_parameter(accessor);				\
	} while (0);

/** Macro for returning 'x' as string property */
#define MAKE_STRING_PROPERTY(accessor, prop_name) do {		\
	if (0 == strcmp(name, prop_name))						\
		return scc_new_string_parameter(accessor);			\
	} while (0);

/** Macro for returning 'x' as action property */
#define MAKE_ACTION_PROPERTY(accessor, prop_name) do {		\
	if (0 == strcmp(name, prop_name))						\
		return scc_new_action_parameter(accessor);			\
	} while (0);

/** Macro for returning dvec_t property */
#define MAKE_DVEC_PROPERTY(accessor, prop_name) do {		\
	if (0 == strcmp(name, prop_name)) {						\
		Parameter* xy[] = {									\
			scc_new_float_parameter((accessor).x),			\
			scc_new_float_parameter((accessor).y)			\
		};													\
		if ((xy[0] == NULL) || (xy[1] == NULL)) {			\
			free(xy[0]); free(xy[1]);						\
			return NULL;									\
		}													\
		return scc_new_tuple_parameter(2, xy);				\
	}														\
} while (0);

/** Macro for returning HapticData-type property */
#define MAKE_HAPTIC_PROPERTY(accessor, prop_name) do {		\
	if (0 == strcmp(name, prop_name)) {						\
		const char* side = NULL;							\
		switch ((accessor).pos) {							\
			case HAPTIC_RIGHT: side = "RIGHT"; break;		\
			case HAPTIC_LEFT: side = "LEFT"; break;			\
			case HAPTIC_BOTH: side = "BOTH"; break;			\
		}													\
		Parameter* h[] = {									\
			scc_new_const_string_parameter(side),			\
			scc_new_int_parameter((accessor).amplitude),	\
			scc_new_float_parameter((accessor).frequency),	\
			scc_new_int_parameter((accessor).period),		\
		};													\
		if ((h[0] == NULL) || (h[1] == NULL)				\
			|| (h[2] == NULL) || (h[3] == NULL)) {			\
			free(h[0]); free(h[1]); free(h[2]); free(h[3]);	\
			return NULL;									\
		}													\
		return scc_new_tuple_parameter(4, h);				\
	}														\
} while (0);


/** Macro for returning actual Parameter as property */
#define MAKE_PARAM_PROPERTY(accessor, prop_name) do {		\
	if (0 == strcmp(name, prop_name)) {						\
		Parameter* p = accessor;							\
		RC_ADD(p);											\
		return p;											\
	}														\
} while (0);

