/*
 * SC-Controller - Actions - ACTION_MAKE_TO_STRING macro.
 *
 * Generates default 'to_string' method. This will work with any action
 * class that stores parameters in 'params' field.
 * If 'pc' (ParamChecker) is not NULL, defaults are stripped.
 */
#pragma once
#include "scc/utils/strbuilder.h"

#define ACTION_MAKE_TO_STRING(ActionType, prefix, keyword, pc)				\
	static char* prefix ## _to_string(Action* _a) {							\
		ActionType* a = container_of(_a, ActionType, action);				\
		char* parmsstr;														\
		if ((pc) == NULL) {													\
			parmsstr = scc_param_list_to_string(a->params);					\
		} else {															\
			ParameterList c = scc_copy_param_list(a->params);				\
			if (c == NULL) return NULL;										\
			scc_param_checker_strip_defaults((pc), c);						\
			parmsstr = scc_param_list_to_string(c);							\
			list_free(c);													\
		}																	\
		if (parmsstr == NULL) return NULL;	/* OOM */						\
		char* rv = strbuilder_fmt("%s(%s)", keyword, parmsstr);				\
		free(parmsstr);														\
		return rv;															\
	}

/**
 * Generates '_to_string' method for modifier that has no 'params' field
 * and remembers only its child
 */
#define MODIFIER_MAKE_TOSTRING(ActionType, prefix, keyword)					\
	static char* prefix ## _to_string(Action* _a) {							\
		ActionType* a = container_of(_a, ActionType, action);				\
		ParameterList l = scc_inline_param_list(							\
				scc_new_action_parameter(a->child)							\
		);																	\
																			\
		char* strl = scc_param_list_to_string(l);							\
		char* rv = (strl == NULL)											\
					? NULL													\
					: strbuilder_fmt("%s(%s)", keyword, strl);				\
		list_free(l);														\
		free(strl);															\
		return rv;															\
	}

#define MODIFIER_MAKE_DESCRIBE(ActionType, format,multiline_format)			\
	static char* describe(Action* _a, ActionDescContext ctx) {				\
		ActionType* a = container_of(_a, ActionType, action);				\
		char* cdesc = scc_action_get_description(a->child, ctx);			\
		char* rv = NULL;													\
		if (cdesc != NULL) {												\
			if ((ctx == AC_STICK) || (ctx == AC_PAD))						\
				rv = strbuilder_fmt((multiline_format), cdesc);				\
			else															\
				rv = strbuilder_fmt((format), cdesc);						\
			free(cdesc);													\
		}																	\
		return rv;															\
	}

