/**
 * Common but private config definitions
 */
#pragma once
#include "scc/config.h"
#include <stdbool.h>
#include <stdint.h>

/** No path (requested or used) should be longer than this */
#define JSONPATH_MAX_LEN		256
// Just arbitrary limit
#define MAX_ARRAY_SIZE			256

#ifdef _WIN32
	#include <windows.h>
	#include "scc/utils/hashmap.h"
	
	typedef struct {
		ConfigValueType			type;
		union {
			const char*			v_str;
			char**				v_strar;
			int64_t				v_int;
			double				v_double;
		};
	} config_value_t;
#else
	#include "scc/utils/aojls.h"
	typedef json_value_t config_value_t;
#endif

struct config_item {
	const char*					path;
	const ConfigValueType		type;
	union {
		const char*				v_str;
		const char**			v_strar;
		int64_t					v_int;
		bool					v_bool;
		double					v_double;
	};
	config_value_t*				value;
};

struct _Config {
	// Private version of Config
	Config						config;
	char						buffer[JSONPATH_MAX_LEN];
	const struct config_item*	defaults;
#ifdef _WIN32
	HKEY						root;
	map_t						values;
	map_t						giant_memoryleak;
#else
	char*						filename;
	/** 'prefix' is set only by test */
	char*						prefix;
	aojls_ctx_t*				ctx;
#endif
};


extern const struct config_item DEFAULTS[];
extern const struct config_item CONTROLLER_DEFAULTS[];
extern const char* DEFAULT_PROFILES[];
extern const char* DEFAULT_ENABLED_DRIVERS[];

inline static const char* last_element(const char* path) {
	const char* e = strrchr(path, '/');
	e = (e == NULL) ? path : (e + 1);
	return e;
}

const struct config_item* config_get_default(struct _Config* c, const char* path);

config_value_t* config_get_value(struct _Config* c, const char* path, ConfigValueType type);

