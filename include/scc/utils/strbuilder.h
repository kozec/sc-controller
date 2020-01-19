#pragma once
#include <stddef.h>
#include <stdbool.h>

typedef struct StrBuilder StrBuilder;

struct StrBuilder {
	size_t		allocation;
	size_t		length;
	char*		value;
	char*		next;
	bool		failed;
};

/** Returns NULL if memory cannot be allocated */
StrBuilder* strbuilder_new();
/** Deallocates StrBuilder allong with not-yet-retrieved string it has generated */
void strbuilder_free(StrBuilder* b);
/** Returns false if memory cannot be allocated or if 'b' is NULL */
bool strbuilder_add(StrBuilder* b, const char* string);
/** Returns false if memory cannot be allocated or if 'b' is NULL */
bool strbuilder_add_char(StrBuilder* b, char c);
/** Returns false if memory cannot be allocated or if 'b' is NULL */
bool strbuilder_addf(StrBuilder* b, const char* format, ...);
/**
 * Clears strbuilder value, without deallocating anything.
 * If 'b' is NULL, does nothing.
 *
 * Also clears 'failed' flag.
 */
void strbuilder_clear(StrBuilder* b);

/**
 * Reads and appends all available data from file descriptor.
 *
 * Returns 1 on succes.
 * Returns 0 if memory cannot be allocated or if 'b' is NULL.
 * Returns (-errno) if reading fails.
 */
int strbuilder_add_fd(StrBuilder* b, int fd);

/** Returns false if memory cannot be allocated or if 'b' is NULL */
bool strbuilder_add(StrBuilder* b, const char* string);
/** Returns false if memory cannot be allocated or if 'b' is NULL */
bool strbuilder_add_char(StrBuilder* b, char c);
/** Returns false if memory cannot be allocated or if 'b' is NULL */
bool strbuilder_addf(StrBuilder* b, const char* format, ...);
/**
 * Adds string as path node, with separator apropriate for platform.
 * Returns false if memory cannot be allocated or if 'b' is NULL.
 */
bool strbuilder_add_path(StrBuilder* b, const char* node);
/** Returns false if memory cannot be allocated or if 'b' is NULL */
bool strbuilder_insert(StrBuilder* b, size_t pos, const char* string);
/** Returns false if memory cannot be allocated or if 'b' is NULL */
bool strbuilder_insert_char(StrBuilder* b, size_t pos, char c);
/** Returns false if memory cannot be allocated or if 'b' is NULL */
bool strbuilder_insertf(StrBuilder* b, size_t pos, const char* format, ...);
/** Removes up to 'count' characters from right of the string */
void strbuilder_rtrim(StrBuilder* b, size_t count);
/** Removes up to 'count' characters from left of the string */
void strbuilder_ltrim(StrBuilder* b, size_t count);
/**
 * Modifies string in place converting it to upper-case.
 * Returns true on success, what should be always.
 */
bool strbuilder_upper(StrBuilder* b);
/** As strbuilder_upper, but converts to lower case */
bool strbuilder_lower(StrBuilder* b);

/**
 * Returns true if any _add*, _insert*, _prepend* (etc) method failed at any
 * point. This can be used to check for OOM error after adding multiple strings.
 * Also returns true if 'b' is NULL.
 */
bool strbuilder_failed(StrBuilder* b);

/**
 * Escapes any instance of any character in 'chars' in stored string with 'escape_char'.
 * Returns false if memory for operation cannot be allocated, 'b' is NULL or 'escape_char' is 0.
 */
bool strbuilder_escape(StrBuilder* b, const char* chars, char escape_char);

/**
 * Replaces any instance of character 'x' with character 'y'
 * 'y' may be NULL, in which case, cuts string after first occurence of 'x'
 */
void strbuilder_replace(StrBuilder* b, char x, char y);

/**
 * Adds string while escaping any instance of characters in 'chars' with 'escape_char'.
 * Returns false if memory for operation cannot be allocated, 'b' is NULL or 'escape_char' is 0.
 */
bool strbuilder_add_escaped(StrBuilder* b, const char* string, const char* chars, char escape_char);

/**
 * While trailing character of string is one of 'chars', removes last character
 */
void strbuilder_rstrip(StrBuilder* b, const char* chars);

/**
 * Adds all strings from array to builder. Empty strings and NULLs are ignored.
 * If 'glue' is not NULL, it's used as separator between joined items.
 *
 * Returns false if allocation fails; In such case, string in builder is not modified.
 */
bool strbuilder_join(StrBuilder* b, const char* array[], size_t size, const char* glue);


/**
 * Iterates over iterator (as defined in iterable.h) and adds every item in it
 * converting it to string using provided conversion function. Empty strings are
 * ignored.
 *
 * If 'glue' is not NULL, it's used as separator between joined items.
 * Values returned by convert_fn is free()'d
 *
 * Returns false if allocation fails; That may happen if convert_fn returns NULL
 * for any argument or if allocation of string fails at any given point. In such
 * case, string in builder is not modified.
 * Also returns false if 'b' is NULL
 */
#define strbuilder_add_all(b, iterator, convert_fn, glue) _strbuilder_add_all(b, \
		iterator, (iterator)->has_next, (iterator)->get_next, \
		(char*(*)(void* item))convert_fn, glue)
bool _strbuilder_add_all(StrBuilder* b, void* iterator, bool(*has_next)(void* i),
	void*(*get_next)(void *i), char*(*convert_fn)(void* item), const char* glue);

/**
 * Braindead templating 'engine':
 * - Goes through entire string stored in builder, searching for "keywords"
 * - By default, keyword is any string in curly braces that doesn't contain
 *   newline or whitespace space characters, up to matchong closing curly brace.
 *      ex.: "this is not a keyword {this_is} but {this is not} and {this+keyword=ok}"
 * - 'chars' argument, if not NULL, overrides above - 1st and 2nd characters
 *   are used braces (and they can be same) and any other characters after are
 *   "whitespace" that marks keyword as invalid and thus skipped.
 * - For every keyword found, calls callback and replaces keyword with string
 *   it returns.
 * - If everything goes well, returns 1.
 *
 * Callback is called with every keyword found as parameter (excluding braces)
 * and is expected to return string that should keyword be replaced with.
 * Then, if free_cb is set, it's called to free memory allocated for used string.
 *
 * If callback returns NULL, templating is interrupted and function returns
 * value set in err_return (which is 0 by default). String stored in builder
 * stays half-way modified in such case.
 *
 * If memory allocation fails at any given point, function returns 0, but string
 * stored in builder is left half-modified as well.
 * If passed StrBuilder 'b' is NULL, returns 0 without changing anything.
 */
int strbuilder_template(StrBuilder* b,
		char* (*callback)(const char* keyword, int* err_return, void* userdata),
		void (*free_cb)(char* string, void* userdata),
		const char* chars,
		void* userdata);

/**
 * Deallocates StrBuilder and returns string it generated.
 * Returned string has to be deallocated manually.
 */
char* strbuilder_consume(StrBuilder* b);

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"

/** Returns value without deallocating builder. Returned string should not be changed or deallocated */
static inline const char* strbuilder_get_value(StrBuilder* b) {
	if (b->value == NULL) return "";
	return b->value;
}

/** Returns length of builder value */
static inline size_t strbuilder_len(StrBuilder* b) {
	return b->length;
}

#pragma GCC diagnostic pop

/** Shortcut to create copy of string. Returns NULL if memory cannot be allocated */
char* strbuilder_cpy(const char* src);
/** Shortcut to create new string out of given format. Returns NULL if memory cannot be allocated */
char* strbuilder_fmt(const char* format, ...);

