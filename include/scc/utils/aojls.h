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

/**
 * @file aojls.h
 * @author Peter Vanusanik
 * @date 2016 13. 3.
 * @brief AOJLS definitions
 *
 * All public api of AOJLS resides here. You only need to include this file to
 * work with AOJLS
 * @see http://enerccio.github.io/aojls/
 */

#pragma once

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

#ifndef AOJLS_OBJECT_START_ALLOC_SIZE
#define AOJLS_OBJECT_START_ALLOC_SIZE 16
#endif

#ifndef AOJLS_ARRAY_START_ALLOC_SIZE
#define AOJLS_ARRAY_START_ALLOC_SIZE 16
#endif

/**
 * @brief JSON value tags
 *
 * Every JSON value is identified by one of these tags
 */
typedef enum {
	JS_OBJECT		= 0, /**< Tag for JSON object */
	JS_ARRAY		= 1, /**< Tag for JSON array */
	JS_NUMBER		= 2, /**< Tag for JSON number */
	JS_STRING		= 3, /**< Tag for JSON string */
	JS_BOOL			= 4, /**< Tag for JSON bool */
	JS_NULL			= 5, /**< Tag for JSON null */
	INVALID			= 6 /**< This tag is never used in any object, however, it may be returned from tag query, in case of invalid reference */
} json_type_t;

/**
 * @brief AOJLS Context object, holding all memory references to JSON values and strings
 */
typedef struct aojls_ctx aojls_ctx_t;
/**
 * @brief Unified type for any JSON value.
 *
 * All JSON value references can be casted into this.
 */
typedef struct json_value json_value_t;
/**
 * @brief JSON object
 *
 * JSON object is a map between string keys and JSON values. In AOLJS you can have multiple identical keys,
 * which will be no problem (however, serialized form might not be valid JSON).
 *
 * json_object references are one-way mutable, ie new key-value pairs might be defined, but none can be
 * removed.
 */
typedef struct json_object json_object;
/**
 * @brief JSON array
 *
 * JSON array is an array of JSON values. json_array references are one-way mutabe, ie new value can be
 * inserted, however no value can be removed
 */
typedef struct json_array json_array;
/**
 * @brief JSON string
 *
 * immutable, also string value is also tracked by context
 */
typedef struct json_string json_string;
/**
 * @brief JSON number
 */
typedef struct json_number json_number;
/**
 * @brief JSON boolean
 */
typedef struct json_boolean json_boolean;
/**
 * @brief JSON null
 */
typedef struct json_null json_null;

/* Value */

/**
 * @brief Returns type for provided value.
 *
 * If NULL pointer is passed as @p value, returns INVALID. Otherwise returns
 * the type of that JSON value.
 *
 * @param value queried JSON value
 * @return type of queried JSON value
 * @see json_type_t
 */
json_type_t json_get_type(json_value_t* value);

/**
 * @brief Converts reference to JSON value to JSON object
 *
 * If @p value is NULL, returns NULL, otherwise returns reference to json_object, if value is
 * JSON object or NULL.
 *
 * @param value JSON value
 * @returns json_object if it is valid JSON object
 * @see json_object
 * @see json_get_type
 */
json_object* json_as_object(json_value_t* value);
/**
 * @brief Converts reference to JSON value to JSON array
 *
 * If @p value is NULL, returns NULL, otherwise returns reference to json_array, if value is
 * JSON array or NULL.
 *
 * @param value JSON value
 * @returns json_array if it is valid JSON array
 * @see json_array
 * @see json_get_type
 */
json_array* json_as_array(json_value_t* value);
/**
 * @brief Converts reference to numeric double value
 *
 * Returns 0 and sets @p correct_type to false if JSON value is invalid or not a number, otherwise
 * @p correct_type is set to true and value is converted to double.
 *
 * @param value JSON value
 * @param checker, if not NULL, state of conversion is stored there
 * @returns double value or 0 if invalid
 * @see json_number
 * @see json_get_type
 */
double json_as_number(json_value_t* value, bool* correct_type);
/**
 * @brief Converts reference to string
 *
 * Returns NULL if string is invalid.
 *
 * @param value JSON value
 * @returns char* string or NULL if invalid
 * @see json_string
 * @see json_get_type
 * @warning Do not deallocate this returned string in any way. It is tracked by context and will be freed
 *          when context is freed.
 */
char* json_as_string(json_value_t* value);
/**
 * @brief Converts reference to boolean
 *
 * Returns false and sets @p correct_type to false if JSON value is invalid or not a boolean, otherwise
 * @p correct_type is set to true and value is converted to boolean.
 *
 * @param value JSON value
 * @param checker, if not NULL, state of conversion is stored there
 * @returns true/false value or false if invalid
 * @see json_boolean
 * @see json_get_type
 */
bool json_as_bool(json_value_t* value, bool* correct_type);
/**
 * @brief Checks if reference is JSON null.
 *
 * @param value JSON value
 * @returns true/false if value is JSON null or not.
 * @see json_null
 * @see json_get_type
 * @warning returns false if reference passed into json_is_null is NULL itself!
 */
bool json_is_null(json_value_t* value);

/* Object */

/**
 * @brief Creates new empty JSON object
 *
 * Failure is marked in @p ctx.
 *
 * @param ctx context to which this JSON object will be bound
 * @return json_object reference or NULL in case of failure
 * @see json_object
 * @see aojls_ctx_t
 * @see json_context_error_happened
 */
json_object* json_make_object(aojls_ctx_t* ctx);

/**
 * @brief Adds key-value pair to this JSON object
 *
 * @param o JSON object
 * @param key null terminated string
 * @value value to be bound to this key
 * @return NULL in case of failure or JSON object
 * @warning Key must be null terminated and will be copied and stored in the context bound to the
 * JSON object!
 */
json_object* json_object_add(json_object* o, const char* key, json_value_t* value);

/**
 * @brief Adds key-value pair to this JSON object
 *
 * @param o JSON object
 * @param key string
 * @param len size of string key
 * @value value to be bound to this key
 * @return NULL in case of failure or JSON object
 * @warning Key may not be null terminated and will be copied and stored in the context bound to the
 * JSON object!
 */
json_object* json_object_nadd(json_object* o, const char* key, size_t len, json_value_t* value);

/**
 * @brief Sets value for key in this JSON object
 *
 * If key doesn't exists, this acts like json_object_add.
 * If key already exists, assotiated value is replaced.
 *
 * @param o JSON object
 * @param key null terminated string
 * @value value to be bound to this key
 * @return NULL in case of failure or JSON object
 * @warning Key must be null terminated and will be copied and stored in the context bound to the
 * JSON object!
 */
json_object* json_object_set(json_object* o, const char* key, json_value_t* value);

/**
 * @brief Removes value for key in this JSON object
 *
 * If key doesn't exists, does nothing.
 * If key already exists, it is removed.
 *
 * @param o JSON object
 * @param key null terminated string
 * @return NULL in case of failure or JSON object
 * @warning Key must be null terminated.
 */
json_object* json_object_set_undefined(json_object* o, const char* key);

/**
 * @return number of keys in this JSON object
 */
size_t json_object_numkeys(json_object* o);
/**
 * @brief Returns key bound to the iteration position @p i
 * @param o JSON object
 * @param i iterator, @p i <= number of keys in JSON object
 * @return key
 * @warning Do not deallocate this key
 * @see json_object_numkeys
 */
const char* json_object_get_key(json_object* o, size_t i);

/**
 * @brief Returns JSON value bound to this key.
 *
 * O(N) complexity where N is number of keys in this JSON object.
 * Keys are compared via strcmp.
 *
 * @param o JSON object
 * @param key
 * @return JSON value bound to that key or NULL in case of an error or no such key in this JSON object
 */
json_value_t* json_object_get_object_as_value(json_object* o, const char* key);
/**
 * @brief Returns JSON object bound to this key.
 * @return JSON object bound to that key or NULL in case of an error, if there is no such key or if key points to
 * other than JSON object JSON value.
 * @see json_object_get_key
 */
json_object* json_object_get_object(json_object* o, const char* key);
/**
 * @brief Returns JSON array bound to this key.
 * @return JSON array bound to that key or NULL in case of an error, if there is no such key or if key points to
 * other than JSON array JSON value.
 * @see json_object_get_key
 */
json_array* json_object_get_array(json_object* o, const char* key);
/**
 * @brief Returns double bound to this key.
 * @param o JSON object
 * @param key key
 * @param valid will contain true if position is valid and JSON number is at that position or false
 * @return double bound to that key or 0 in case of an error, if there is no such key or if key points to
 * other than JSON number JSON value.
 * @see json_object_get_key
 */
double json_object_get_double(json_object* o, const char* key, bool* valid);
/**
 * @brief Returns double bound to this key or default value.
 * @param o JSON object
 * @param key key
 * @param defval default value
 * @return double bound to that key or @p defval in case of an error, if there is no such key or if key points to
 * other than JSON number JSON value.
 * @see json_object_get_key
 */
double json_object_get_double_default(json_object* o, const char* key, double defval);
/**
 * @brief Returns string bound to this key.
 * @param o JSON object
 * @param key key
 * @return string bound to that key or NULL in case of an error, if there is no such key or if key points to
 * other than JSON string JSON value.
 * @see json_object_get_key
 */
char* json_object_get_string(json_object* o, const char* key);
/**
 * @brief Returns string bound to this key or default value.
 * @param o JSON object
 * @param key key
 * @param defval default value
 * @return string bound to that key or @p defval in case of an error, if there is no such key or if key points to
 * other than JSON string JSON value.
 * @see json_object_get_key
 */
char* json_object_get_string_default(json_object* o, const char* key, char* defval);
/**
 * @brief Returns boolean bound to this key.
 * @param o JSON object
 * @param key key
 * @param valid will contain true if position is valid and JSON boolean is at that position or false
 * @return boolean bound to that key or NULL in case of an error, if there is no such key or if key points to
 * other than JSON boolean JSON value.
 * @see json_object_get_key
 */
bool json_object_get_bool(json_object* o, const char* key, bool* valid);
bool json_object_get_bool_default(json_object* o, const char* key, bool defval);
/**
 * @brief Returns if null is bound for that key
 * @param o JSON object
 * @param key key
 * @return true if JSON null is bound to that key
 * @see json_object_get_key
 */
bool json_object_is_null(json_object* o, const char* key);

/* Array */

/**
 * @brief Creates new empty JSON array
 *
 * Failure is marked in @p ctx.
 *
 * @param ctx context to which this JSON array will be bound
 * @return json_array reference or NULL in case of failure
 * @see json_object
 * @see aojls_ctx_t
 * @see json_context_error_happened
 */
json_array* json_make_array(aojls_ctx_t* ctx);

/**
 * @brief Adds new JSON value to the JSON array
 *
 * @param a JSON array
 * @param value JSON value
 * @return NULL in case of failure, JSON array on success
 */
json_array* json_array_add(json_array* a, json_value_t* value);

/**
 * @brief Returns number of elements in this array
 * @param a JSON array
 */
size_t json_array_size(json_array* a);

/**
 * @brief Returns JSON value at position @p i
 * @param a array
 * @param i position
 * @return JSON value in the JSON array at position i or NULL if invalid position is specified
 */
json_value_t* json_array_get(json_array* a, size_t i);
/**
 * @brief Returns JSON object in JSON array at position @p i.
 * @param a array
 * @param i position
 * @return JSON object or NULL if position is invalid or there is no JSON object at that position
 * @see json_array_get
 */
json_object* json_array_get_object(json_array* a, size_t i);
/**
 * @brief Returns JSON array in JSON array at position @p i.
 * @param a array
 * @param i position
 * @return JSON array or NULL if position is invalid or there is no JSON array at that position
 * @see json_array_get
 */
json_array* json_array_get_array(json_array* a, size_t i);
/**
 * @brief Returns double value in JSON array at position @p i.
 * @param a array
 * @param i position
 * @param valid will contain true if position is valid and JSON number is at that position or false
 * @return double or 0 if position is invalid or there is no JSON number at that position
 * @see json_array_get
 */
double json_array_get_double(json_array* a, size_t i, bool* valid);
/**
 * @brief Returns double value in JSON array at position @p i or default value
 * @param a array
 * @param i position
 * @param defval returned in case of failure
 * @see json_array_get
 */
double json_array_get_double_default(json_array* a, size_t i, double defval);
/**
 * @brief Returns string in JSON array at position @p i.
 * @param a array
 * @param i position
 * @return string or NULL if position is invalid or there is no JSON string at that position
 * @see json_array_get
 * @warning Do not deallocate this string, it is tracked by context bound to the JSON string in the array
 */
char* json_array_get_string(json_array* a, size_t i);
/**
 * @brief Returns string in JSON array at position @p i or default.
 * @param a array
 * @param i position
 * @param defval is returned in any case of failure
 * @return string
 * @see json_array_get
 * @warning Do not deallocate this string , it is tracked by context bound to the JSON string in the array
 * This only applies if defval was not returned.
 */
char* json_array_get_string_default(json_array* a, size_t i, char* defval);
/**
 * @brief Returns boolean value in JSON array at position @p i.
 * @param a array
 * @param i position
 * @param valid will contain true if position is valid and JSON boolean is at that position or false
 * @return bool or false if position is invalid or there is no JSON boolean at that position
 * @see json_array_get
 */
bool json_array_get_bool(json_array* a, size_t i, bool* valid);
/**
 * @brief Returns boolean value in JSON array at position @p i or default value
 * @param a array
 * @param i position
 * @param defval returned in case of failure
 * @see json_array_get
 */
bool json_array_get_bool_default(json_array* a, size_t i, bool defval);
/**
 * @brief Returns whether JSON null is at the position @p i.
 * @param a array
 * @param i position
 * @return whether JSON null is at that position
 * @see json_array_get
 */
bool json_array_is_null(json_array* a, size_t i);

/* Primitives */

/**
 * @brief Creates JSON string from @p string.
 *
 * Failure is marked in @p ctx.
 *
 * @param ctx context to which this JSON string will be bound
 * @param string value
 * @return json_string reference or NULL in case of failure
 * @see json_object
 * @see aojls_ctx_t
 * @see json_context_error_happened
 * @warning @p string is copied into created object so source can be deallocated/modified after this call
 */
json_string* json_from_string(aojls_ctx_t* ctx, const char* string);
/**
 * @brief Creates JSON number from @p number.
 *
 * Failure is marked in @p ctx.
 *
 * @param ctx context to which this JSON number will be bound
 * @param number value
 * @return json_number reference or NULL in case of failure
 * @see json_object
 * @see aojls_ctx_t
 * @see json_context_error_happened
 */
json_number* json_from_number(aojls_ctx_t* ctx, double number);
/**
 * @brief Creates JSON boolean from @p b.
 *
 * Failure is marked in @p ctx.
 *
 * @param ctx context to which this JSON boolean will be bound
 * @param b boolean value
 * @return json_boolean reference or NULL in case of failure
 * @see json_object
 * @see aojls_ctx_t
 * @see json_context_error_happened
 */
json_boolean* json_from_boolean(aojls_ctx_t* ctx, bool b);
/**
 * @brief Creates JSON null
 *
 * Failure is marked in @p ctx.
 *
 * @param ctx context to which this JSON boolean will be bound
 * @return json_boolean reference or NULL in case of failure
 * @see json_object
 * @see aojls_ctx_t
 * @see json_context_error_happened
 */
json_null* json_make_null(aojls_ctx_t* ctx);

/* Context */

/**
 * @brief Creates new AOJLS context.
 *
 * All JSON value creating operations require valid context. All JSON value's memory
 * is then tracked by this context and therefore should not be freed explicitedly.
 *
 * @return NULL on failure or reference to new context
 */
aojls_ctx_t* json_make_context();
/**
 * @brief Whether any error is detected while manipulating with this context or values bound to it.
 *
 * @return true if any error has happened, false if none
 */
bool json_context_error_happened(aojls_ctx_t* ctx);
/**
 * @If this context was used in deserialization, returns result of last deserialization
 *
 * @return deserialized JSON value or NULL in case of an error or if this context was not used in deserialization
 * @warning if same context is used in multiple deserialization, the result will be overwritten!
 */
json_value_t* json_context_get_result(aojls_ctx_t* ctx);
/**
 * @brief frees the context and all bound values
 *
 * Frees all the memory used by all bound values in this context, all strings used by those values and then
 * context itself.
 * @warning After this operation, all references to any values in this context is undefined!
 */
void json_free_context(aojls_ctx_t* ctx);

/* Serialization */

/**
 * @brief Custom serialization callback
 *
 * This callback is called each time serializer needs to write byte output. writer_data is
 * user provided writer state that is passed in the preferences
 * @see aojls_serialization_prefs
 */
typedef bool(*writer_function_t)(const char* buffer, size_t len, void* writer_data);

/**
 * @brief Serialization preferences
 *
 * Contains all available preferences that can be used by serialization. Also holds result of
 * serialization where they were used.
 */
typedef struct {
	bool pretty; /**< Whether pretty output is required (newlines, indentation), default is false */
	size_t offset_per_level; /**< If pretty output is required, this denounces number of spaces per level, default is 4 */
	const char* eol; /**< Custom end of line character sequence, default is '\n' */
	const char* number_formatter; /**< Custom number formatter for JSON numbers. Default is "%f" */

	writer_function_t writer; /**< Custom writer function. If not provided, serializer will output to string */
	void* writer_data; /**< Writer state. Only applicable when custom writer is used, otherwise should be NULL. */

	bool success; /**< true if serialization was successful, false if not */
} aojls_serialization_prefs;

/**
 * @brief Serializes JSON value
 *
 * Serializes the JSON value according to the preferences specified. Returns serialized string if no
 * writer_function is specified or NULL in case of error or when custom writer_function is specified.
 *
 * @param value to be serialized
 * @param prefs preferences, may be NULL
 * @return serialized value or NULL
 * @see aojls_serialization_prefs
 * @warning Any cycles in nested JSON values will cause stack overflow!
 * @warning If returned string is non-NULL, it must be freed by calling free when it is not needed!
 */
char* aojls_serialize(json_value_t* value, aojls_serialization_prefs* prefs);

/* Deserialization */

/**
 * @brief Custom deserialization callback
 *
 * This callback is called each time deserializer needs to read new data.
 * This callback must return number of bytes actually read in the buffer and it must be <= len, or
 * negative in case of failure. If 0 is returned, deserializer considers that as EOF.
 */
typedef long(*reader_function_t)(char* buffer, size_t len, void* reader_data);

/**
 * @brief Deserialization preferences
 *
 * Contains all available preferences that can be used by deserialization. Also holds reference to any error,
 * if it has happened during the deserialization.
 */
typedef struct {
	reader_function_t reader; /**< Custom reader function. If not provided, deserializer will use string provided as source */
	void* reader_data; /**< Reader state. Only applicable if custom reader is used, otherwise should be NULL */

	aojls_ctx_t* ctx; /**< If non-NULL, this context will be used by deserializer, otherwise new context will be created */
	const char* error; /**< If error has happened, this will contain reference to a string containing error details, otherwise NULL */
} aojls_deserialization_prefs;

/**
 * @brief Deserialization function
 *
 * @param source string containing JSON data, may be NULL if custom reader is used instead
 * @param len size of previous string, if applicable
 * @param prefs preferences used for this deserialization
 * @return context where the result may be (if there was no error) or NULL if context is not provided
 * and there was failure when creating a new one
 * @see aojls_ctx_t
 * @see json_context_get_result
 * @see json_free_context
 */
aojls_ctx_t* aojls_deserialize(char* source, size_t len, aojls_deserialization_prefs* prefs);
