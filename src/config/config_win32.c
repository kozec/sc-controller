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
#define SUPPORTED_TYPES (RRF_RT_REG_SZ | RRF_RT_REG_MULTI_SZ | RRF_RT_REG_QWORD)


static void config_dealloc(void* _c) {
	struct _Config* c = container_of(_c, struct _Config, config);
	
	if (c->root != NULL)
		RegCloseKey(c->root);
	// Free interned string
	hashmap_free(c->giant_memoryleak);
	// Free values
	HashMapIterator it = iter_get(c->values);
	FOREACH(const char*, path, it) {
		config_value_t* value;
		if (hashmap_get(c->values, path, (void*)&value) != MAP_OK) continue;
		if (value->type == CVT_STR_ARRAY)
			free(value->v_strar);
		free(value);
	}
	iter_free(it);
	hashmap_free(c->values);
	// Free config object
	free(c);
}


/**
 * Returns (optionally creating) parent key of value, or root node if there are no slashes
 * 'buffer' will be overwriten with random data and its size has to be at least JSONPATH_MAX_LEN.
 * if 'root' is NULL, HKEY_CURRENT_USER is assumed.
 */
static HKEY config_get_parent(HKEY root, char* buffer, const char* path, bool create) {
	LSTATUS r;
	HKEY obj = root;
	bool close_obj = false;
	REGSAM sam = KEY_READ;
	
	if (obj == NULL) {
		close_obj = true;
		if ((r = RegOpenCurrentUser(KEY_READ, &obj)) != ERROR_SUCCESS) {
			WARN("Failed to open registry: Code %i.", r);
			return NULL;
		}
	}
	
	while (obj != NULL) {
		const char* slash = strchr(path, '/');
		if (slash == NULL)
			return obj;
		
		size_t slash_index = slash - path;
		if (slash_index >= JSONPATH_MAX_LEN) {
			// Requested path is too long, this is not reasonable thing to request
			return NULL;
		}
		strncpy(buffer, path, JSONPATH_MAX_LEN);
		buffer[slash_index] = 0;
		
		if (0 != strcmp("Software", buffer))
			sam |= KEY_WRITE;
		
		HKEY subkey;
		if (create) {
			r = RegCreateKeyExA(obj, buffer, 0, NULL, 0, sam, NULL, &subkey, NULL);
			if (r != ERROR_SUCCESS) {
				char* errstr;
				FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
								NULL, r, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
								(void*)&errstr, 0, NULL);
				WARN("Failed to create registry key: %i: %s", r, errstr);
				LocalFree(errstr);
				return NULL;
			}
		} else {
			r = RegOpenKeyExA(obj, buffer, 0, sam, &subkey);
			if (r != ERROR_SUCCESS)
				return NULL;
		}
		
		if (close_obj)
			RegCloseKey(obj);
		close_obj = true;
		obj = subkey;
		path = &path[slash_index + 1];
	}
	
	return NULL;
}

HKEY config_make_subkey(HKEY root, const char* path) {
	char buffer[JSONPATH_MAX_LEN];
	StrBuilder* sb = strbuilder_new();
	
	strbuilder_add(sb, path);
	strbuilder_replace(sb, '\\', '/');
	strbuilder_rstrip(sb, "/");
	strbuilder_add(sb, "/dummy");
	if (strbuilder_failed(sb))
		return NULL;
	
	HKEY rv = config_get_parent(root, buffer, strbuilder_get_value(sb), true);
	strbuilder_free(sb);
	return rv;
}


static inline struct _Config* config_new() {
	struct _Config* c = malloc(sizeof(struct _Config));
	if (c == NULL) return NULL;
	RC_INIT(&c->config, &config_dealloc);
	c->defaults = DEFAULTS;
	c->root = NULL;
	
	c->giant_memoryleak = hashmap_new();
	// About giant_memoryleak... Config guarantees that all strings returned by
	// it are stored in memory at least until Config object is deallocated.
	// To be able to deallocate them eventyally, all strings are stored
	// as linked-list in 'giant_memoryleak'.
	
	c->values = hashmap_new();
	if ((c->values == NULL) || (c->giant_memoryleak == NULL)) {
		hashmap_free(c->values);
		hashmap_free(c->giant_memoryleak);
		free(c);
		return NULL;
	}
	
	c->root = NULL;
	return c;
}


Config* config_load() {
	// On Windows, this actually reads from registry
	struct _Config* c = config_new();
	if (c == NULL) return NULL;
	
	c->root = config_get_parent(NULL, c->buffer, "Software/SCController/dummy", true);
	// ^^ Sets root to HKCU/Software/SCController
	if (c->root == NULL) {
		config_dealloc(c);
		return NULL;
	}
	return &c->config;
}


Config* config_load_from_key(const char* path, char* error_return) {
	if (error_return != NULL) *error_return = 0;
	
	struct _Config* c = config_new();
	if (c == NULL) return NULL;
	if (strlen(path) >= JSONPATH_MAX_LEN - 10) {
		strcpy(error_return, "Path is too long");
		config_dealloc(c);
		return NULL;
	}
	
	snprintf(c->buffer, JSONPATH_MAX_LEN, "%s/d", path);
	c->root = config_get_parent(NULL, c->buffer, c->buffer, true);
	if (c->root == NULL) {
		if (error_return != NULL)
			strcpy(error_return, "Failed to create registry key");
		config_dealloc(c);
		return NULL;
	}
	
	return &c->config;
}

/** Returns NULL if memory cannot be allocated */
static const char* internalize_string(struct _Config* c, const char* value) {
	const char* k = hashmap_get_key(c->giant_memoryleak, value);
	if (k == NULL) {
		hashmap_put(c->giant_memoryleak, value, (void*)1);
		k = hashmap_get_key(c->giant_memoryleak, value);
	}
	return k;
}

DLL_EXPORT bool config_is_parent(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	snprintf(c->buffer, JSONPATH_MAX_LEN, "%s/d", path);
	HKEY key = config_get_parent(c->root, c->buffer, c->buffer, false);
	return (key != NULL);
}

config_value_t* config_get_value(struct _Config* c, const char* path, ConfigValueType type) {
	config_value_t* value;
	// First, try to return cached value
	if (hashmap_get(c->values, path, (void*)&value) == MAP_OK)
		return value;
	
	// 2nd, try to read value from registry
	HKEY subkey;
	value = NULL;
	REGSAM sam = KEY_READ;
	HKEY parent = config_get_parent(c->root, c->buffer, path, false);
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
		case CVT_OBJECT:
			// Just check if key exists, return NULL if it doesn't
			r = RegOpenKeyExA(c->root, path, 0, sam, &subkey);
			if (r != ERROR_SUCCESS)
				return NULL;
			RegCloseKey(subkey);
			break;
		case CVT_STRING:
		case CVT_STR_ARRAY:
			// retrieve size
			r = RegGetValueA(parent, NULL, last, RRF_RT_REG_SZ | RRF_RT_REG_MULTI_SZ, &reg_type, NULL, &size);
			if (r != ERROR_SUCCESS) {
				// Value doesn't exists, has wrong type or just generally failed to be retrieved
				goto config_get_value_fail;
			} else {
				char* copy = malloc(size);
				if (copy == NULL)
					goto config_get_value_fail;
				r = RegGetValueA(parent, NULL, last, RRF_RT_REG_SZ | RRF_RT_REG_MULTI_SZ, &reg_type, copy, &size);
				if (r != ERROR_SUCCESS) {
					free(copy);
					goto config_get_value_fail;
				}
				if (type == CVT_STR_ARRAY) {
					// Little bit of processing is needed to split CVT_STR_ARRAY into strings
					// 1st, determine how many items were retrieved
					size_t count = 0;
					size_t len;
					char* pos = copy;
					while ((len = strlen(pos)) > 0) {
						pos += len + 1;
						count ++;
					}
					// 2nd, allocate space for all the pointers
					value->v_strar = malloc(sizeof(char*) * (count + 1));
					if (value->v_strar == NULL) {
						free(copy);
						goto config_get_value_fail;
					}
					// 3rd, copy values & store pointers
					size_t i = 0;
					pos = copy;
					while ((len = strlen(pos)) > 0) {
						pos[len] = 0;
						value->v_strar[i] = (char*)internalize_string(c, pos);
						if (value->v_strar[i] == NULL) {
							// OOM
							free(copy);
							free(value->v_strar);
							value->v_strar = NULL;
							goto config_get_value_fail;
						}
						pos += len + 1;
						i ++;
					}
					value->v_strar[count] = NULL;	// terminator
				} else {
					// No processing needed for simple string
					value->v_str = internalize_string(c, copy);
					if (value->v_str == NULL) {
						free(copy);
						goto config_get_value_fail;
					}
				}
				free(copy);
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
		case CVT_INVALID:
			return NULL;
		}
		
		// code reaches here after registry value is sucessfully retrieved
		if (parent != c->root)
			RegCloseKey(parent);
		if (hashmap_put(c->values, path, (void*)value) != MAP_OK) {
			// OOM
			free(value);
			return NULL;
		}
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
	if (config_get_parent(c->root, c->buffer, path, true) == NULL)
		return NULL;		// OOM
	config_value_t* value = config_get_value(c, path, type);
	if (value == NULL) {
		const struct config_item* def = config_get_default(c, path);
		value = malloc(sizeof(config_value_t));
		if (value == NULL) return NULL;			// OOM
		if (hashmap_put(c->values, path, (void*)value) != MAP_OK) {
			// another OOM
			free(value);
			return NULL;
		}
		
		value->type = (def == NULL) ? type : def->type;
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
		HKEY parent = config_get_parent(c->root, c->buffer, path, true);
		if (parent == NULL) goto config_save_key_failed;
		const char* last = last_element(path);
		
		switch (value->type) {
		case CVT_STRING:
			r = RegSetKeyValueA(parent, NULL, last, REG_SZ, value->v_str, strlen(value->v_str) + 1);
			break;
		case CVT_DOUBLE:
			// Fun fact: You can't save float into registry
			LOG("Saving double %s", path);
			snprintf(buffer, BUFFER_SIZE, "%g", value->v_double);
			r = RegSetKeyValueA(parent, NULL, last, REG_SZ, buffer, strlen(buffer) + 1);
			break;
		case CVT_INT:
		case CVT_BOOL:
			LOG("Saving int %s", path);
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
				multi_sz_buffer[total_size - 1] = 0;
				r = RegSetKeyValueA(parent, NULL, last, REG_MULTI_SZ, multi_sz_buffer, total_size);
				free(multi_sz_buffer);
			} while(0);
			break;
		case CVT_OBJECT:
			// Not saved
		case CVT_INVALID:
			// Not possible
			break;
		}
		
		if (parent != c->root)
			RegCloseKey(parent);
		if (r == ERROR_SUCCESS)
			continue;
		
		char* err;
		if (!FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM,
					NULL, r,
					MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), // default language
					(LPTSTR) &err,
					0, NULL))
			goto config_save_key_failed;
		
		LERROR("Failed to save %s into registry: %s", path, err);
		free(err);
		iter_free(it);
		return false;
		
config_save_key_failed:
		LERROR("Failed to save %s into registry", path);
		iter_free(it);
		return false;
	}
	iter_free(it);
	return true;
}


ConfigValueType config_get_type(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	const struct config_item* def = config_get_default(c, path);
	if (def != NULL) return def->type;
	
	config_value_t* value;
	if (hashmap_get(c->values, path, (void*)&value) == MAP_OK)
		return value->type;
	
	HKEY parent = config_get_parent(c->root, c->buffer, path, false);
	if (parent == NULL)
		return CVT_INVALID;
	
	const char* last = last_element(path);
	LSTATUS r;
	HKEY subkey;
	REGSAM sam = KEY_READ;
	r = RegOpenKeyExA(parent, last, 0, sam, &subkey);
	if (r == ERROR_SUCCESS) {
		RegCloseKey(subkey);
		return CVT_OBJECT;
	}
	
	DWORD reg_type;
	const DWORD flags = SUPPORTED_TYPES;
	r = RegGetValueA(parent, NULL, last, flags, &reg_type, NULL, NULL);
	ConfigValueType type = CVT_INVALID;
	if (r == ERROR_SUCCESS) {
		switch (reg_type) {
		case REG_SZ:
			type = CVT_STRING;
			break;
		case REG_QWORD:
			type = CVT_INT;
			break;
		}
	}
	if (parent != c->root)
		RegCloseKey(parent);
	
	return type;
}


const char* config_get(Config* _c, const char* path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* value = config_get_value(c, path, CVT_STRING);
	if (value != NULL) {
		return value->v_str;
	}
	
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
	value = config_get_value(c, path, CVT_INT);
	if (value != NULL)
		return value->v_int;
	
	const struct config_item* def = config_get_default(c, path);
	if ((def != NULL) && (def->type == CVT_DOUBLE)) {
		config_set_double(_c, path, def->v_double);
		return def->v_double;
	}
	
	return 0;
}

static ssize_t config_enum_keys(struct _Config* c, HKEY key, const char** target, ssize_t limit, bool include_values) {
	DWORD max_len, max_value_len;
	DWORD subkey_cnt, value_cnt;
	// Query data
	LSTATUS r = RegQueryInfoKeyA(key, NULL, NULL, NULL,
			&subkey_cnt, &max_len, NULL,
			&value_cnt, &max_value_len, NULL, NULL, NULL
	);
	
	// Compute size and allocate buffer
	if (include_values && (max_value_len > max_len))
		max_len = max_value_len;
	if ((r != ERROR_SUCCESS) || (max_value_len >= ULONG_MAX - 1))
		return -1;
	char* buffer = malloc(++ max_len);
	if (buffer == NULL)
		return -1;
	
	// Read keys
	ssize_t j = 0;
	for (DWORD i=0; i<subkey_cnt; i++) {
		DWORD len = max_len;
		r = RegEnumKeyEx(key, i, buffer, &len, NULL, NULL, NULL, NULL);
		if (r == ERROR_SUCCESS) {
			if (j >= limit) {
				j = -2;
				break;
			}
			buffer[len] = 0;
			target[j] = internalize_string(c, buffer);
			if (target[j] == NULL) {
				j = 0;
				break;
			}
			j++;
		}
	}
	
	// Read values
	if (include_values) {
		for (DWORD i=0; i<value_cnt; i++) {
			DWORD len = max_len;
			DWORD type;
			r = RegEnumValueA(key, i, buffer, &len, NULL, &type, NULL, NULL);
			if ((r == ERROR_SUCCESS) && (type | SUPPORTED_TYPES)) {
				if (j >= limit) {
					j = -2;
					break;
				}
				buffer[len] = 0;
				target[j] = internalize_string(c, buffer);
				if (target[j] == NULL) {
					j = 0;
					break;
				}
				j++;
			}
		}
	}
	
	// Free memory
	free(buffer);
	return j;
}

ssize_t config_get_strings(Config* _c, const char* path, const char** target, ssize_t limit) {
	struct _Config* c = container_of(_c, struct _Config, config);
	config_value_t* value = config_get_value(c, path, CVT_STR_ARRAY);
	ssize_t j = 0;
	if (value == NULL) {
		// Two possibilities why code reaches here;
		// - Value in registry is not yet set and default should be used
		// - Path represents key
		// 2nd possibility is check 1st and if key is not found, default
		// value is tried as fallback.
		HKEY parent = config_get_parent(c->root, c->buffer, path, false);
		if (parent != NULL) {
			const char* last = last_element(path);
			HKEY key;
			LSTATUS r;
			REGSAM sam = KEY_READ;
			r = RegOpenKeyExA(parent, last, 0, sam, &key);
			if (r == ERROR_SUCCESS) {
				ssize_t rv = config_enum_keys(c, key, target, limit, true);
				RegCloseKey(key);
				return rv;
			}
		}
		
		// Path doesn't represents key, go for default value
		const struct config_item* def = config_get_default(c, path);
		if ((def == NULL) || (def->type != CVT_STR_ARRAY))
			return 0;
		if (def->v_strar != NULL) {
			for (size_t i=0; (i<SSIZE_MAX) && (def->v_strar[i]!=NULL); i++) {
				if (j >= limit) return -2;
				target[i] = def->v_strar[i];
				j++;
			}
		}
	} else {
		for (size_t i=0; (i<SSIZE_MAX) && (value->v_strar[i]!=NULL); i++) {
			if (j >= limit) return -2;
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
	if (v->type == CVT_DOUBLE)
		return config_set_double(_c, path, (double)value);
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
	if ((v->type == CVT_INT) || (v->type == CVT_BOOL))
		return config_set_int(_c, path, (int64_t)value);
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

ssize_t config_get_controllers(Config* _c, const char** target, ssize_t limit) {
	struct _Config* c = container_of(_c, struct _Config, config);
	HKEY key = config_get_parent(c->root, c->buffer, "/devices/dummy", true);
	if (key == NULL) return 0;
	
	ssize_t rv = config_enum_keys(c, key, target, limit, false);
	RegCloseKey(key);
	return rv;
}

Config* config_get_controller_config(Config* _c, const char* id, char* error_return) {
	struct _Config* c = container_of(_c, struct _Config, config);
	char* path = strbuilder_fmt("/devices/%s/dummy", id);
	if (path == NULL) return NULL;
	HKEY key = config_get_parent(c->root, c->buffer, path, false);
	free(path);
	if (key == NULL) {
		if (error_return != NULL)
			strcpy(error_return, "Registry key not found");
		return NULL;
	}
	
	struct _Config* rv = config_new();
	if (rv == NULL) {
		RegCloseKey(key);
		return NULL;
	}
	rv->defaults = CONTROLLER_DEFAULTS;
	rv->root = key;
	return &rv->config;
}

Config* config_create_controller_config(Config* _c, const char* id, char* error_return) {
	struct _Config* c = container_of(_c, struct _Config, config);
	char* path = strbuilder_fmt("/devices/%s/dummy", id);
	if (path == NULL) return NULL;
	HKEY key = config_get_parent(c->root, c->buffer, path, true);
	free(path);
	if (key == NULL) return NULL;
	RegCloseKey(key);
	return config_get_controller_config(_c, id, error_return);
}

int config_delete_key(Config* _c, const char* path) {
	printf("Should delete key: %s\n", path);
	return 1;
}

#else	// _WIN32
	#error "config_win32.c included outside of Windows"
#endif

