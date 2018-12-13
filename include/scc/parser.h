#pragma once
#include "scc/action.h"
#include "scc/error.h"

/**
 * Parses action from string. Returns Action or ActionError with one reference
 * that has to be released by caller in both cases.
 */
ActionOE scc_parse_action(const char* source);

/**
 * There is pre-set list of constants recognized by parser (mainly keycodes
 * and gamepad and mouse axes).
 * 
 * This function returns integer value (which fits to uint16_t alias Keycode)
 * for given constant name, or -1 (which doesn't fit to uint16_t, that's why
 * int32_t is return type here) if there is no constant with given name.
 *
 * List of constants is allocated when this function is called for 1st time and
 * so it can theoretically fail to find valid constant if there is no memory
 * for allocation. This situation will be indicated by return value -2.
 */
int32_t scc_get_int_constant(const char* key);

/**
 * In addition to integer constants above, there is also list of strings
 * recognized as constant. Those are expanding to itself (constant named LEFT
 * has value "LEFT").
 *
 * If 'key' is recognized constant, returns its name. Returned string should NOT
 * be deallocated, ever.
 * Returns NULL for unrecognized strings.
 */
const char* scc_get_string_constant(const char* key);


/**
 * Returns name of key (e.g. KEY_A for 30) or NULL if key is not recognized.
 * Returned value shall not be deallocated.
 */
const char* scc_get_key_name(int32_t code);
