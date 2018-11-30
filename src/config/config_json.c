/**
 * SC Controller - config
 * Handles loading, storing and querying config file
 *
 * Default config backend that stores data in json file
 */
#ifndef _WIN32
#define LOG_TAG "config"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/hashmap.h"
#include "scc/tools.h"
#include "config.h"
#include <sys/stat.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
#include <fcntl.h>

#define CONFIG_FILENAME			"config.c.json"
// TODO: Remove '.c.' from CONFIG_FILENAME.


static void config_dealloc(void* _c) {
	struct _Config* c = container_of(_c, struct _Config, config);
	
	json_free_context(c->ctx);
	free(c->filename);
	free(c);
}

static inline struct _Config* config_new() {
	struct _Config* c = malloc(sizeof(struct _Config));
	if (c == NULL) return NULL;
	RC_INIT(&c->config, &config_dealloc);
	c->filename = NULL;
	c->ctx = NULL;
	return c;
}

static long json_reader_fn(char* buffer, size_t len, void* reader_data) {
	return read(*((int*)reader_data), buffer, len);
}

/** JSON-parsing part of config_load_from */
static bool config_load_json_file(struct _Config* c, int fd, char* error_return, size_t error_limit) {
	aojls_deserialization_prefs prefs = {
		.reader = &json_reader_fn,
		.reader_data = (void*)&fd
	};
	
	c->ctx = aojls_deserialize(NULL, 0, &prefs);
	if ((c->ctx == NULL) || (prefs.error != NULL)) {
		LERROR("Failed to decode configuration: %s", prefs.error);
		if (error_return != NULL) {
			strncpy(error_return, prefs.error, error_limit);
			error_return[error_limit - 1] = 0;
		}
		json_free_context(c->ctx);
		c->ctx = NULL;
		return false;
	}
	
	return true;
}

Config* config_load() {
	char error_return[1024];
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
	} else if (!config_load_json_file(c, fd, error_return, 1024)) {
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

Config* config_load_from(int fd, char* error_return, size_t error_limit) {
	if (error_return != NULL)
		error_return[0] = 0;
	
	struct _Config* c = config_new();
	if (c == NULL) return NULL;
	
	if (!config_load_json_file(c, fd, error_return, error_limit)) {
		// Failed to load
		config_dealloc(&c->config);
		return NULL;
	}
	return &c->config;
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
				child = json_make_object(c->ctx);
				if (child != NULL)
					child = json_object_set(obj, c->buffer, (json_value_t*)child);
				if (child == NULL)
					return NULL;
			} else {
				obj = child;
			}
			path = &path[slash_index + 1];
		}
	}
	return NULL;
}

config_value_t* config_get_value(struct _Config* c, const char* path, ConfigValueType type) {
	json_object* obj = config_get_parent(c, path, false);
	if (obj == NULL)
		return NULL;
	
	config_value_t* value = json_object_get_object_as_value(obj, last_element(path));
	switch (type) {
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
	}
	return value;
}

bool config_save_writer(const char* buffer, size_t len, void* _fd) {
	uintptr_t fd = (uintptr_t)_fd;
	return write(fd, buffer, len) == len;
}

bool config_save(Config* _c) {
	struct _Config* c = container_of(_c, struct _Config, config);
	if (c->filename == NULL)
		return false;
	int fd = open(c->filename, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	if (fd < 0) {
		WARN("Failed to save config file: %s. ", strerror(errno));
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
	}
	
	const struct config_item* def = config_get_default(c, path);
	if ((def != NULL) && (def->type == CVT_INT)) {
		config_set_int(_c, path, def->v_int);
		return def->v_int;
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
		config_set_int(_c, path, def->v_double);
		return def->v_double;
	}
	
	return 0;
}

size_t config_get_strings(Config* _c, const char* path, const char** target, size_t limit) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_array* value = json_as_array(config_get_value(c, path, CVT_STR_ARRAY));
	size_t j = 0;
	if (value == NULL) {
		const struct config_item* def = config_get_default(c, path);
		if ((def == NULL) || (def->type != CVT_STR_ARRAY))
			return 0;
		for (size_t i=0; (i<limit) && (def->v_strar[i]!=NULL); i++) {
			target[i] = def->v_strar[i];
			j++;
		}
	} else {
		for (size_t i=0; (i<limit) && (i<json_array_size(value)); i++) {
			const char* s = json_array_get_string(value, i);
			if (s != NULL) {
				target[j] = s;
				j++;
			}
		}
	}
	return j;
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
	json_object* parent = config_get_parent(c, path, true);
	if (parent == NULL) return 0;
	return config_set_common(parent, (json_value_t*)json_from_string(c->ctx, value), path);
}

int config_set_int(Config* _c, const char* path, int64_t value) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_object* parent = config_get_parent(c, path, true);
	if (parent == NULL) return 0;
	// TODO: Check for bools here
	const struct config_item* def = config_get_default(c, path);
	if ((def != NULL) && (def->type == CVT_BOOL))
		return config_set_common(parent, (json_value_t*)json_from_boolean(c->ctx, value), path);
	else
		return config_set_common(parent, (json_value_t*)json_from_number(c->ctx, value), path);
}

int config_set_double(Config* _c, const char* path, double value) {
	struct _Config* c = container_of(_c, struct _Config, config);
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

#endif // _WIN32
