#include "scc/utils/strbuilder.h"
#include "scc/utils/tokenizer.h"
#include "scc/utils/assert.h"
#include "scc/conversions.h"
#include "scc/parameter.h"
#include "scc/action.h"
#include "scc/parser.h"
#include "scc/error.h"
#include "parser.h"
#include <string.h>
#include <stdlib.h>

/**
 * "Maybe OOM"
 * If passed argument is proper parameter, this returns it unchanged.
 * If it's NULL (as scc_new_XY_parameter returns on OOM), returns scc_oom_action_error().
 */
static inline ParamOE mOOM(Parameter* p) {
	if (p == NULL)
		return (ParamOE)scc_oom_action_error();
	return (ParamOE)p;
}


ParamOE scc_parse_parameter(Tokens* tokens) {
	// TODO: is skipWhitespace needed?
	tokens_skip_whitespace(tokens);
	
	if (!iter_has_next(tokens))
		return (ParamOE)scc_new_parse_error("Expected parameter at end of string");
	
	const char* token = iter_next(tokens);
	
	if ((strstr(token, "Keys.") == token) || (strstr(token, "Rels.") == token) || (strstr(token, "Axes.") == token))
		token = &token[5];
	
	int64_t c = scc_get_int_constant(token);
	if (c >= 0)
		return mOOM(scc_new_const_int_parameter(token, c));
	const char* c2 = scc_get_string_constant(token);
	if (c2 != NULL)
		return mOOM(scc_new_const_string_parameter(c2));
	
	// "None"
	if (strcmp(token, "None") == 0) {
		return (ParamOE)None;
	}
	
	// Action
	if (scc_action_known(token)) {
		char* copy = strbuilder_cpy(token);
		if (copy == NULL)
			return (ParamOE)scc_oom_action_error();
		ActionOE action = parse_after_keyword(tokens, copy);
		free(copy);
		if (IS_ACTION_ERROR(action))
			return (ParamOE)action.error;
		return (ParamOE)scc_new_action_parameter(action.action);
	}
	
	// Integer or negative integer
	if (scc_str_is_int(token)) {
		return mOOM(scc_new_int_parameter(atoi(token)));
	}
	
	/*
	// TODO: Integer as hex
	if reHex.MatchString(token) {
		i, err := strconv.ParseInt(reHex.FindStringSubmatch(token)[1], 16, 64)
		if err != nil { return nil, p.parseError(err.Error()) }
		return actions.NewHexParameter(i), nil
	}
	*/
	
	// Float or negative float
	if (scc_str_is_float(token)) {
		return mOOM(scc_new_float_parameter(atof(token)));
	}
	
	size_t len = strlen(token);
	if ((len > 2) && ((token[0] == '"') || (token[0] == '\'')) && (token[len-1] == token[0])) {
		char* cpy = strbuilder_cpy(&token[1]);
		if (cpy == NULL)
			return (ParamOE)scc_oom_action_error();
		cpy[strlen(cpy)-1] = 0;
		return mOOM(scc_string_to_parameter(cpy));
	}
	
	return (ParamOE)scc_new_parse_error("Unexpected '%s'", token);
}


ParameterList _scc_tokens_to_param_list(Tokens* tokens, ParamError** err) {
	*err = NULL;
	ParamOE param;
	ParameterList params = scc_make_param_list(NULL);
	if (params == NULL) return NULL;
	
	tokens_skip_whitespace(tokens);
	char t = tokens_peek_char(tokens);
	if (t == '(') {
		iter_next(tokens);		// skips over '('
		while (t != ')') {
			tokens_skip_whitespace(tokens);
			if (tokens_peek_char(tokens) == ')')
				break;
			param = scc_parse_parameter(tokens);
			if (IS_PARAM_ERROR(param)) goto scc_pap_err_cleanup;
			
			tokens_skip_whitespace(tokens);
			t = tokens_peek_char(tokens);
			if ((t == '>') || (t == '<')) {			// Check & parse range operator
				const char* op = iter_next(tokens);
				RangeType rt = 0;
				if (0 == strcmp(">", op))
					rt = RT_GREATER;
				else if (0 == strcmp("<", op))
					rt = RT_LESS;
				else if (0 == strcmp(">=", op))
					rt = RT_GREATER_OREQUAL;
				else if (0 == strcmp("<=", op))
					rt = RT_LESS_OREQUAL;
				if (rt == 0) {
					RC_REL(PARAMETER(param));
					param = (ParamOE)scc_new_parse_error("Unexpected '%s' after parameter", op);
					goto scc_pap_err_cleanup;
				}
				ParamOE rigth_side = scc_parse_parameter(tokens);
				if (IS_PARAM_ERROR(rigth_side)) {
					RC_REL(PARAMETER(param));
					param = rigth_side;
					goto scc_pap_err_cleanup;
				}
				if (!(scc_parameter_type(PARAMETER(rigth_side)) & PT_FLOAT)) {
					RC_REL(PARAMETER(param));
					char* _rigth_side = scc_parameter_to_string(PARAMETER(rigth_side));
					param = (ParamOE)((_rigth_side == NULL) ? NULL : scc_new_parse_error("Unexpected '%s' after operator", _rigth_side));
					free(_rigth_side);
					RC_REL(PARAMETER(rigth_side));
					goto scc_pap_err_cleanup;
				}
				// Sucesfully parsed range
				Parameter* range = scc_new_range_parameter(PARAMETER(param), rt, scc_parameter_as_float(PARAMETER(rigth_side)));
				RC_REL(PARAMETER(param));
				RC_REL(PARAMETER(rigth_side));
				param = (ParamOE)range;
				if (range == NULL)
					goto scc_pap_err_cleanup;
				t = tokens_peek_char(tokens);
			}
			
			if (!list_add(params, PARAMETER(param))) goto scc_pap_err_cleanup;
			
			if (t == 0) {
				param = (ParamOE)scc_new_parse_error("Expected ')'");
				goto scc_pap_err_cleanup;
			} else if (t == ',') {
				iter_next(tokens); // skips over ','
				tokens_skip_whitespace(tokens);
				t = tokens_peek_char(tokens);
			} else if (t != ')') {
				param = (ParamOE)scc_new_parse_error("Unexpected '%c' after parameter", t);
				goto scc_pap_err_cleanup;
			}
		}
		iter_next(tokens); // skips over ')'
	}
	
	return params;
	
scc_pap_err_cleanup:
	list_free(params);
	*err = param.error;
	return NULL;
}


ActionOE scc_parse_action_with_parameters(Tokens* tokens, const char* keyword) {
	ActionOE a = {NULL};
	ParamError* err = NULL;
	ParameterList params = _scc_tokens_to_param_list(tokens, &err);
	if (params == NULL) {
		if (err == NULL)
			return (ActionOE)scc_oom_action_error();
		return (ActionOE)err;
	}
	
	a = scc_action_new(keyword, params);
	list_free(params);
	return a;
}

