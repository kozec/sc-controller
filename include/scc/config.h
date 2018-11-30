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
 * Saves configuration. It's illegal to call this on config loaded with config_load_from
 * Returns true on success.
 */
bool config_save(Config* cfg);

/**
 * Fills config with default where user-provided value is missing.
 * Usually there is no need to call this as config_get* automatically returns
 * default when needed.
 *
 * Returns true if any default was replaced. If false is returned, calling
 * config_save would have no point.
 */
bool config_fill_defaults(Config* cfg);

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
const char* config_get(Config* c, const char* path);

/** Returns integer value. Returns 0 (and logs error) if invalid path is requested */
int64_t config_get_int(Config* c, const char* path);

/** Returns double value. Returns 0 (and logs error) if invalid path is requested */
double config_get_double(Config* c, const char* path);

/** Returns true if given driver name is mentioned and set to enabled in config */
bool config_is_driver_enabled(Config* c, const char* path);

/**
 * Retrieves elements of string array.
 * Fills 'target' up to 'limit'. Returns number of stored strings.
 * Strings set to 'target' are part Config object memory and shall _not_ be
 * deallocated by caller.
 */
size_t config_get_strings(Config* c, const char* path, const char** target, size_t limit);


/**
 * Stores string.
 * Returns 1 on success, 0 if memory cannot be allocated.
 * Returns -1 if invalid path is requested.
 * Returns -2 if config_set tries to overwrite value with different type.
 */
int config_set(Config* c, const char* path, const char* value);

/**
 * Stores integer value.
 * Returns 1 on success, 0 if memory cannot be allocated.
 * Returns -1 if invalid path is requested.
 * Returns -2 if config_set_int tries to overwrite value with different type.
 */
int config_set_int(Config* c, const char* path, int64_t value);

/**
 * Stores double value.
 * Returns 1 on success, 0 if memory cannot be allocated.
 * Returns -1 if invalid path is requested.
 * Returns -2 if config_set_double tries to overwrite value with different type.
 */
int config_set_double(Config* c, const char* path, double value);

/**
 * Stores string array. Empty strings are not allowed.
 * If 'count' is set to negative, size of stored array is determined by
 * searching for last element of 'list' which has to be be NULL.
 *
 * Elements stored before are discarded, but not deallocated
 * until entire Config object is not deallocated.
 *
 * Returns 1 on success, 0 if memory cannot be allocated.
 * Returns -1 if invalid path is requested.
 * Returns -2 if config_set_strings tries to overwrite value with different type.
 */
int config_set_strings(Config* c, const char* path, const char** list, ssize_t count);
