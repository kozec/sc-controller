/*
 * SC-Controller - props.h
 *
 * Macros used in get_property methods
 */
#pragma once

/** Macro for returning 'x' as float-type property */
#define MAKE_FLOAT_PROPERTY(accessor, prop_name) do {	\
	if (0 == strcmp(name, prop_name))					\
		return scc_new_float_parameter(accessor);		\
	} while (0);

/** Macro for returning 'x' as integer-type property */
#define MAKE_INT_PROPERTY(accessor, prop_name) do {		\
	if (0 == strcmp(name, prop_name))					\
		return scc_new_int_parameter(accessor);			\
	} while (0);

/** Macro for returning dvec_t property */
#define MAKE_DVEC_PROPERTY(accessor, prop_name) do {	\
	if (0 == strcmp(name, prop_name)) {					\
		Parameter* xy[] = {								\
			scc_new_float_parameter((accessor).x),		\
			scc_new_float_parameter((accessor).y)		\
		};												\
		if ((xy[0] == NULL) || (xy[1] == NULL)) {		\
			free(xy[0]); free(xy[1]);					\
			return NULL;								\
		}												\
		return scc_new_tuple_parameter(2, xy);			\
	}													\
} while (0);

