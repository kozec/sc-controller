/**
 * SC Controller - config
 * Handles loading, storing and querying config file
 *
 * Default config backend that stores data in json file
 */
#define LOG_TAG "config"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/hashmap.h"
#include "scc/utils/math.h"
#include "scc/tools.h"
#include "config.h"
#include <sys/stat.h>
#include <limits.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdlib.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>

#define CONFIG_FILENAME			"config.c.json"
// TODO: Remove '.c.' from CONFIG_FILENAME.

#ifdef _WIN32
	#error "config_json.c included on Windows"
#endif

static void config_dealloc(void* _c) {
	struct _Config* c = container_of(_c, struct _Config, config);
	
	json_free_context(c->ctx);
	free(c->filename);
	free(c->prefix);
	free(c);
}

static inline struct _Config* config_new() {
	struct _Config* c = malloc(sizeof(struct _Config));
	if (c == NULL) return NULL;
	RC_INIT(&c->config, &config_dealloc);
	c->defaults = DEFAULTS;
	c->filename = NULL;
	c->prefix = NULL;
	c->ctx = NULL;
	return c;
}

static long json_reader_fn(char* buffer, size_t len, void* reader_data) {
	return read(*((int*)reader_data), buffer, len);
}

/** JSON-parsing part of config_load_from */
static bool config_load_json_file(struct _Config* c, int fd, char* error_return) {
	aojls_deserialization_prefs prefs = {
		.reader = &json_reader_fn,
		.reader_data = (void*)&fd
	};
	
	c->ctx = aojls_deserialize(NULL, 0, &prefs);
	if ((c->ctx == NULL) || (prefs.error != NULL)) {
		LERROR("Failed to decode configuration: %s", prefs.error);
		if (error_return != NULL) {
			strncpy(error_return, prefs.error, SCC_CONFIG_ERROR_LIMIT);
			error_return[SCC_CONFIG_ERROR_LIMIT - 1] = 0;
		}
		json_free_context(c->ctx);
		c->ctx = NULL;
		return false;
	}
	
	return true;
}

Config* config_load() {
	char error_return[SCC_CONFIG_ERROR_LIMIT];
	struct _Config* c = config_new();
	if (c == NULL) return NULL;
	
	StrBuilder* sb = strbuilder_new();
	strbuilder_add(sb, scc_get_config_path());
	strbuilder_add_path(sb, CONFIG_FILENAME);
	if (strbuilder_failed(sb))
		goto config_load_fail;
	
	c->filename = strbuilder_consume(sb);
	int fd = open(c->filename, O_RDONLY);
	if (fd < 0) {
		WARN("Failed to open config file: %s. Starting with defaults.", strerror(errno));
	} else if (!config_load_json_file(c, fd, error_return)) {
		WARN("Failed to parse config file: %s. Starting with defaults", error_return);
	}
	if (c->ctx == NULL) {
		c->ctx = aojls_deserialize("{}", 2, NULL);
		if (c->ctx == NULL)
			goto config_load_fail;
		// json_object* root = json_make_object(c->ctx);
	}
	
	return &c->config;
	
config_load_fail:
	config_dealloc(&c->config);
	return NULL;
}

Config* config_load_from(const char* filename, char* error_return) {
	if (error_return != NULL)
		error_return[0] = 0;
	
	int fd = open(filename, O_RDONLY);
	if (fd < 0) {
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-but-set-variable"
		int xsi;
		if (error_return != NULL) {
			xsi = strerror_r(errno, error_return, SCC_CONFIG_ERROR_LIMIT);
		}
		return NULL;
#pragma GCC diagnostic pop
	}
	
	struct _Config* c = config_new();
	if (c == NULL) return NULL;
	
	c->filename = strbuilder_cpy(filename);
	if ((c->filename == NULL) || (!config_load_json_file(c, fd, error_return))) {
		// Failed to load / allocate
		close(fd);
		config_dealloc(&c->config);
		return NULL;
	}
	close(fd);
	return &c->config;
}

bool config_set_prefix(Config* _c, const char* prefix) {
	struct _Config* c = container_of(_c, struct _Config, config);
	char* cpy = strbuilder_cpy(prefix);
	if (cpy == NULL) return false;
	free(c->prefix);
	c->prefix = cpy;
	return true;
}

/**
 * Returns (optionally creating) parent node of value or root node if there are no slashes
 */
static inline json_object* config_get_parent(struct _Config* c, const char* path, bool create) {
	json_object* obj = json_as_object(json_context_get_result(c->ctx));
	while (obj != NULL) {
		const char* slash = strchr(path, '/');
		if (slash == NULL) {
			return obj;
		} else {
			size_t slash_index = slash - path;
			if (slash_index >= JSONPATH_MAX_LEN)
				// Requested path is too long, this is not reasonable thing to request
				return NULL;
			strncpy(c->buffer, path, JSONPATH_MAX_LEN);
			c->buffer[slash_index] = 0;
			json_object* child = json_object_get_object(obj, c->buffer);
			if (child == NULL) {
				if (!create)
					return NULL;
				child = json_make_object(c->ctx);
				if ((child == NULL) || (json_object_set(obj, c->buffer, (json_value_t*)child) == NULL))
					return NULL;
			}
			obj = child;
			path = &path[slash_index + 1];
		}
	}
	return NULL;
}

DLL_EXPORT bool config_is_parent(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	snprintf(c->buffer, JSONPATH_MAX_LEN, "%s/d", path);
	json_object* obj = config_get_parent(c, c->buffer, false);
	return (obj != NULL);
}

config_value_t* config_get_value(struct _Config* c, const char* path, ConfigValueType type) {
	json_object* obj = config_get_parent(c, path, false);
	if (obj == NULL)
		return NULL;
	
	config_value_t* value = json_object_get_object_as_value(obj, last_element(path));
	switch (type) {
	case CVT_OBJECT:
		if (json_get_type(value) != JS_OBJECT)
			return NULL;
		break;
	case CVT_STRING:
		if (json_get_type(value) != JS_STRING)
			return NULL;
		break;
	case CVT_BOOL:
		if (json_get_type(value) != JS_BOOL)
			return NULL;
		break;
	case CVT_INT:
	case CVT_DOUBLE:
		if (json_get_type(value) != JS_NUMBER)
			return NULL;
		break;
	case CVT_STR_ARRAY:
		if (json_get_type(value) != JS_ARRAY)
			return NULL;
		break;
	case CVT_INVALID:
		return NULL;
	}
	return value;
}

ConfigValueType config_get_type(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_object* obj = config_get_parent(c, path, false);
	if ((obj == NULL) && (config_get_default(c, path) != NULL))
		obj = config_get_parent(c, path, true);
	if (obj == NULL)
		return CVT_INVALID;
	
	config_value_t* value = json_object_get_object_as_value(obj, last_element(path));
	json_type_t type = 0;
	if (value != NULL)
		type = json_get_type(value);
	
	const struct config_item* def;
	switch (type) {
	case JS_STRING:
		return CVT_STRING;
	case JS_BOOL:
		return CVT_BOOL;
	case JS_NUMBER:
		def = config_get_default(c, path);
		if (def != NULL)
			return def->type;
		return CVT_DOUBLE;
	case JS_ARRAY:
		return CVT_STR_ARRAY;
	default:
		def = config_get_default(c, path);
		if (def != NULL)
			return def->type;
	}
	
	return CVT_INVALID;
}

bool config_save_writer(const char* buffer, size_t len, void* _fd) {
	uintptr_t fd = (uintptr_t)_fd;
	return write(fd, buffer, len) == len;
}

bool config_save(Config* _c) {
	struct _Config* c = container_of(_c, struct _Config, config);
	if (c->filename == NULL) {
		WARN("Failed to save config file: Filename not set");
		return false;
	}
	int fd = open(c->filename, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	if (fd < 0) {
		WARN("Failed to save config file: %s: %s. ", c->filename, strerror(errno));
		return false;
	}
	aojls_serialization_prefs prefs = {
		.writer = &config_save_writer,
		.writer_data = (void*)(intptr_t)fd,
		
		.eol = NULL,
		.pretty = true,
		.offset_per_level = 4,
		.number_formatter = NULL,
	};
	aojls_serialize(json_context_get_result(c->ctx), &prefs);
	return prefs.success;
}

const char* config_get(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* value = config_get_value(c, path, CVT_STRING);
	if (value != NULL)
		return json_as_string(value);
	
	const struct config_item* def = config_get_default(c, path);
	if ((def != NULL) && (def->type == CVT_STRING)) {
		config_set(_c, path, def->v_str);
		return def->v_str;
	}
	
	return NULL;
}

int64_t config_get_int(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* value = config_get_value(c, path, CVT_INT);
	if (value != NULL) {
		bool correct = true;
		double d_value = json_as_number(value, &correct);
		if (correct)
			return (int64_t)d_value;
	} else {
		value = config_get_value(c, path, CVT_BOOL);
		if (value != NULL) {
			bool correct = true;
			bool b_value = json_as_bool(value, &correct);
			if (correct)
				return (int64_t)b_value;
		}
	}
	
	const struct config_item* def = config_get_default(c, path);
	if (def != NULL) {
		if (def->type == CVT_INT) {
			config_set_int(_c, path, def->v_int);
			return def->v_int;
		}
		if (def->type == CVT_BOOL) {
			config_set_int(_c, path, def->v_bool);
			return def->v_bool;
		}
	}
	
	return 0;
}

double config_get_double(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* value = config_get_value(c, path, CVT_DOUBLE);
	if (value != NULL) {
		bool correct = true;
		double d_value = json_as_number(value, &correct);
		if (correct)
			return d_value;
	}
	
	const struct config_item* def = config_get_default(c, path);
	if ((def != NULL) && (def->type == CVT_DOUBLE)) {
		config_set_double(_c, path, def->v_double);
		return def->v_double;
	}
	
	return 0;
}

ssize_t config_get_strings(Config* _c, const char* path, const char** target, ssize_t limit) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_array* value = NULL;
	json_value_t* obj;
	if (0 == strcmp("/", path)) {
		obj = json_context_get_result(c->ctx);
	} else {
		obj = config_get_value(c, path, CVT_STR_ARRAY);
		if (obj == NULL)
			obj = config_get_value(c, path, CVT_OBJECT);
		value = json_as_array(obj);
	}
	
	ssize_t j = 0;
	if (json_get_type(obj) == JS_OBJECT) {
		json_object* o = json_as_object(obj);
		size_t len = json_object_numkeys(o);
		while ((j < SSIZE_MAX) && (j < len)) {
			if (j >= limit) return -2;
			target[j] = json_object_get_key(o, j);
			j ++;
		}
		return len;
	} else if (value == NULL) {
		const struct config_item* def = config_get_default(c, path);
		if ((def == NULL) || (def->type != CVT_STR_ARRAY)) {
			return 0;
		}
		if (def->v_strar != NULL) {
			for (ssize_t i=0; (i<SSIZE_MAX) && (def->v_strar[i]!=NULL); i++) {
				if (i >= limit) return -2;
				target[i] = def->v_strar[i];
				j++;
			}
		}
	} else {
		for (size_t i=0; i<json_array_size(value); i++) {
			const char* s = json_array_get_string(value, i);
			if (s != NULL) {
				if (j >= limit) return -2;
				target[j] = s;
				j++;
			}
		}
	}
	return j;
}

ssize_t config_get_controllers(Config* _c, const char** target, ssize_t limit) {
	struct _Config* c = container_of(_c, struct _Config, config);
	DIR *dir;
	struct dirent *ent;
	char* device_cfg_path = strbuilder_fmt("%s/devices", (c->prefix != NULL) ? c->prefix : scc_get_config_path());
	if (device_cfg_path == NULL) return -1;
	if ((dir = opendir(device_cfg_path)) == NULL) {
		// Failed to open directory
		WARN("Failed to enumerate '%s': %s", device_cfg_path, strerror(errno));
		return 0;
	}
	
	ssize_t j = 0;
	while (j < SSIZE_MAX - 1) {
		ent = readdir(dir);
		if (ent == NULL) break;
		if (strstr(ent->d_name, ".json") != NULL) {
			if (j >= limit) {
				// 'target' is too small
				j = -2;
				break;
			}
			char* cpy = strbuilder_cpy(ent->d_name);
			if (cpy == NULL) {
				// OOM
				while (j > 0)
					free((char*)target[--j]);
				j = -1;
				break;
			}
			cpy[strlen(ent->d_name) - 5] = 0;			// Strips extension
			target[j++] = cpy;
		}
	}
	closedir (dir);
	return j;
}

inline static char* config_make_controller_filename(struct _Config* c, const char* id) {
	return strbuilder_fmt("%s/devices/%s.json",
				(c->prefix != NULL) ? c->prefix : scc_get_config_path(), id);
}

Config* config_get_controller_config(Config* _c, const char* id, char* error_return) {
	struct _Config* c = container_of(_c, struct _Config, config);
	char* filename = config_make_controller_filename(c, id);
	if (filename == NULL)
		goto config_get_controller_config_oom;
	Config* _rv = config_load_from(filename, error_return);
	if (_rv == NULL)
		return NULL;
	
	struct _Config* rv = container_of(_rv, struct _Config, config);
	rv->defaults = CONTROLLER_DEFAULTS;
	rv->filename = filename;
	filename = NULL;
	if (c->prefix != NULL) {
		if (!config_set_prefix(_rv, c->prefix)) {
			RC_REL(_rv);
			goto config_get_controller_config_oom;
		}
	}
	return _rv;
	
config_get_controller_config_oom:
	if (error_return != NULL)
		strncpy(error_return, "Out of memory", SCC_CONFIG_ERROR_LIMIT);
	return NULL;
}

Config* config_create_controller_config(Config* _c, const char* id, char* error_return) {
	Config* rv = config_get_controller_config(_c, id, error_return);
	if (rv == NULL) {
		struct _Config* c = container_of(_c, struct _Config, config);
		char* filename = config_make_controller_filename(c, id);
		if (filename == NULL) {
			if (error_return != NULL)
				strncpy(error_return, "Out of memory", SCC_CONFIG_ERROR_LIMIT);
			return NULL;
		}
		int fd = open(filename, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
		if (fd < 0) {
			if (error_return != NULL) {
				snprintf(error_return, SCC_CONFIG_ERROR_LIMIT, "Failed to open '%s': %s",
						filename, strerror(fd));
			}
			free(filename);
			return NULL;
		}
		free(filename);
		write(fd, "{}\n", 3);
		close(fd);
		return config_get_controller_config(_c, id, error_return);
	}
	return rv;
}

/** Common part of all config_set-s */
static inline int config_set_common(json_object* parent, json_value_t* value, const char* path) {
	if (value == NULL) return 0;
	if (json_object_set(parent, last_element(path), value) == NULL)
		return 0;
	return 1;
}

int config_set(Config* _c, const char* path, const char* value) {
	struct _Config* c = container_of(_c, struct _Config, config);
	const struct config_item* def = config_get_default(c, path);
	if ((def != NULL) && (def->type != CVT_STRING))
		return -2;
	json_object* parent = config_get_parent(c, path, true);
	if (parent == NULL) return 0;
	json_value_t* json_value =  (json_value_t*)json_from_string(c->ctx, value);
	if (json_value == NULL) return 0;
	return config_set_common(parent, json_value, path);
}

int config_set_int(Config* _c, const char* path, int64_t value) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_object* parent = config_get_parent(c, path, true);
	if (parent == NULL) return 0;
	const struct config_item* def = config_get_default(c, path);
	if ((def != NULL) && (def->type == CVT_BOOL))
		return config_set_common(parent, (json_value_t*)json_from_boolean(c->ctx, value), path);
	else if ((def == NULL) || ((def->type == CVT_INT) || (def->type == CVT_DOUBLE)))
		return config_set_common(parent, (json_value_t*)json_from_number(c->ctx, value), path);
	else
		return -2;
}

int config_set_double(Config* _c, const char* path, double value) {
	struct _Config* c = container_of(_c, struct _Config, config);
	const struct config_item* def = config_get_default(c, path);
	if ((def != NULL) && (def->type != CVT_INT) && (def->type != CVT_DOUBLE))
		return -2;
	
	json_object* parent = config_get_parent(c, path, true);
	if (parent == NULL) return 0;
	return config_set_common(parent, (json_value_t*)json_from_number(c->ctx, value), path);
}

int config_set_strings(Config* _c, const char* path, const char** list, ssize_t count) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_object* parent = config_get_parent(c, path, true);
	if (parent == NULL) return 0;			// OOM
	
	if (count < 0) {
		count = 0;
		if (list != NULL)
			while ((count <= MAX_ARRAY_SIZE) && (list[count] != NULL))
				count++;
		if (count == MAX_ARRAY_SIZE)
			return 0;
	}
	
	json_array* ar = json_make_array(c->ctx);
	if (ar == NULL) return 0;				// OOM
	
	for (size_t i=0; i<count; i++) {
		json_string* str = json_from_string(c->ctx, list[i]);
		if (str == NULL) return 0;			// OOM
		if (json_array_add(ar, (json_value_t*)str) == NULL)
			return 0;						// OOM
	}
	
	if (json_object_set(parent, last_element(path), (json_value_t*)ar) == NULL)
		return 0;
	return 1;
}

int config_delete_key(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_object* parent = config_get_parent(c, path, false);
	if (parent == NULL) return -1;
	json_object_set_undefined(parent, last_element(path));
	return 1;
}

