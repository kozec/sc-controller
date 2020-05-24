/**
 * Copyright (c) 2016, Peter Vanusanik
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * * Redistributions of source code must retain the above copyright notice, this
 *   list of conditions and the following disclaimer.
 *
 * * Redistributions in binary form must reproduce the above copyright notice,
 *   this list of conditions and the following disclaimer in the documentation
 *   and/or other materials provided with the distribution.
 *
 * * Neither the name of AOJLS nor the names of its
 *   contributors may be used to endorse or promote products derived from
 *   this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "scc/utils/aojls.h"

#include <setjmp.h>
#include <float.h>

#define MAX_DOUBLE_LENGTH (4 + DBL_MANT_DIG + (-DBL_MIN_EXP))

#define FAIL_ENOMEM 1
#define FAIL_EXPECTED_PAIR 2
#define FAIL_EXPECTED_VALUE 3
#define FAIL_EXPECTED_EOO 4
#define FAIL_EXPECTED_EOL 5

// private struct implementations

typedef struct _aojls_alloc_node _aojls_alloc_node_t;

struct _aojls_alloc_node {
	struct _aojls_alloc_node* next;
};

struct json_value{
	_aojls_alloc_node_t anode;
	json_type_t         type;
	aojls_ctx_t*		ctx;
};

struct json_object {
	json_value_t   self;
	size_t         allocated;
	size_t		   n;
	char**		   keys;
	json_value_t** values;
};

struct json_array {
	json_value_t   self;
	size_t         allocated;
	size_t		   n;
	json_value_t** elements;
};

struct json_string {
	json_value_t self;
	char*		 value; // null terminated, always
};

struct json_number {
	json_value_t self;
	double       value;
};

struct json_boolean {
	json_value_t self;
	bool		 value;
};

struct json_null {
	json_value_t self;
};

typedef struct char_node {
	struct char_node* next;
	char*  data;
} char_node_t;

struct aojls_ctx {
	_aojls_alloc_node_t* snode;
	_aojls_alloc_node_t* enode;

	json_value_t*        result;
	bool				 failed;

	char_node_t* ssnode;
	char_node_t* esnode;
};

// json value

json_type_t json_get_type(json_value_t* value) {
	if (value == NULL)
		return INVALID;
	return value->type;
}

json_object* json_as_object(json_value_t* value) {
	if (value != NULL && value->type == JS_OBJECT)
		return (json_object*)value;
	else
		return NULL;
}

json_array* json_as_array(json_value_t* value) {
	if (value != NULL && value->type == JS_ARRAY)
		return (json_array*)value;
	else
		return NULL;
}

double json_as_number(json_value_t* value, bool* correct_type) {
	if (value != NULL && value->type == JS_NUMBER) {
		if (correct_type != NULL)
			*correct_type = true;
		return ((json_number*)value)->value;
	} else
		if (correct_type != NULL)
			*correct_type = false;
	return 0;
}

char* json_as_string(json_value_t* value) {
	if (value != NULL && value->type == JS_STRING)
		return ((json_string*)value)->value;
	else
		return NULL;
}

bool json_as_bool(json_value_t* value, bool* correct_type) {
	if (value != NULL && value->type == JS_BOOL) {
		if (correct_type != NULL)
			*correct_type = true;
		return ((json_boolean*)value)->value;
	} else
		if (correct_type != NULL)
			*correct_type = false;
	return false;
}

bool json_is_null(json_value_t* value) {
	if (value != NULL && value->type == JS_NULL)
		return true;
	else
		return false;
}

// auxiliary functions

static void append_to_context(aojls_ctx_t* ctx, json_value_t* v) {
	if (v == NULL || ctx == NULL) {
		if (ctx != NULL)
			ctx->failed = true;
		return;
	}
	if (ctx->enode == NULL) {
		ctx->snode = &v->anode;
		ctx->enode = &v->anode;
	} else {
		ctx->enode->next = &v->anode;
		ctx->enode = &v->anode;
	}
	v->anode.next = NULL;
	v->ctx = ctx;
}

static char* append_string(aojls_ctx_t* ctx, const char* string, size_t len) {
	if (ctx == NULL || string == NULL) {
		if (ctx != NULL)
			ctx->failed = true;
		return NULL;
	}

	char* cpy = (char*)malloc((len+1) * sizeof(char));
	if (cpy == NULL) {
		ctx->failed = true;
		return NULL;
	}
	cpy[len] = '\0';
	char_node_t* cnode = (char_node_t*)calloc(1, sizeof(char_node_t));
	if (cnode == NULL) {
		free(cpy);
		ctx->failed = true;
		return NULL;
	}

	memcpy(cpy, string, len);
	cnode->data = cpy;

	if (ctx->esnode == NULL) {
		ctx->esnode = cnode;
		ctx->ssnode = cnode;
	} else {
		ctx->esnode->next = cnode;
		ctx->esnode = cnode;
	}

	return cpy;
}

// json object

json_object* json_make_object(aojls_ctx_t* ctx) {
	if (ctx == NULL)
		return NULL;
	json_object* o = (json_object*)calloc(1, sizeof(json_object));
	if (o == NULL) {
		ctx->failed = true;
		return NULL;
	}

	o->self.type = JS_OBJECT;
	o->allocated = AOJLS_OBJECT_START_ALLOC_SIZE;
	o->n = 0;
	o->keys = (char**)malloc(o->allocated*sizeof(char*));
	if (o->keys == NULL) {
		free(o);
		ctx->failed = true;
		return NULL;
	}
	o->values = (json_value_t**)malloc(o->allocated*sizeof(json_value_t*));
	if (o->values == NULL) {
		free(o->keys);
		free(o);
		ctx->failed = true;
		return NULL;
	}

	append_to_context(ctx, &o->self);
	return o;
}

json_object* json_object_add(json_object* o, const char* key, json_value_t* value) {
	if (key == NULL)
		return NULL;
	return json_object_nadd(o, key, strlen(key), value);
}

json_object* json_object_nadd(json_object* o, const char* key, size_t len, json_value_t* value) {
	if (o == NULL || value == NULL || key == NULL) {
		if (o != NULL)
			o->self.ctx->failed = true;
		return NULL;
	}

	if (o->n == o->allocated) {
		// reallocate and increase the size
		size_t allocated = o->allocated * 2;
		char** keys = (char**)realloc(o->keys, allocated*sizeof(char*));
		if (keys == NULL) {
			o->self.ctx->failed = true;
			return NULL;
		}
		json_value_t** values = (json_value_t**)realloc(o->values, allocated*sizeof(json_value_t*));
		if (values == NULL) {
			free(keys);
			o->self.ctx->failed = true;
			return NULL;
		}
		o->allocated = allocated;
		o->keys = keys;
		o->values = values;
	}

	key = append_string(o->self.ctx, key, len);
	if (key == NULL) {
		o->self.ctx->failed = true;
		return NULL;
	}

	o->keys[o->n] = (char*)key;
	o->values[o->n] = value;
	++o->n;

	return o;
}

json_object* json_object_set(json_object* o, const char* key, json_value_t* value) {
	if (o == NULL || value == NULL || key == NULL) {
		if (o != NULL)
			o->self.ctx->failed = true;
		return NULL;
	}

	for (size_t i=0; i<o->n; i++) {
		if (0 == strcmp(o->keys[i], key)) {
			o->values[i] = value;
			return o;
		}
	}
	
	return json_object_nadd(o, key, strlen(key), value);
}

json_object* json_object_set_undefined(json_object* o, const char* key) {
	if (o == NULL || key == NULL) {
		if (o != NULL)
			o->self.ctx->failed = true;
		return NULL;
	}

	for (size_t i=0; i<o->n; i++) {
		if (0 == strcmp(o->keys[i], key)) {
			if (o->n > 1) {
				for (size_t j=i; j<o->n - 1; j++) {
					o->keys[j] = o->keys[j+1];
					o->values[j] = o->values[j+1];
				}
			}
			--o->n;
			return o;
		}
	}
	return 0;
}

size_t json_object_numkeys(json_object* o) {
	if (o == NULL)
		return 0;
	return o->n;
}

const char* json_object_get_key(json_object* o, size_t i) {
	if (o == NULL || i >= o->n)
		return NULL;
	return o->keys[i];
}

json_value_t* json_object_get_object_as_value(json_object* o, const char* key) {
	if (o == NULL || key == NULL) {
		if (o != NULL)
			o->self.ctx->failed = true;
		return NULL;
	}
	for (size_t i=0; i<o->n; i++) {
		if (strcmp(key, o->keys[i]) == 0) {
			return o->values[i];
		}
	}
	return NULL; // not found
}

json_object* json_object_get_object(json_object* o, const char* key) {
	json_value_t* value = json_object_get_object_as_value(o, key);
	if (value == NULL) {
		return NULL;
	}
	return json_as_object(value);
}

json_array* json_object_get_array(json_object* o, const char* key) {
	json_value_t* value = json_object_get_object_as_value(o, key);
	if (value == NULL) {
		return NULL;
	}
	return json_as_array(value);
}

double json_object_get_double(json_object* o, const char* key, bool* valid) {
	json_value_t* value = json_object_get_object_as_value(o, key);
	if (value == NULL) {
		if (valid != NULL)
			*valid = false;
		return 0;
	}
	return json_as_number(value, valid);
}

double json_object_get_double_default(json_object* o, const char* key, double defval) {
	bool valid = false;
	double result = json_object_get_double(o, key, &valid);
	if (!valid)
		result = defval;
	return result;
}

char* json_object_get_string(json_object* o, const char* key) {
	json_value_t* value = json_object_get_object_as_value(o, key);
	if (value == NULL) {
		return NULL;
	}
	return json_as_string(value);
}

char* json_object_get_string_default(json_object* o, const char* key, char* defval) {
	char* value = json_object_get_string(o, key);
	if (value == NULL)
		value = defval;
	return value;
}

bool json_object_get_bool(json_object* o, const char* key, bool* valid) {
	json_value_t* value = json_object_get_object_as_value(o, key);
	if (value == NULL) {
		if (valid != NULL)
			*valid = false;
		return 0;
	}
	return json_as_bool(value, valid);
}

bool json_object_get_bool_default(json_object* o, const char* key, bool defval) {
	bool valid = false;
	bool result = json_object_get_bool(o, key, &valid);
	if (!valid)
		result = defval;
	return result;
}

bool json_object_is_null(json_object* o, const char* key) {
	json_value_t* value = json_object_get_object_as_value(o, key);
	return json_is_null(value);
}

// array

json_array* json_make_array(aojls_ctx_t* ctx) {
	if (ctx == NULL)
		return NULL;
	json_array* o = (json_array*)calloc(1, sizeof(json_array));
	if (o == NULL) {
		ctx->failed = true;
		return NULL;
	}

	o->self.type = JS_ARRAY;
	o->allocated = AOJLS_ARRAY_START_ALLOC_SIZE;
	o->n = 0;
	o->elements = (json_value_t**)malloc(o->allocated*sizeof(json_value_t*));
	if (o->elements == NULL) {
		free(o);
		ctx->failed = true;
		return NULL;
	}

	append_to_context(ctx, &o->self);
	return o;
}

json_array* json_array_add(json_array* a, json_value_t* value) {
	if (a == NULL || value == NULL) {
		if (a != NULL)
			a->self.ctx->failed = true;
		return NULL;
	}

	if (a->n == a->allocated) {
		// reallocate and increase the size
		size_t allocated = a->allocated * 2;
		json_value_t** elements = (json_value_t**)realloc(a->elements, allocated*sizeof(json_value_t*));
		if (elements == NULL) {
			a->self.ctx->failed = true;
			return NULL;
		}
		a->allocated = allocated;
		a->elements = elements;
	}

	a->elements[a->n] = value;
	++a->n;

	return a;
}

size_t json_array_size(json_array* a) {
	if (a == NULL)
		return 0;
	return a->n;
}

json_value_t* json_array_get(json_array* a, size_t i) {
	if (a == NULL)
		return NULL;
	if (i >= a->n)
		return NULL;
	return a->elements[i];
}

json_object* json_array_get_object(json_array* a, size_t key) {
	json_value_t* value = json_array_get(a, key);
	if (value == NULL) {
		return NULL;
	}
	return json_as_object(value);
}

json_array* json_array_get_array(json_array* a, size_t key) {
	json_value_t* value = json_array_get(a, key);
	if (value == NULL) {
		return NULL;
	}
	return json_as_array(value);
}

double json_array_get_double(json_array* a, size_t key, bool* valid) {
	json_value_t* value = json_array_get(a, key);
	if (value == NULL) {
		if (valid != NULL)
			*valid = false;
		return 0;
	}
	return json_as_number(value, valid);
}

double json_array_get_double_default(json_array* a, size_t key, double defval) {
	bool valid = false;
	double result = json_array_get_double(a, key, &valid);
	if (!valid)
		result = defval;
	return result;
}

char* json_array_get_string(json_array* a, size_t key) {
	json_value_t* value = json_array_get(a, key);
	if (value == NULL) {
		return NULL;
	}
	return json_as_string(value);
}

char* json_array_get_string_default(json_array* a, size_t key, char* defval) {
	char* value = json_array_get_string(a, key);
	if (value == NULL)
		value = defval;
	return value;
}

bool json_array_get_bool(json_array* a, size_t key, bool* valid) {
	json_value_t* value = json_array_get(a, key);
	if (value == NULL) {
		if (valid != NULL)
			*valid = false;
		return 0;
	}
	return json_as_bool(value, valid);
}

bool json_array_get_bool_default(json_array* a, size_t key, bool defval) {
	bool valid = false;
	bool result = json_array_get_bool(a, key, &valid);
	if (!valid)
		result = defval;
	return result;
}

bool json_array_is_null(json_array* a, size_t key) {
	json_value_t* value = json_array_get(a, key);
	return json_is_null(value);
}

// primitives

json_string* json_from_string(aojls_ctx_t* ctx, const char* string) {
	if (ctx == NULL || string == NULL) {
		if (ctx != NULL)
			ctx->failed = true;
		return NULL;
	}
	json_string* o = (json_string*)calloc(1, sizeof(json_string));
	if (o == NULL) {
		ctx->failed = true;
		return NULL;
	}
	char* copy = append_string(ctx, string, strlen(string));
	if (copy == NULL) {
		free(o);
		ctx->failed = true;
		return NULL;
	}

	o->self.type = JS_STRING;
	o->value = copy;
	append_to_context(ctx, &o->self);
	return o;
}

json_number* json_from_number(aojls_ctx_t* ctx, double number) {
	if (ctx == NULL) {
		return NULL;
	}
	json_number* o = (json_number*)calloc(1, sizeof(json_number));
	if (o == NULL) {
		ctx->failed = true;
		return NULL;
	}
	o->self.type = JS_NUMBER;
	o->value = number;

	append_to_context(ctx, &o->self);
	return o;
}

json_boolean* json_from_boolean(aojls_ctx_t* ctx, bool b) {
	if (ctx == NULL)
		return NULL;
	json_boolean* o = (json_boolean*)calloc(1, sizeof(json_boolean));
	if (o == NULL) {
		ctx->failed = true;
		return NULL;
	}
	o->self.type = JS_BOOL;
	o->value = b;

	append_to_context(ctx, &o->self);
	return o;
}

json_null* json_make_null(aojls_ctx_t* ctx) {
	if (ctx == NULL)
		return NULL;
	json_null* o = (json_null*)calloc(1, sizeof(json_null));
	if (o == NULL) {
		ctx->failed = true;
		return NULL;
	}
	o->self.type = JS_NULL;

	append_to_context(ctx, &o->self);
	return o;
}

// context

aojls_ctx_t* json_make_context() {
	return (aojls_ctx_t*) calloc(1, sizeof(aojls_ctx_t));
}

bool json_context_error_happened(aojls_ctx_t* ctx) {
	return ctx->failed;
}

json_value_t* json_context_get_result(aojls_ctx_t* ctx) {
	if (ctx == NULL)
		return NULL;
	return ctx->result;
}

void json_free_context(aojls_ctx_t* ctx) {
	if (ctx == NULL)
		return;

	_aojls_alloc_node_t* anode = ctx->snode;
	while (anode != NULL) {
		_aojls_alloc_node_t* node = anode;
		anode = node->next;

		json_value_t* v = (json_value_t*)node;
		if (v->type == JS_OBJECT || v->type == JS_ARRAY) {
			if (v->type == JS_OBJECT) {
				json_object* o = json_as_object(v);
				free(o->keys);
				free(o->values);
			} else {
				json_array* a = json_as_array(v);
				free(a->elements);
			}
		}

		free(node);
	}

	char_node_t* cnode = ctx->ssnode;
	while (cnode != NULL) {
		char_node_t* node = cnode;
		cnode = node->next;
		free(node->data);
		free(node);
	}

	free(ctx);
}

// serialization

typedef struct {
	char* data;
	size_t offset;
	size_t len;
} string_buffer_data_t;

static bool string_writer_function(const char* buffer, size_t len, void* writer_data) {
	string_buffer_data_t* wd = (string_buffer_data_t*)writer_data;

	if (wd->offset + len >= wd->len) {
		size_t addendum = wd->len*2;
		if (addendum == 0)
			addendum = 2048;
		char* rb = (char*)realloc(wd->data, addendum);
		if (rb == NULL) {
			return false;
		}
		wd->data = rb;
		wd->len = addendum;
		return string_writer_function(buffer, len, writer_data);
	}

	memcpy(wd->data+wd->offset, buffer, len);
	wd->offset += len;

	return true;
}

static bool do_serialize_string(const char* string, aojls_serialization_prefs* prefs) {
	size_t len = strlen(string);
	if (!prefs->writer("\"", 1, prefs->writer_data))
		return false;
	for (size_t i=0; i<len; i++) {
		if (string[i] == '\n') {
			if (!prefs->writer("\\n", 2, prefs->writer_data))
				return false;
		} else if (string[i] == '\r') {
			if (!prefs->writer("\\r", 2, prefs->writer_data))
				return false;
		} else if (string[i] == '\t') {
			if (!prefs->writer("\\t", 2, prefs->writer_data))
				return false;
		} else if (string[i] == '\f') {
			if (!prefs->writer("\\f", 2, prefs->writer_data))
				return false;
		} else if (string[i] == '\b') {
			if (!prefs->writer("\\b", 2, prefs->writer_data))
				return false;
		} else if (string[i] == '/') {
			if (!prefs->writer("\\/", 2, prefs->writer_data))
				return false;
		} else if (string[i] == '\\') {
			if (!prefs->writer("\\\\", 2, prefs->writer_data))
				return false;
		} else if (string[i] == '\"') {
				if (!prefs->writer("\\\"", 2, prefs->writer_data))
					return false;
		} else {
			if (!prefs->writer(string+i, 1, prefs->writer_data))
				return false;
		}
	}
	if (!prefs->writer("\"", 1, prefs->writer_data))
		return false;
	return true;
}

static bool do_serialize(json_value_t* value, aojls_serialization_prefs* prefs,
		const char* perlinsert, const char* eol, size_t level) {
	if (value == NULL)
		return false;

	switch (json_get_type(value)) {
	case JS_OBJECT: {
		if (!prefs->writer("{", 1, prefs->writer_data))
			return false;
		if (!prefs->writer(eol, strlen(eol), prefs->writer_data))
			return false;

		size_t nl = level + 1;
		json_object* o = json_as_object(value);
		size_t keys = json_object_numkeys(o);

		for (size_t k=0; k<keys; k++) {
			for (size_t i=0; i<nl; i++) {
				if (!prefs->writer(perlinsert, strlen(perlinsert), prefs->writer_data))
					return false;
			}

			const char* key = json_object_get_key(o, k);
			if (!do_serialize_string(key, prefs))
				return false;
			if (prefs->pretty) {
				if (!prefs->writer(" : ", 3, prefs->writer_data))
					return false;
			} else {
				if (!prefs->writer(":", 1, prefs->writer_data))
					return false;
			}

			json_value_t* value = json_object_get_object_as_value(o, key);
			if (!do_serialize(value, prefs, perlinsert, eol, nl))
				return false;

			if (k != keys-1) {
				if (prefs->pretty) {
					if (!prefs->writer(", ", 2, prefs->writer_data))
						return false;
				} else {
					if (!prefs->writer(",", 1, prefs->writer_data))
						return false;
				}
			}

			if (!prefs->writer(eol, strlen(eol), prefs->writer_data))
				return false;
		}

		for (size_t i=0; i<level; i++) {
			if (!prefs->writer(perlinsert, strlen(perlinsert), prefs->writer_data))
				return false;
		}
		if (!prefs->writer("}", 1, prefs->writer_data))
			return false;
		return true;
	}
	case JS_ARRAY: {
		if (!prefs->writer("[", 1, prefs->writer_data))
					return false;
		if (!prefs->writer(eol, strlen(eol), prefs->writer_data))
			return false;

		size_t nl = level + 1;
		json_array* a = json_as_array(value);
		size_t keys = json_array_size(a);

		for (size_t k=0; k<keys; k++) {
			for (size_t i=0; i<nl; i++) {
				if (!prefs->writer(perlinsert, strlen(perlinsert), prefs->writer_data))
					return false;
			}

			json_value_t* value = json_array_get(a, k);
			if (!do_serialize(value, prefs, perlinsert, eol, nl))
				return false;

			if (k != keys-1) {
				if (prefs->pretty) {
					if (!prefs->writer(", ", 2, prefs->writer_data))
						return false;
				} else {
					if (!prefs->writer(",", 1, prefs->writer_data))
						return false;
				}
			}

			if (!prefs->writer(eol, strlen(eol), prefs->writer_data))
				return false;
		}

		for (size_t i=0; i<level; i++) {
			if (!prefs->writer(perlinsert, strlen(perlinsert), prefs->writer_data))
				return false;
		}
		if (!prefs->writer("]", 1, prefs->writer_data))
			return false;
		return true;
	}
	case JS_NUMBER: {
		double num = json_as_number(value, NULL);
		char buf[MAX_DOUBLE_LENGTH];
		sprintf(buf, prefs->number_formatter, num);
		return prefs->writer(buf, strlen(buf), prefs->writer_data);
	}
	case JS_STRING: {
		char* string = json_as_string(value);
		return do_serialize_string(string, prefs);
	}
	case JS_BOOL: {
		bool v = json_as_bool(value, NULL);
		if (v)
			return prefs->writer("true", 4, prefs->writer_data);
		else
			return prefs->writer("false", 5, prefs->writer_data);
	}
	case JS_NULL: {
		return prefs->writer("null", 4, prefs->writer_data);
	}
	case INVALID:
	default:
		return false;
	}
}

static bool serialize(json_value_t* value, aojls_serialization_prefs* prefs) {
	const char* eol = "";
	char* perlinsert = "";
	if (prefs->number_formatter == NULL) {
		prefs->number_formatter = "%.17g";
	}
	if (prefs->pretty) {
		if (prefs->eol == NULL)
			eol = "\n";
		else
			eol = prefs->eol;
		perlinsert = (char*)malloc((prefs->offset_per_level)+1 * sizeof(char));
		if (perlinsert == NULL) {
			return false;
		}
		for (size_t i=0; i<prefs->offset_per_level; i++)
			perlinsert[i] = ' ';
		perlinsert[prefs->offset_per_level] = '\0';
	}
	bool r = true;

	r = do_serialize(value, prefs, perlinsert, eol, 0);

	if (prefs->pretty) {
		free(perlinsert);
	}
	return r;
}

char* aojls_serialize(json_value_t* value, aojls_serialization_prefs* prefs) {
	aojls_serialization_prefs p;
	if (prefs == NULL) {
		p.pretty = false;
		p.writer_data = NULL;
		p.writer = NULL;
	} else {
		p = *prefs;
	}

	bool selfbuffer = false;
	if (p.writer == NULL) {
		selfbuffer = true;
		p.writer = string_writer_function;
		string_buffer_data_t* wd = (string_buffer_data_t*)malloc(sizeof(string_buffer_data_t));
		if (wd == NULL) {
			p.success = false;
			return NULL;
		}

		wd->data = (char*)malloc(2048);
		if (wd->data == NULL) {
			free(wd);
			p.success = false;
			return NULL;
		}
		wd->len = 2048;
		wd->offset = 0;
		p.writer_data = wd;
	}

	bool result = serialize(value, &p);
	p.success = result;

	if ((!result && selfbuffer) || (selfbuffer && !p.writer("\0", 1, p.writer_data))) {
		free(((string_buffer_data_t*)p.writer_data)->data);
		free(p.writer_data);
		if (prefs != NULL) {
			*prefs = p;
		}
		return NULL;
	}

	if (selfbuffer) {
		char* buffer = ((string_buffer_data_t*)p.writer_data)->data;
		free(p.writer_data);
		if (prefs != NULL) {
			*prefs = p;
		}
		return buffer;
	}

	if (prefs != NULL) {
		*prefs = p;
	}
	return NULL;
}

// Deserializer

long string_reader_function(char* buffer, size_t len, void* reader_data) {
	string_buffer_data_t* rd = (string_buffer_data_t*)reader_data;
	if (rd == NULL || rd->data == NULL) {
		return -1;
	} else if (rd->offset >= rd->len) {
		return 0;
	}

	size_t readsiz = len >= rd->len - rd->offset ?
			rd->len - rd->offset : len;
	memcpy(buffer, rd->data+rd->offset, readsiz);
	rd->offset += readsiz;
	return readsiz;
}

typedef enum {
	LEFT_CURLY, RIGHT_CURLY,
	LEFT_SQUARE, RIGHT_SQUARE,
	STRING, COMMA, COLON, DOT,
	PLUS, MINUS, DIGIT, E,
	_TRUE, _FALSE, _NULL
} json_token_type_t;

typedef struct {
	char* value;
	size_t len;
	json_token_type_t type;
} json_token_t;

bool append_token(json_token_t** tbuf, size_t* bflen, size_t* n,
		char* data, size_t len, json_token_type_t type) {
	size_t bfl = *bflen;
	size_t nn = *n;

	if (bfl == nn) {
		size_t nl = bfl * 2;
		json_token_t* nt = (json_token_t*)realloc(*tbuf, sizeof(json_token_t)*nl);
		if (nt == NULL) {
			return false;
		}
		*tbuf = nt;
		*bflen = nl;
	}

	json_token_t* t = *tbuf;
	json_token_t* token = &t[*n];
	*n += 1;

	token->type = type;
	token->len = len;
	token->value = data;
	return true;
}

json_token_t* create_token_stream(aojls_deserialization_prefs* prefs, size_t* count) {
	size_t numtokens = 0;
	size_t bflen = 32;
	json_token_t* tbuf = (json_token_t*)malloc(sizeof(json_token_t)*bflen);
	string_buffer_data_t* data = NULL;
	if (tbuf == NULL) {
		goto memerror;
	}
	char ib[1];
	long readc = prefs->reader(ib, 1, prefs->reader_data);
	data = (string_buffer_data_t*)calloc(1, sizeof(string_buffer_data_t));
	if (data == NULL) {
		goto memerror;
	}
	data->len = 16;
	data->data = calloc(data->len, sizeof(char));
	if (data->data == NULL) {
		goto memerror;
	}

	bool in_string = false;
	bool escaped = false;

	size_t truep = 0;
	size_t falsep = 0;
	size_t nullp = 0;

	while (true) {
		if (readc < 0) {
			prefs->error = "tokenstream: failed to read data";
			goto cleanup;
		}

		if (truep == 4) {
			if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, _TRUE)) {
				goto memerror;
			}
			truep = 0;
		}

		if (falsep ==5) {
			if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, _FALSE)) {
				goto memerror;
			}
			falsep = 0;
		}

		if (nullp == 4) {
			if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, _NULL)) {
				goto memerror;
			}
			nullp = 0;
		}

		if (readc == 0) {
			if (in_string || escaped) {
				prefs->error = "tokenstream: eof in the middle of a token";
				goto cleanup;
			}
			break;
		}

		char current = ib[0];
		readc = prefs->reader(ib, 1, prefs->reader_data);

		if (in_string) {
			if (!escaped && current == '"') {
				in_string = false;
				if (!append_token(&tbuf, &bflen, &numtokens, data->data, data->offset, STRING)) {
					goto memerror;
				}
				free(data);
				data = (string_buffer_data_t*)calloc(1, sizeof(string_buffer_data_t));
				if (data == NULL) {
					goto memerror;
				}
				data->len = 16;
				data->data = calloc(data->len, sizeof(char));
				if (data->data == NULL) {
					goto memerror;
				}
			} else {
				if (escaped) {
					switch (current) {
					case 'b': current = '\b'; break;
					case 'f': current = '\f'; break;
					case 'n': current = '\n'; break;
					case 'r': current = '\r'; break;
					case 't': current = '\t'; break;
					case '"': current = '"'; break;
					case '/': current = '/'; break;
					case 'u':
						if (!string_writer_function("\\", 1, data)) {
							goto memerror;
						}
						break;
					case '\\': current = '\\'; break;
					default:
						prefs->error = "tokenstream: unknown escape sequence";
						goto cleanup;
					}
				} else if (current == '\\') {
					escaped = true;
					continue;
				}
				if (!string_writer_function(&current, 1, data)) {
					goto memerror;
				}
				escaped = false;
			}
		} else {
			switch (current) {
			case 0x20:
			case 0x09:
			case 0x0A:
			case 0x0D:
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got whitespace";
					goto cleanup;
				}
				break;

			case 'e':
				if (falsep == 4) {
					++falsep;
					break;
				} else if (truep == 3) {
					++truep;
					break;
				}
				/* no break */
            // fall through
			case 'E':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got e/E instead";
					goto cleanup;
				}

				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, E)) {
					goto memerror;
				}
				break;
			case '0':
			case '1':
			case '2':
			case '3':
			case '4':
			case '5':
			case '6':
			case '7':
			case '8':
			case '9':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got digit instead";
					goto cleanup;
				}

				char* str = malloc(sizeof(char)*2);
				if (str == NULL) {
					goto memerror;
				}

				str[0] = current;
				str[1] = '\0';

				if (!append_token(&tbuf, &bflen, &numtokens, str, 1, DIGIT)) {
					goto memerror;
				}
				break;
			case '"':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got \" instead";
					goto cleanup;
				}

				in_string = true;
				break;
			case '{':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got { instead";
					goto cleanup;
				}

				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, LEFT_CURLY)) {
					goto memerror;
				}
				break;
			case '}':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got } instead";
					goto cleanup;
				}

				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, RIGHT_CURLY)) {
					goto memerror;
				}
				break;
			case '[':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got [ instead";
					goto cleanup;
				}

				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, LEFT_SQUARE)) {
					goto memerror;
				}
				break;
			case ']':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got ] instead";
					goto cleanup;
				}

				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, RIGHT_SQUARE)) {
					goto memerror;
				}
				break;
			case '+':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got + instead";
					goto cleanup;
				}

				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, PLUS)) {
					goto memerror;
				}
				break;
			case '-':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got - instead";
					goto cleanup;
				}

				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, MINUS)) {
					goto memerror;
				}
				break;
			case '.':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got . instead";
					goto cleanup;
				}


				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, DOT)) {
					goto memerror;
				}
				break;
			case ':':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got : instead";
					goto cleanup;
				}

				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, COLON)) {
					goto memerror;
				}
				break;
			case ',':
				if (falsep > 0 || truep > 0 || nullp > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got , instead";
					goto cleanup;
				}

				if (!append_token(&tbuf, &bflen, &numtokens, NULL, 0, COMMA)) {
					goto memerror;
				}
				break;
			case 't':
				if (falsep > 0 || nullp > 0 || truep != 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got t instead";
					goto cleanup;
				}
				++truep;
				break;
			case 'r':
				if (falsep > 0 || nullp > 0 || truep != 1) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got r instead";
					goto cleanup;
				}
				++truep;
				break;
			case 'u':
				if (falsep > 0 || (nullp != 1 && truep != 2)) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got u instead";
					goto cleanup;
				}
				if (nullp != 1)
					++truep;
				else
					++nullp;
				break;
			case 'f':
				if (falsep != 0 || nullp > 0 || truep > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got f instead";
					goto cleanup;
				}
				++falsep;
				break;
			case 'a':
				if (falsep != 1 || nullp > 0 || truep > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got a instead";
					goto cleanup;
				}
				++falsep;
				break;
			case 'l':
				if (truep > 0 || (falsep != 2 && nullp != 2 && nullp != 3)) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got l instead";
					goto cleanup;
				}
				if (falsep == 2)
					++falsep;
				else
					++nullp;
				break;
			case 's':
				if (falsep != 3 || nullp > 0 || truep > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got s instead";
					goto cleanup;
				}
				++falsep;
				break;
			case 'n':
				if (falsep > 0 || nullp != 0 || truep > 0) {
					prefs->error = "tokenstream: incorrect token, expected keyword continuation, got n instead";
					goto cleanup;
				}
				++nullp;
				break;
			default:
				prefs->error = "tokenstream: incorrect character in token stream";
				goto cleanup;
			}
		}
	}

	*count = numtokens;
	free(data->data);
	free(data);
	return tbuf;

memerror:
	prefs->error = "tokenstream: memory error";
cleanup:
	for (size_t i=0; i<numtokens; i++) {
		free(tbuf[i].value);
	}
	free(tbuf);
	if (data != NULL)
		free(data->data);
	free(data);
	return NULL;
}

typedef struct tokenizer {
	size_t cpos;
	size_t total;
	json_token_t* tokenstream;
	jmp_buf jmppos;
} tokenizer_t;

static inline bool has_next(tokenizer_t* tokenizer) {
	return tokenizer->cpos < tokenizer->total;
}

static inline json_token_t* next(tokenizer_t* tokenizer) {
	if (!has_next(tokenizer)) {
		return NULL;
	} else
		return &tokenizer->tokenstream[tokenizer->cpos++];
}

static inline bool next_type(tokenizer_t* tokenizer, json_token_type_t ttype) {
	if (!has_next(tokenizer)) {
		return false;
	} else
		return tokenizer->tokenstream[tokenizer->cpos].type == ttype;
}

size_t get_current_pos(tokenizer_t* tokenizer) {
	return tokenizer->cpos;
}

static inline void set_current_pos(tokenizer_t* tokenizer, size_t cpos) {
	tokenizer->cpos = cpos;
}

static inline void fail(tokenizer_t* tokenizer, int status) {
	longjmp(tokenizer->jmppos, status);
}

/* parser rules */

typedef struct {
	char* key;
	json_value_t* value;
} _pair_t;

static bool parse_value(aojls_ctx_t*, tokenizer_t*, json_value_t**);
static bool parse_object(aojls_ctx_t*, tokenizer_t*, json_object**);
static bool parse_members(aojls_ctx_t*, tokenizer_t*, _pair_t**, size_t*);
static bool parse_pair(aojls_ctx_t*, tokenizer_t*, _pair_t*);
static bool parse_array(aojls_ctx_t*, tokenizer_t*, json_array**);
static bool parse_elements(aojls_ctx_t*, tokenizer_t*, json_value_t***, size_t*);
static bool parse_string(aojls_ctx_t*, tokenizer_t*, char**);
static bool parse_number(aojls_ctx_t*, tokenizer_t*, double*);
static bool parse_int(aojls_ctx_t*, tokenizer_t*, double*);
static bool parse_fract(aojls_ctx_t*, tokenizer_t*, double*);
static bool parse_exp(aojls_ctx_t*, tokenizer_t*, double*);
static bool parse_digits(aojls_ctx_t*, tokenizer_t*, char**);
static bool parse_digit(aojls_ctx_t*, tokenizer_t*, char*);
static bool parse_digit19(aojls_ctx_t*, tokenizer_t*, char*);

static bool parse_value(aojls_ctx_t* ctx, tokenizer_t* tokenizer, json_value_t** result) {
	size_t cprg = get_current_pos(tokenizer);
	char* str;
	if (parse_string(ctx, tokenizer, &str)) {
		json_string* s = json_from_string(ctx, str);
		if (s == NULL)
			fail(tokenizer, FAIL_ENOMEM);
		*result = (json_value_t*)s;
		return true;
	}
	set_current_pos(tokenizer, cprg);
	double res = 0;
	if (parse_number(ctx, tokenizer, &res)) {
		json_number* num = json_from_number(ctx, res);
		if (num == NULL)
			fail(tokenizer, FAIL_ENOMEM);
		*result = (json_value_t*)num;
		return true;
	}
	set_current_pos(tokenizer, cprg);
	if (parse_object(ctx, tokenizer, (json_object**)result)) {
		return true;
	}
	set_current_pos(tokenizer, cprg);
	if (parse_array(ctx, tokenizer, (json_array**)result)) {
		return true;
	}
	if (next_type(tokenizer, _TRUE)) {
		next(tokenizer); // eat token
		json_boolean* b = json_from_boolean(ctx, 1);
		if (b == NULL)
			fail(tokenizer, FAIL_ENOMEM);
		*result = (json_value_t*)b;
		return true;
	}
	if (next_type(tokenizer, _FALSE)) {
		next(tokenizer); // eat token
		json_boolean* b = json_from_boolean(ctx, 0);
		if (b == NULL)
			fail(tokenizer, FAIL_ENOMEM);
		*result = (json_value_t*)b;
		return true;
	}
	if (next_type(tokenizer, _NULL)) {
		next(tokenizer); // eat token
		json_null* n = json_make_null(ctx);
		if (n == NULL)
			fail(tokenizer, FAIL_ENOMEM);
		*result = (json_value_t*)n;
		return true;
	}
	*result = NULL;
	return false;
}

static bool parse_object(aojls_ctx_t* ctx, tokenizer_t* tokenizer, json_object** object) {
	_pair_t* pairs;
	size_t len;

	if (next_type(tokenizer, LEFT_CURLY)) {
		next(tokenizer);
		if (next_type(tokenizer, RIGHT_CURLY)) {
			next(tokenizer);
			*object = json_make_object(ctx);
			if ((*object) == NULL)
				fail(tokenizer, FAIL_ENOMEM);
			return true;
		} else if (parse_members(ctx, tokenizer, &pairs, &len)) {
			if (!next_type(tokenizer, RIGHT_CURLY)) {
				free(pairs);
				fail(tokenizer, FAIL_EXPECTED_EOO);
			}

			*object = json_make_object(ctx);
			if ((*object) == NULL) {
				free(pairs);
				fail(tokenizer, FAIL_ENOMEM);
			}
			for (size_t i=0; i<len; i++) {
				_pair_t* p = &pairs[i];
				if (json_object_add(*object, p->key, p->value) == NULL) {
					free(pairs);
					fail(tokenizer, FAIL_ENOMEM);
				}
			}
			free(pairs);
			next(tokenizer);
			return true;
		}
	}
	return false;
}

static bool parse_members(aojls_ctx_t* ctx, tokenizer_t* tokenizer, _pair_t** members, size_t* members_count) {
	size_t bfc = 16;
	size_t len = 0;
	_pair_t* memb = (_pair_t*)malloc(sizeof(_pair_t)*bfc);
	bool first = true;

	do {
		int cpgr = get_current_pos(tokenizer);
		if (!first)
			next(tokenizer); // eat comma
		_pair_t pair;
		if (!parse_pair(ctx, tokenizer, &pair)) {
			if (!first) {
				free(memb);
				fail(tokenizer, FAIL_EXPECTED_PAIR);
			}
			set_current_pos(tokenizer, cpgr);
			break;
		}

		if (len == bfc) {
			size_t nbfc = bfc * 2;
			_pair_t* nmemb = (_pair_t*)realloc(memb, sizeof(_pair_t)*nbfc);
			if (nmemb == NULL) {
				free(memb);
				fail(tokenizer, FAIL_ENOMEM);
			}
			memb = nmemb;
			bfc = nbfc;
		}
		memb[len++] = pair;

		first = false;
	} while (next_type(tokenizer, COMMA));

	*members = memb;
	*members_count = len;
	return true;
}

static bool parse_pair(aojls_ctx_t* ctx, tokenizer_t* tokenizer, _pair_t* pair) {
	char* str;
	_pair_t pp;

	if (!parse_string(ctx, tokenizer, &str)) {
		return false;
	}
	pp.key = str;
	if (!next_type(tokenizer, COLON)) {
		return false;
	}
	next(tokenizer); // eat colon
	if (!parse_value(ctx, tokenizer, &pp.value)) {
		return false;
	}
	*pair = pp;
	return true;
}

static bool parse_array(aojls_ctx_t* ctx, tokenizer_t* tokenizer, json_array** array) {
	json_value_t** elements;
	size_t len;

	if (next_type(tokenizer, LEFT_SQUARE)) {
		next(tokenizer);
		if (next_type(tokenizer, RIGHT_SQUARE)) {
			next(tokenizer);
			*array = json_make_array(ctx);
			if ((*array) == NULL)
				fail(tokenizer, FAIL_ENOMEM);
			return true;
		} else if (parse_elements(ctx, tokenizer, &elements, &len)) {
			if (!next_type(tokenizer, RIGHT_SQUARE)) {
				free(elements);
				fail(tokenizer, FAIL_EXPECTED_EOL);
			}
			next(tokenizer);

			*array = json_make_array(ctx);
			if ((*array) == NULL) {
				free(elements);
				fail(tokenizer, FAIL_ENOMEM);
			}
			for (size_t i=0; i<len; i++) {
				json_value_t* v = elements[i];
				if (json_array_add(*array, v) == NULL) {
					free(elements);
					fail(tokenizer, FAIL_ENOMEM);
				}
			}
			free(elements);
			return true;
		}
	}
	return false;
}

static bool parse_elements(aojls_ctx_t* ctx, tokenizer_t* tokenizer, json_value_t*** elements, size_t* size) {
	size_t bfc = 16;
	size_t len = 0;
	json_value_t** elems = (json_value_t**)malloc(sizeof(json_value_t*)*bfc);
	bool first = true;

	do {
		int cpgr = get_current_pos(tokenizer);
		if (!first)
			next(tokenizer); // eat comma
		json_value_t* value;
		if (!parse_value(ctx, tokenizer, &value)) {
			if (!first) {
				free(elems);
				fail(tokenizer, FAIL_EXPECTED_VALUE);
			}
			set_current_pos(tokenizer, cpgr);
			break;
		}

		if (len == bfc) {
			size_t nbfc = bfc * 2;
			json_value_t** nelems = (json_value_t**)realloc(elems, sizeof(json_value_t*)*nbfc);
			if (nelems == NULL) {
				free(elems);
				fail(tokenizer, FAIL_ENOMEM);
			}
			elems = nelems;
			bfc = nbfc;
		}
		elems[len++] = value;

		first = false;
	} while (next_type(tokenizer, COMMA));

	*elements = elems;
	*size = len;
	return true;
}

static bool parse_string(aojls_ctx_t* ctx, tokenizer_t* tokenizer, char** string) {
	if (next_type(tokenizer, STRING)) {
		json_token_t* token = next(tokenizer);
		*string = append_string(ctx, token->value, token->len);
		return true;
	}
	return false;
}

static size_t count_digits(double d) {
	if (d == 0.0)
		return 0;
	char buffer[MAX_DOUBLE_LENGTH];
	sprintf(buffer, "%.0f", d);
	size_t len = strlen(buffer);
	return d < 0 ? len-1 : len;
}

static inline double power(double x, long y) {
	double temp;
    if (y == 0)
       return 1;
    temp = power(x, y/2);
    if (y%2 == 0)
        return temp*temp;
    else {
        if(y > 0)
            return x*temp*temp;
        else
            return (temp*temp)/x;
    }
}

static bool parse_number(aojls_ctx_t* ctx, tokenizer_t* tokenizer, double* num) {
	double _int;
	double _frac;
	double _exp;
	double r;

	if (!parse_int(ctx, tokenizer, &_int)) {
		return false;
	}

	size_t cpgr = get_current_pos(tokenizer);
	if (parse_fract(ctx, tokenizer, &_frac)) {
		size_t cpgr2 = get_current_pos(tokenizer);
		if (parse_exp(ctx, tokenizer, &_exp)) {
			goto compute_number;
		} else {
			set_current_pos(tokenizer, cpgr2);
			_exp = 0;
			goto compute_number;
		}
	}
	set_current_pos(tokenizer, cpgr);
	_frac = 0;

	if (parse_exp(ctx, tokenizer, &_exp)) {
		goto compute_number;
	}
	_exp = 0;
compute_number:
	r = _int;
	size_t digitsc = count_digits(_frac);
	if (digitsc != 0)
		_frac = _frac/power(10.0, digitsc);
	r += _frac;
	if (_exp != 0) {
		r = r*power(10.0, (long)_exp);
	}
	*num = r;
	return true;
}

static bool parse_int(aojls_ctx_t* ctx, tokenizer_t* tokenizer, double* num) {
	bool minus = false;
	if (next_type(tokenizer, MINUS)) {
		next(tokenizer);
		minus = true;
	}

	size_t cpgr = get_current_pos(tokenizer);

	char* digits = NULL;
	char digit1 = 0;

	if (parse_digit19(ctx, tokenizer, &digit1)) {
		if (parse_digits(ctx, tokenizer, &digits)) {
			char* newdigits = (char*)malloc(sizeof(char)*(strlen(digits)+2));
			if (newdigits == NULL) {
				free(digits);
				fail(tokenizer, FAIL_ENOMEM);
			}
			newdigits[0] = digit1;
			memcpy(newdigits+1, digits, strlen(digits)+1);
			free(digits);
			digits = newdigits;
		} else {
			digits = (char*)malloc(sizeof(char)*2);
			if (digits == NULL) {
				fail(tokenizer, FAIL_ENOMEM);
			}
			digits[0] = digit1;
			digits[1] = '\0';
		}

		double r = strtod(digits, NULL);
		if (minus) {
			*num = -r;
		} else {
			*num = r;
		}
		free(digits);
		return true;
	}

	set_current_pos(tokenizer, cpgr);
	if (parse_digit(ctx, tokenizer, &digit1)) {
		*num = 0.0;
		return true;
	}

	return false;
}

static bool parse_fract(aojls_ctx_t* ctx, tokenizer_t* tokenizer, double* num) {
	if (!next_type(tokenizer, DOT)) {
		return false;
	}

	next(tokenizer); // eat dot
	char* digits;
	if (parse_digits(ctx, tokenizer, &digits)) {
		*num = strtod(digits, NULL);
		free(digits);
		return true;
	}

	return false;
}

static bool parse_exp(aojls_ctx_t* ctx, tokenizer_t* tokenizer, double* num) {
	bool minus = false;

	if (next_type(tokenizer, E)) {
		next(tokenizer); // eat e/E

		if (next_type(tokenizer, PLUS)) {
			next(tokenizer);
		} else if (next_type(tokenizer, MINUS)) {
			next(tokenizer);
			minus = true;
		}

		char* digits;
		if (parse_digits(ctx, tokenizer, &digits)) {
			double r = strtod(digits, NULL);
			free(digits);
			if (minus)
				*num = -r;
			else
				*num = r;
			return true;
		}
	}
	return false;
}

static bool parse_digits(aojls_ctx_t* ctx, tokenizer_t* tokenizer, char** digits) {
	size_t bfc = 16;
	size_t len = 0;
	char* buf = (char*)malloc(sizeof(char)*bfc);

	do {
		int cpgr = get_current_pos(tokenizer);
		char digit;
		if (!parse_digit(ctx, tokenizer, &digit)) {
			set_current_pos(tokenizer, cpgr);
			break;
		}

		if (len == bfc-1) {
			size_t nbfc = bfc * 2;
			char* nbuf = (char*)realloc(buf, sizeof(char)*nbfc);
			if (nbuf == NULL) {
				free(buf);
				fail(tokenizer, FAIL_ENOMEM);
			}
			buf = nbuf;
			bfc = nbfc;
		}
		buf[len++] = digit;
	} while (true);

	buf[len] = '\0';
	*digits = buf;
	return true;
}

static bool parse_digit(aojls_ctx_t* ctx, tokenizer_t* tokenizer, char* digit) {
   (void)ctx;
	if (next_type(tokenizer, DIGIT)) {
		json_token_t* tok = next(tokenizer);
		*digit = tok->value[0];
		return true;
	}
	return false;
}

static bool parse_digit19(aojls_ctx_t* ctx, tokenizer_t* tokenizer, char* digit) {
   (void)ctx;
	if (next_type(tokenizer, DIGIT)) {
		json_token_t* tok = next(tokenizer);
		*digit = tok->value[0];
		if (*digit == 0)
			return false;
		return true;
	}
	return false;
}

static json_value_t* deserialize(aojls_deserialization_prefs* prefs) {
	size_t tlen = 0;
	json_token_t* tokenstream = create_token_stream(prefs, &tlen);
	if (tokenstream == NULL) {
		prefs->ctx->failed = true;
		return NULL;
	}

	tokenizer_t tokenizer;
	tokenizer.tokenstream = tokenstream;
	tokenizer.cpos = 0;
	tokenizer.total = tlen;

	json_value_t* result;
	int ff;
	if ((ff = setjmp(tokenizer.jmppos)) == 0) {
		if (!parse_value(prefs->ctx, &tokenizer, &result)) {
			prefs->error = "failed to parse json tokenstream";
			goto error;
		}
	} else {
		switch (ff) {
		case FAIL_ENOMEM:
			prefs->error = "failed to parse json due to no memory";
			break;
		case FAIL_EXPECTED_PAIR:
			prefs->error = "failed to parse json due to wrong token sequence, expected pair, got something else";
			break;
		case FAIL_EXPECTED_VALUE:
			prefs->error = "failed to parse json due to wrong token sequence, expected value, got something else";
			break;
		case FAIL_EXPECTED_EOO:
			prefs->error = "failed to parse json due to wrong token sequence, expected }, got something else";
			break;
		case FAIL_EXPECTED_EOL:
			prefs->error = "failed to parse json due to wrong token sequence, expected ], got something else";
			break;
		}
		goto error;
	}

	for (size_t i=0; i<tlen; i++)
		free(tokenstream[i].value);
	free(tokenstream);
	prefs->error = NULL;
	return result;
error:
	for (size_t i=0; i<tlen; i++)
		free(tokenstream[i].value);
	free(tokenstream);
	prefs->ctx->failed = true;
	return NULL;
}

aojls_ctx_t* aojls_deserialize(char* source, size_t len, aojls_deserialization_prefs* prefs) {
	aojls_deserialization_prefs p;
	if (prefs == NULL) {
		p.ctx = NULL;
		p.reader = NULL;
		p.reader_data = NULL;
	} else {
		p = *prefs;
	}

	if (p.ctx == NULL) {
		p.ctx = json_make_context();
		if (p.ctx == NULL) {
			return NULL;
		}
	}

	bool selfbuffer = false;
	if (p.reader == NULL) {
		selfbuffer = true;
		p.reader = string_reader_function;
		string_buffer_data_t* rd = (string_buffer_data_t*)malloc(sizeof(string_buffer_data_t));
		if (rd == NULL) {
			p.ctx->failed = true;
			return p.ctx;
		}
		rd->data = source;
		rd->len = len;
		rd->offset = 0;
		p.reader_data = rd;
	}

	p.ctx->result = deserialize(&p);

	if (selfbuffer) {
		free(p.reader_data);
	}

	if (prefs != NULL) {
		*prefs = p;
	}

	return p.ctx;
}
