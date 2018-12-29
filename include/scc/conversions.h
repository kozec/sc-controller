/**
 * SC Controller - conversions
 *
 * Mainly functions to convert KEY_* constants used by action parser
 * in all possible ways
 */
#pragma once
#include "scc/controller.h"

/** Largest recognized keycode value */
extern const uint16_t SCC_KEYCODE_MAX;

/**
 * Converts KEY_* value to hw keycode used by uinput
 * Returns 0 for unknown values, so this can also be used to check if keycode
 * represents known KEY_* constant.
 */
uint16_t scc_keycode_to_hw_scan(Keycode keycode);


/**
 * Converts KEY_* value to x11 keycode usable by XTestFakeKeyEvent & co.
 * Returns 0 for unknown values.
 */
unsigned int scc_keycode_to_x11(Keycode code);

#ifdef _WIN32
/**
 * Converts KEY_* value to scancode usable by winapi.
 * Returns 0 for unknown values.
 *
 * Available only on Windows.
 */
uint16_t scc_keycode_to_win32_scan(Keycode code);
#endif

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

