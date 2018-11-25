#pragma once
#include "scc/utils/tokenizer.h"
#include "scc/error.h"
#include <stdbool.h>

/**
 * Parses single parameter.
 * Returned parameter (or error) has to be dereferenced manually.
 */
ParamOE scc_parse_parameter(Tokens* tokens);

/**
 * Parses list of parameters (stuff that follows after '(', up to next ')').
 * Returns action generated using this list and given keyword.
 * Returned action (or error) has to be dereferenced manually.
 */
ActionOE scc_parse_action_parameters(Tokens* tokens, const char* keyword);

/** Returns true if passed string is valid integer */
bool scc_str_is_int(const char* str);
/** Returns true if passed string is valid float */
bool scc_str_is_float(const char* str);

/**
 * Parses that part of action definition in parantheses (or fact that there are
 * no parentheses at all)
 */
ActionOE parse_after_keyword(Tokens* tokens, const char* keyword);
