/**
 * SC Controller - config
 * Handles loading, storing and querying config file
 * 
 * Backend that stores settings in registry
 */
#ifdef _WIN32
#define LOG_TAG "config"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/hashmap.h"
#include "scc/tools.h"
#include "config.h"
#include <windows.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>

#define BUFFER_SIZE		256

#ifndef _WIN32
	#error "config_win32.c included outside of Windows"
#endif

static void config_dealloc(void* _c) {
	struct _Config* c = container_of(_c, struct _Config, config);
	
	if (c->root != NULL)
		RegCloseKey(c->root);
	while (c->giant_memoryleak != NULL) {
		struct InternalString* next = c->giant_memoryleak->next;
		free(c->giant_memoryleak);
		c->giant_memoryleak = next;
	}
	free(c);
}

static inline struct _Config* config_new() {
	struct _Config* c = malloc(sizeof(struct _Config));
	if (c == NULL) return NULL;
	RC_INIT(&c->config, &config_dealloc);
	c->root = NULL;
	c->giant_memoryleak = NULL;
	// About giant_memoryleak... Config guarantees that all strings returned by
	// it are stored in memory at least until Config object is deallocated.
	// To be able to deallocate them eventyally, all strings are stored
	// as linked-list in 'giant_memoryleak'.
	return c;
}

/**
 * Returns (optionally creating) parent node of value or root node if there are no slashes
 */
static inline HKEY config_get_parent(struct _Config* c, const char* path, bool create) {
	LSTATUS r;
	HKEY obj = c->root;
	bool close_obj = false;
	REGSAM sam = KEY_READ;
	
	while (obj != NULL) {
		const char* slash = strchr(path, '/');
		if (slash == NULL)
			return obj;
		
		size_t slash_index = slash - path;
		if (slash_index >= JSONPATH_MAX_LEN)
			// Requested path is too long, this is not reasonable thing to request
			return NULL;
		strncpy(c->buffer, path, JSONPATH_MAX_LEN);
		c->buffer[slash_index] = 0;
		
		if (0 != strcmp("Software", c->buffer))
			sam |= KEY_WRITE;
		
		HKEY subkey;
		if (create)
			r = RegCreateKeyExA(obj, c->buffer, 0, NULL, 0, sam, NULL, &subkey, NULL);
		else
			r = RegOpenKeyExA(obj, c->buffer, 0, sam, &subkey);
		if (r != ERROR_SUCCESS)
			return NULL;
		
		if (close_obj)
			RegCloseKey(obj);
		close_obj = true;
		obj = subkey;
		path = &path[slash_index + 1];
	}
	
	return NULL;
}


Config* config_load() {
	// On Windows, this actually reads from registry
	struct _Config* c = config_new();
	if (c == NULL) return NULL;
	c->values = hashmap_new();
	if (c->values == NULL) {
		free(c);
		return NULL;
	}
	
	HKEY hkcu;
	LSTATUS r;
	if ((r = RegOpenCurrentUser(KEY_READ, &hkcu)) != ERROR_SUCCESS) {
		WARN("Failed to open registry: Code %i. Starting with defaults.", r);
		return &c->config;
	}
	c->root = hkcu;
	c->root = config_get_parent(c, "Software/SCController/dummy", true);
	// ^^ Sets root to HKCU/Software/SCController
	return &c->config;
}

Config* config_load_from(int fd, char* error_return, size_t error_limit) {
	LERROR("config_load_from should not be used on Windows");
	return NULL;
}


/** Returns NULL if memory cannot be allocated */
static inline char* internal_string_alloc(struct _Config* c, size_t len) {
	void* data = malloc(sizeof(struct InternalString) + len);
	if (data == NULL) return NULL;
	struct InternalString* s = (struct InternalString*)data;
	s->next = c->giant_memoryleak;
	c->giant_memoryleak = s;
	return &s->value;
}

/** Returns NULL if memory cannot be allocated */
static const char* internalize_string(struct _Config* c, const char* value) {
	size_t len = strlen(value);
	if (len < 1) return NULL;
	char* is = internal_string_alloc(c, len);
	strcpy(is, value);
	return is;
}

config_value_t* config_get_value(struct _Config* c, const char* path, ConfigValueType type) {
	config_value_t* value;
	// First, try to return cached value
	if (hashmap_get(c->values, path, (void*)&value) == MAP_OK)
		return value;
	
	// 2nd, try to read value from registry
	value = NULL;
	HKEY parent = config_get_parent(c, path, false);
	char buffer[BUFFER_SIZE];
	
	if (parent != NULL) {
		LSTATUS r;
		DWORD reg_type;
		DWORD size;
		value = malloc(sizeof(config_value_t));
		if (value == NULL)
			goto config_get_value_fail;								// OOM
		const char* last = last_element(path);
		value->type = type;
		
		switch (type) {
		case CVT_STRING:
		case CVT_STR_ARRAY:
			// retrieve size
			r = RegGetValueA(parent, NULL, last, RRF_RT_REG_SZ | RRF_RT_REG_MULTI_SZ, &reg_type, NULL, &size);
			if (r != ERROR_SUCCESS) {
				// Value doesn't exists, has wrong type or just generally failed to be retrieved
				goto config_get_value_fail;
			} else {
				char* is = internal_string_alloc(c, size);
				if (is == NULL)
					goto config_get_value_fail;
				r = RegGetValueA(parent, NULL, last, RRF_RT_REG_SZ | RRF_RT_REG_MULTI_SZ, &reg_type, is, &size);
				if (r != ERROR_SUCCESS)
					// Something failed. 'is' is internal string and so it should not be deallocated
					goto config_get_value_fail;
				if (type == CVT_STR_ARRAY) {
					// Little bit of processing is needed to split CVT_STR_ARRAY into strings
					// 1st, determine how many items were retrieved
					size_t count = 0;
					size_t len;
					char* pos = is;
					while ((len = strlen(pos)) > 0) {
						pos += len + 1;
						count ++;
					}
					// 2nd, allocate space for all the pointers
					value->v_strar = malloc(sizeof(char*) * (count + 1));
					if (value->v_strar == NULL)
						goto config_get_value_fail;
					// 3rd, store pointers
					size_t i = 0;
					pos = is;
					while ((len = strlen(pos)) > 0) {
						value->v_strar[i] = pos;
						pos += len + 1;
						i ++;
					}
					value->v_strar[count] = NULL;	// terminator
				} else {
					// No processing needed for simple string
					value->v_str = is;
				}
			}
			break;
		case CVT_DOUBLE:
			size = BUFFER_SIZE;
			r = RegGetValueA(parent, NULL, last, RRF_RT_REG_SZ, &reg_type, buffer, &size);
			if (r != ERROR_SUCCESS)
				goto config_get_value_fail;
			errno = 0;
			value->v_double = strtod(buffer, NULL);
			if (errno != 0)
				// parsing failed
				goto config_get_value_fail;
			break;
		case CVT_INT:
		case CVT_BOOL:
			size = sizeof(int64_t);
			r = RegGetValueA(parent, NULL, last, RRF_RT_REG_QWORD, &reg_type, &value->v_int, &size);
			if (r != ERROR_SUCCESS)
				// Value doesn't exists, has wrong type or just generally failed to be retrieved
				goto config_get_value_fail;
			break;
		}
		
		// code reaches here after registry value is sucessfully retrieved
		if (parent != c->root)
			RegCloseKey(parent);
		return value;
	}
	
	// 3rd, give up and just return NULL
config_get_value_fail:
	// code jumps / reaches here if memory cannot t be allocated
	// or if value from registry can't be retrieved.
	free(value);
	if ((parent != NULL) && (parent != c->root))
		RegCloseKey(parent);
	return NULL;
}

static inline config_value_t* config_get_or_create(struct _Config* c, const char* path, ConfigValueType type) {
	config_value_t* value = config_get_value(c, path, type);
	if (value == NULL) {
		value = malloc(sizeof(struct _Config));
			if (value == NULL) return NULL;			// OOM
		if (hashmap_put(c->values, path, (void*)value) != MAP_OK) {
				// another OOM
			free(value);
			return NULL;
		}
		value->type = type;
		value->v_str = NULL;
	}
	return value;
}

/**
 * In very specific case of OOM, config may end with string or string array
 * that has no value stored. This method is called to verify if that's the case
 * and to deallocate and clear such value
 */
static void config_delete_unused(struct _Config* c, const char* path, config_value_t* v) {
	if (v == NULL) return;
	if (v->type == CVT_STRING) {
		if (v->v_str != NULL) return;
	} else if (v->type == CVT_STR_ARRAY) {
		if (v->v_strar != NULL) return;
	} else {
		return;
	}
	// Config value is allocated, but has no string/strar value.
	free(v);
	hashmap_remove(c->values, path);
}

bool config_save(Config* _c) {
	struct _Config* c = container_of(_c, struct _Config, config);
	char buffer[BUFFER_SIZE];
	HashMapIterator it = iter_get(c->values);
	if (it == NULL) return false;		// OOM
	FOREACH(const char*, path, it) {
		LSTATUS r = ERROR_SUCCESS;
		config_value_t* value;
		if (hashmap_get(c->values, path, (void*)&value) != MAP_OK) continue;
		HKEY parent = config_get_parent(c, path, true);
		if (parent == NULL) goto config_save_key_failed;
		const char* last = last_element(path);
		
		switch (value->type) {
		case CVT_STRING:
			r = RegSetKeyValueA(parent, NULL, last, REG_SZ, value->v_str, strlen(value->v_str) + 1);
			break;
		case CVT_DOUBLE:
			// Fun fact: You can't save float into registry
			snprintf(buffer, BUFFER_SIZE, "%f", value->v_double);
			r = RegSetKeyValueA(parent, NULL, last, REG_SZ, buffer, BUFFER_SIZE);
			break;
		case CVT_INT:
		case CVT_BOOL:
			r = RegSetKeyValueA(parent, NULL, last, REG_QWORD, &value->v_int, sizeof(int64_t));
			break;
		case CVT_STR_ARRAY:
			// Little bit of madness
			do {
				size_t total_size = 1;	// 1B for last terminating 0
				for (int i=0; value->v_strar[i] != NULL; i++)
					total_size += strlen(value->v_strar[i]) + 1;
				char* multi_sz_buffer = malloc(total_size);
				char* pos = multi_sz_buffer;
				if (multi_sz_buffer == NULL) {
					// OOM
					goto config_save_key_failed;
				}
				for (int i=0; value->v_strar[i] != NULL; i++) {
					size_t len = strlen(value->v_strar[i]);
					memcpy(pos, value->v_strar[i], len + 1);
					pos += len + 1;
				}
				multi_sz_buffer[total_size + 1] = 0;
				r = RegSetKeyValueA(parent, NULL, last, REG_MULTI_SZ, multi_sz_buffer, total_size);
				free(multi_sz_buffer);
			} while(0);
			break;
		}
		
		if (parent != c->root)
			RegCloseKey(parent);
		if (r == ERROR_SUCCESS)
			continue;
		
config_save_key_failed:
		LERROR("Failed to save %s into registry", path);
		iter_free(it);
		return false;
	}
	iter_free(it);
	return true;
}

const char* config_get(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* value = config_get_value(c, path, CVT_STRING);
	if (value != NULL)
		return value->v_str;
	
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
	if (value != NULL)
		return value->v_int;
	
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
	if (value != NULL)
		return value->v_double;
	
	const struct config_item* def = config_get_default(c, path);
	if ((def != NULL) && (def->type == CVT_DOUBLE)) {
		config_set_int(_c, path, def->v_double);
		return def->v_double;
	}
	
	return 0;
}

size_t config_get_strings(Config* _c, const char* path, const char** target, size_t limit) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* value = config_get_value(c, path, CVT_STR_ARRAY);
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
		for (size_t i=0; (i<limit) && (value->v_strar[i]!=NULL); i++) {
			target[i] = value->v_strar[i];
			j++;
		}
	}
	return j;
}


/** Common part of all config_set-s */
static inline int config_set_common(json_object* parent, json_value_t* value, const char* path) {
	if (value == NULL) return 0;
	if (NULL == json_object_add(parent, last_element(path), value))
		return 0;
	return 1;
}

int config_set(Config* _c, const char* path, const char* value) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* v = config_get_or_create(c, path, CVT_STRING);
	const char* internalized = internalize_string(c, value);
	if ((v == NULL) || (internalized == NULL)) {
		config_delete_unused(c, path, v);
		return 0;							// OOM
	}
	if (v->type != CVT_STRING)
		return -2;
	
	v->v_str = internalized;
	return 1;
}

int config_set_int(Config* _c, const char* path, int64_t value) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* v = config_get_or_create(c, path, CVT_INT);
	if (v == NULL)
		return 0;							// OOM
	if ((v->type != CVT_INT) && (v->type != CVT_BOOL))
		return -2;
	
	v->v_int = value;
	return 1;
}

int config_set_double(Config* _c, const char* path, double value) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* v = config_get_or_create(c, path, CVT_DOUBLE);
	if (v == NULL)
		return 0;							// OOM
	if (v->type != CVT_DOUBLE)
		return -2;
	
	v->v_double = value;
	return 1;
}

int config_set_strings(Config* _c, const char* path, const char** list, ssize_t count) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* v = config_get_or_create(c, path, CVT_STR_ARRAY);
	if (v == NULL)
		return 0;							// OOM
	if (v->type != CVT_STR_ARRAY)
		return -2;
	
	if (count < 0) {
		count = 0;
		while ((count <= MAX_ARRAY_SIZE) && (list[count] != NULL))
			count++;
		if (count == MAX_ARRAY_SIZE)
			return 0;
	}
	
	char** new_arr = malloc(sizeof(char*) * (count + 1));
	if (new_arr == NULL) {
		// OOM
		config_delete_unused(c, path, v);
		return 0;
	}
	for (size_t i=0; i<count; i++) {
		// TODO: This can be optimized so I don't have duplicate "internal" strings
		const char* internalized = internalize_string(c, list[i]);
		if (internalized == NULL) {
			// OOM
			free(new_arr);
			config_delete_unused(c, path, v);
			return 0;
		}
		new_arr[i] = (char*)internalized;
	}
	new_arr[count] = NULL;
	free(v->v_strar);
	v->v_strar = new_arr;
	return 1;
}

#endif // _WIN32
