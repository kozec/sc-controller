#include "scc/utils/strbuilder.h"
#include "scc/utils/tokenizer.h"
#include "scc/utils/assert.h"
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
	// TODO: range
	/*
	token := p.s.TokenText()
	param := ConstantToParameter(token)
	if param != nil {
		p.skipWhitespace()
		op := p.s.Peek()
		if param.Type() & actions.PTInteger == actions.PTInteger && (op == '<' || op == '>') {
			rangeType := actions.RangeTypeGreater
			if op == '<' {
				rangeType = actions.RangeTypeLess
			}
			p.s.Scan()
			or_eq := p.s.Peek()
			if or_eq == '=' {
				rangeType |= actions.RangeTypeOrEqual
				p.s.Scan()
			} else {
				or_eq = 0
			}
			next_param, err := p.parseParameter()
			if err != nil || next_param.Type() & actions.PTFloat == 0 || next_param.Type() & actions.PTConstant != 0 {
				if or_eq != 0 {
					return nil, p.parseError(fmt.Sprintf("Expected number after '%c%c'", op, or_eq))
				} else {
					return nil, p.parseError(fmt.Sprintf("Expected number after '%c'", op))
				}
			}
			return actions.NewRange(param, rangeType, next_param.Float()), nil
		}
		return param, nil
	}
	*/
	
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
	
	
	/*
	// String
	if strings.HasPrefix(token, "\"") && strings.HasSuffix(token, "\"") {
		return actions.NewStringParameter(token[1:len(token)-1]), nil
	}
	
	// Backwards compatibility; This is just silently ignored,  "X.y" is parsed as "y"
	if token == "Keys" || token == "Axes" || token == "Rels" {
		p.s.Scan()
		dot := p.s.TokenText()
		if dot != "." {
			return nil, p.parseError(fmt.Sprintf("Expected '.' after '%s'", token))
		}
		p.s.Scan()
		conststr := p.s.TokenText()
		param := ConstantToParameter(conststr)
		if param == nil {
			return nil, p.parseError(fmt.Sprintf("Expected constant after '%s.'", token))
		}
		return param, nil
	}
	
	return nil, p.parseError(fmt.Sprintf("Expected parameter, got '%s'", token))
	*/
}


ActionOE scc_parse_action_parameters(Tokens* tokens, const char* keyword) {
	ParamOE param;
	ActionOE a = {NULL};
	ParameterList params = list_new(Parameter, 0);
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
			if (!list_add(params, PARAMETER(param))) goto scc_pap_err_cleanup;
			
			tokens_skip_whitespace(tokens);
			t = tokens_peek_char(tokens);
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
	
	a = scc_action_new(keyword, params);
scc_pap_err_cleanup:
	list_free(params);
	if (a.action != NULL)
		return a;
	else if (IS_PARAM_ERROR(param))
		return (ActionOE)param.error;
	return (ActionOE)scc_oom_action_error();
}
