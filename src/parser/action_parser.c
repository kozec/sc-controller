#include "scc/utils/strbuilder.h"
#include "scc/utils/tokenizer.h"
#include "scc/parameter.h"
#include "scc/action.h"
#include "scc/parser.h"
#include "scc/error.h"
#include "parser.h"
#include <stdlib.h>


inline static ParamOE unexpected_token_error(const char* token) {
	return (ParamOE)scc_new_param_error(AEC_PARSE_ERROR, "Unexpected '%s'", token);
}


static ActionOE parse_action(Tokens* tokens) {
	if (iter_has_next(tokens)) {
		const char* keyword = iter_next(tokens);
		if (scc_action_known(keyword)) {
			// token is broken once iter_next is called, so copy of it has to be created
			char* copy = strbuilder_cpy(keyword);
			if (copy == NULL)
				return (ActionOE)scc_oom_action_error();
			ActionOE action = parse_after_keyword(tokens, copy);
			free(copy);
			return action;
		} else {
			return (ActionOE)unexpected_token_error(keyword).error;
		}
	} else {
		return (ActionOE)scc_new_parse_error("Syntax error");
	}
}


ActionOE parse_after_keyword(Tokens* tokens, const char* keyword) {
	ActionOE a = scc_parse_action_parameters(tokens, keyword);
	if (IS_ACTION_ERROR(a)) return a;
	
	if (iter_has_next(tokens)) {
		tokens_skip_whitespace(tokens);
		
		char t = tokens_peek_char(tokens);
		if ((t == ')') || (t == ','))
			return a;
		
		RC_REL(ACTION(a));
		return (ActionOE)scc_new_parse_error("Parsing shit after action not yet implemented");
		
		// if p.s.Peek() == ')' || p.s.Peek() == ',' {
		// 	return a, nil
		// }
		// p.s.Scan()
		// if p.s.TokenText() == "and" {
		// 	if !p.tokensLeft() {
		// 		return nil, &ParseError{"Expected action after 'and'", p.s.Pos()}
		// 	}
		// 	next, err := p.parseAction()
		// 	if err != nil { return nil, err }
		// 	a = actions.NewMultiAction([]scc.Action{ a, next })
		// 	return a, nil
		// }
		// if p.s.TokenText() == ";" {
		// 	p.skipWhitespace()
		// 	if !p.tokensLeft() {
		// 		// Unlike with 'and', ; at end of line is OK and just silently ignored
		// 		return a, nil
		// 	}
		// 	next, err := p.parseAction()
		// 	if err != nil { return nil, err }
		// 	a = actions.NewMacro([]scc.Action{ a, next })
		// 	return a, nil
		// TODO: newline
	}
	return a;
}


ActionOE scc_parse_action(const char* source) {
	Tokens* tokens = tokenize(source);
	ActionOE a = parse_action(tokens);
	tokens_free(tokens);
	return a;
	// FOREACH(const char*, i, tokens) {
	// 	printf(" - '%s' : %i\n", i, scc_action_known(i));
	// }
}
