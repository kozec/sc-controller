/*
 * SC-Controller - Actions - ACTION_MAKE_TO_STRING macro.
 *
 * Generates default 'to_string' method. This will work with any action
 * class that stores parameters in 'params' field.
 * If 'pc' (ParamChecker) is not NULL, defaults are stripped.
 */
#pragma once

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
