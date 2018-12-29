#pragma once
#include "scc/action.h"
#include "scc/error.h"

/**
 * Parses action from string. Returns Action or ActionError with one reference
 * that has to be released by caller in both cases.
 */
ActionOE scc_parse_action(const char* source);

