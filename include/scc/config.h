/**
 * SC Controller - Config
 *
 * Config is container (aojls wrapper) that loads configuration from JSON file
 * and provides methods to access values, while supplying defaults where needed.
 *
 * Supported value types are int, double and string. Boolean is supported,
 * but converted to int (1 for true) internally.
 * To reference value, path should be used. That means to retrieve value stored
 * as { 'key1': { 'subkey': { 'value': 42 }}}, one should call
 * config_get_int(c, "key1/subkey/value").
 *
 * Config object is reference-counted. Any value returned by it will be held in
 * memory at least until Config object itself is deallocated.
 */
#pragma once
#include "scc/utils/aojls.h"
#include "scc/utils/rc.h"
#include <stdint.h>

typedef struct Config Config;

struct Config {
	RC_HEADER;
};

/**
 * Loads configuration from default location (~/.config/scc/config.json).
 * This works even if file doesn't exists or cannot be readed, defaults are
 * supplied in such case.
 *
 * Returns Config object with single reference or NULL if memory cannot be allocated.
 */
Config* config_load();

/**
 * Loads configuration from specified file handle.
 *
 * If valid JSON cannot be loaded from given handle, returns NULL and updates
 * 'error_return' string with desciption up to 'error_limit' characters.
 * 'error_limit' should be at least 256B, but can be lower.
 * On memory error, returns NULL and sets error_return to empty string.
 * 'error_return' can be NULL, this will not cause crashing.
 * Otherwise, Returns Config object with single reference.
 */
Config* config_load_from(int fd, char* error_return, size_t error_limit);

/**
 * Returns string. Returns NULL (and logs error) if memory cannot be
 * allocated or invalid path is requested.
 *
 * Returned string is part of Config object memory and shall NOT be deallocated by caller.
 */
const char* config_get(Config* c, const char* json_path);

/**
 * Fills 'target' with up to 'limit' recent profiles names. Returns number of
 * stored profiles.
 * Strings set to 'target' are part Config object memory and shall _not_ be
 * deallocated by caller.
 */
size_t config_get_recents(Config* c, const char** target, size_t limit);

/** Returns integer value. Returns 0 (and logs error) if invalid path is requested */
int64_t config_get_int(Config* c, const char* json_path);

/** Returns double value. Returns 0 (and logs error) if invalid path is requested */
double config_get_double(Config* c, const char* json_path);

/** Returns true if given driver name is mentioned and set to enabled in config */
bool config_is_driver_enabled(Config* c, const char* json_path);
