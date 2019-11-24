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
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/utils/dll_export.h"
#include <stdint.h>
#include "scc/utils/aojls.h"
#include "scc/utils/rc.h"
#include <stdint.h>

typedef struct Config Config;
#define SCC_CONFIG_ERROR_LIMIT 1024

struct Config {
	RC_HEADER;
};

typedef enum ConfigValueType {
	// Numbers here are chosen to losely match json_type_t values
	CVT_STR_ARRAY		= 1,
	CVT_DOUBLE			= 2,
	CVT_STRING			= 3,
	CVT_BOOL			= 4,
	CVT_INT				= 10,	// json_type_t doesn't have this one
} ConfigValueType;


/**
 * Makes sure that configuration directory exists and contains config file.
 * Then loads config file, ensures all required values are set (adding defaults
 * where needed) and saves it back.
 *
 * Returns Config* instance with single reference or NULL if anything fails.
 */
DLL_EXPORT Config* config_init();

/**
 * Loads configuration from default location (~/.config/scc/config.json).
 * This works even if file or parent directory doesn't exists or cannot be
 * readed, as defaults are supplied in such case.
 *
 * Returns Config object with single reference or NULL if memory cannot be allocated.
 */
DLL_EXPORT Config* config_load();


/**
 * Saves configuration. Using this on config loaded with config_load_from is unsupported.
 * Returns true on success.
 */
DLL_EXPORT bool config_save(Config* cfg);

/**
 * Fills config with default where user-provided value is missing.
 *
 * Usually there is no need to call this as config_get* automatically returns
 * default when needed and config_init ensures all defaults are in place.
 *
 * Returns true if any default was replaced. If false is returned, calling
 * config_save would have no point.
 */
DLL_EXPORT bool config_fill_defaults(Config* cfg);

/**
 * On everything that's not Windows, loads configuration from specified file.
 *
 * If valid JSON cannot be loaded from given handle, returns NULL and updates
 * 'error_return' string with desciption up to 1024 characters.
 *
 * On Windows, loads configuration from subkey in H_KEY_CURRENT_USER registry.
 * If specified subkey is not found or cannot be loaded,
 * returns NULL and updates 'error_return' string with desciption up
 * to 1024 characters.
 *
 * On memory error, returns NULL and sets error_return to empty string.
 * 'error_return' may be NULL, in which case it's not updated. If it's not NULL,
 * it has to have space for at least 1024 characters.
 *
 * On success, returns Config object with single reference.
 */
#ifdef _WIN32
DLL_EXPORT Config* config_load_from(const char* path, char* error_return);
#else
DLL_EXPORT Config* config_load_from(const char* filename, char* error_return);
#endif

/**
 * Returns string. Returns NULL (and logs error) if memory cannot be
 * allocated or invalid path is requested.
 *
 * Returned string is part of Config object memory and shall NOT be deallocated by caller.
 */
DLL_EXPORT const char* config_get(Config* c, const char* path);

/** Returns integer value. Returns 0 (and logs error) if invalid path is requested */
DLL_EXPORT int64_t config_get_int(Config* c, const char* path);

/** Returns double value. Returns 0 (and logs error) if invalid path is requested */
DLL_EXPORT double config_get_double(Config* c, const char* path);

/** Returns true if given key exists and has subkeys */
DLL_EXPORT bool config_is_parent(Config* c, const char* path);

/** Returns true if given driver name is mentioned and set to enabled in config */
DLL_EXPORT bool config_is_driver_enabled(Config* c, const char* path);

/**
 * Retrieves elements of string array.
 * Fills 'target' up to 'limit'. Returns number of stored strings.
 * Strings set to 'target' are part Config object memory and shall _not_ be
 * deallocated by caller.
 */
DLL_EXPORT size_t config_get_strings(Config* c, const char* path, const char** target, size_t limit);

/**
 * Returns type of configuration value (see ConfigValueType)
 * or 0 if key is not found.
 */
DLL_EXPORT ConfigValueType config_get_type(Config* c, const char* path);


/**
 * Stores string.
 * Returns 1 on success, 0 if memory cannot be allocated.
 * Returns -1 if invalid path is requested.
 * Returns -2 if config_set tries to overwrite value with different type.
 */
DLL_EXPORT int config_set(Config* c, const char* path, const char* value);

/**
 * Stores integer value.
 * Returns 1 on success, 0 if memory cannot be allocated.
 * Returns -1 if invalid path is requested.
 * Returns -2 if config_set_int tries to overwrite value with different type.
 */
DLL_EXPORT int config_set_int(Config* c, const char* path, int64_t value);

/**
 * Stores double value.
 * Returns 1 on success, 0 if memory cannot be allocated.
 * Returns -1 if invalid path is requested.
 * Returns -2 if config_set_double tries to overwrite value with different type.
 */
DLL_EXPORT int config_set_double(Config* c, const char* path, double value);

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
DLL_EXPORT int config_set_strings(Config* c, const char* path, const char** list, ssize_t count);

#ifdef __cplusplus
}
#endif

