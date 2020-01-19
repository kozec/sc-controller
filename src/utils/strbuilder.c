#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <stdio.h>
#include <errno.h>

#define STRBUILDER_ALOC_INC 16
#define STRBUILDER_FMT_SIZE 1024
#define STRBUILDER_READ_SIZE 1024

StrBuilder* strbuilder_new() {
	StrBuilder* b = malloc(sizeof(StrBuilder));
	if (b == NULL) return NULL;
	
	b->allocation = 0;
	b->failed = false;
	b->length = 0;
	b->value = NULL;
	b->next = NULL;
	return b;
}


void strbuilder_free(StrBuilder* b) {
	if (b != NULL) {
		free(b->value);
		free(b);
	}
}


void strbuilder_clear(StrBuilder* b) {
	if (b == NULL) return;
	if (b->length == 0) return;
	b->failed = false;
	b->value[0] = 0;
	b->next = b->value;
	b->length = 0;
}


char* strbuilder_consume(StrBuilder* b) {
	if (b == NULL) return NULL;
	char* str = b->value;
	if (str == NULL) {
		// Ugly hack to reuse StrBuilder data as empty string :)
		// Saves one allocation and thus cannot fail when running out of memory.
		str = (char*)b;
		str[0] = 0;
	} else {
		free(b);
	}
	return str;
}


bool strbuilder_failed(StrBuilder* b) {
	return (b == NULL) || (b->failed);
}


/** Returns false on failure */
static bool strbuilder_realloc(StrBuilder* b, size_t new_length) {
	if (new_length < b->allocation)
		return true;
	char* reallocated = realloc(b->value, new_length + 1);
	if (reallocated == NULL) {
		b->failed = true;
		return false;
	}
	b->next = (b->next == NULL) ? reallocated : (reallocated + (b->next - b->value));
	b->value = reallocated;
	b->allocation = new_length;
	return true;
}


bool strbuilder_add(StrBuilder* b, const char* string) {
	if (b == NULL) return false;
	size_t len = strlen(string);
	if (len == 0)
		return true;
	if (b->length + len > b->allocation)
		if (!strbuilder_realloc(b, b->length + len))
			return false;
	strcpy(b->next, string);
	b->next += len;
	b->length += len;
	return true;
}


bool strbuilder_add_char(StrBuilder* b, char c) {
	// TODO: Maybe optimize this
	char buff[] = { c, 0 };
	return strbuilder_add(b, buff);
}


static void move_chars_forward(StrBuilder* b, size_t pos, size_t offset) {
	// This function assumes that space for new character is already allocated
	if ((b->length - pos < 1) || (offset < 1))
		// Nothing to do
		return;
	memmove(b->value + pos + offset, b->value + pos, b->length - pos);
	b->length += offset;
	b->next += offset;
	*b->next = 0;
}


bool strbuilder_addf(StrBuilder* b, const char* format, ...) {
	int r;
	size_t len;
	va_list args;
	size_t free_space = b->allocation - b->length;
	if (b == NULL) return false;
	if (free_space < 4) {
		if (!strbuilder_realloc(b, b->allocation + STRBUILDER_ALOC_INC))
			return false;
		free_space = b->allocation - b->length;
	}
	
	va_start (args, format);
	r = vsnprintf(b->next, free_space + 1, format, args);
	if (r < 0)
		goto strbuilder_addf_this_shouldnt_ever_happen;
	len = (size_t)r;
	va_end (args);
	
	if (len >= free_space + 1) {
		// too much text, builder has to be expanded and written again
		if (!strbuilder_realloc(b, b->length + len + STRBUILDER_ALOC_INC))
			return false;
		free_space = b->allocation - b->length;
		va_start (args, format);
		r = vsnprintf(b->next, free_space + 1, format, args);
		if (r < 0)
			goto strbuilder_addf_this_shouldnt_ever_happen;
		len = (size_t)r;
		va_end (args);
	}
	
	b->next += len;
	b->length += len;
	b->value[b->length] = 0;
	return true;
strbuilder_addf_this_shouldnt_ever_happen:
	fprintf(stderr, "***** strbuilder_addf: Failed to apply format '%s': %i\n", format, r);
	return false;
}


bool strbuilder_add_path(StrBuilder* b, const char* node) {
	if (b == NULL) return false;
	if ((b->length > 0) && (*(b->next-1) != '/')&& (*(b->next-1) != '\\')) {
#ifndef _WIN32
		if (!strbuilder_add(b, "/")) return false;
#else
		if (!strbuilder_add(b, "\\")) return false;
#endif
	}
	return strbuilder_add(b, node);
}


int strbuilder_add_fd(StrBuilder* b, int fd) {
	if (b == NULL) return false;
	size_t original_len = b->length;
	int err = 0;
	while (1) {
		if (!strbuilder_realloc(b, b->length + STRBUILDER_READ_SIZE))
			break;
		ssize_t len = read(fd, b->next, STRBUILDER_READ_SIZE - 1);
		if (len < 0) {
			err = -errno;
			break;
		} else if (len == 0) {
			// EOF reached
			*b->next = 0;
			return 1;
		}
		b->next += len;
		b->length += len;
	}
	// Reaches here only on error
	b->next = b->value + original_len;
	b->failed = true;
	*b->next = 0;
	return err;
}


int strbuilder_template(StrBuilder* b,
			char* (*callback)(const char* keyword, int* err_return, void* userdata),
			void (*free_cb)(char* string, void* userdata),
			const char* chars,
			void* userdata) {
	// TODO: removing and replacing part can be optimized
	// Check
	if (b == NULL) return 0;
	// Setup
	int err = 0;
	*b->next = 0;	// just to be sure
	char* start = b->value;
	if (chars == NULL) chars = "{} \t\r\n";
	char open_brace = chars[0];
	char close_brace = chars[1];
	const char* invalid_chars = &chars[2];
	while (1) {
		// Main loop, exits when start == NULL
		start = strchr(start + 1, open_brace);
		if (start == NULL)
			// No more {'s, we are done here
			return 1;
		char* end = strchr(start + 1, close_brace);
		if (end != NULL) {
			*end = 0;	// Mark '}' as end of string
			end ++;		// ... and step over it
		} else {
			// No } matching {. }
			end = b->next - 1;
		}
		// Check validity
		bool valid = true;
		for (const char* invalid_char = invalid_chars; *invalid_char != 0; invalid_char++) {
			if (strchr(start + 1, *invalid_char) != NULL) {
				valid = false;
				break;
			}
		}
		if (!valid) {
			if (end != b->next - 1)
				*(end-1) = close_brace;
			continue;
		}
		// Compute replacement
		char* replacement = callback(start + 1, &err, userdata);
		if (replacement == NULL) {
			// Hey, we just failed miserably.
			if (end != b->next - 1)
				*(end-1) = close_brace;
			return err;
		}
		// Remove keyword from string
		b->length -= end - start;
		if (end != b->next - 1) {
			memmove(start, end, b->next - end);
			b->next -= end - start;
		} else {
			b->next = start;
		}
		*b->next = 0;
		
		// Insert replacement
		bool inserted = strbuilder_insert(b, start - b->value, replacement);
		if (free_cb != NULL)
			free_cb(replacement, userdata);
		if (!inserted)
			return 0;
	}
}


bool strbuilder_insert(StrBuilder* b, size_t pos, const char* string) {
	if (b == NULL) return false;
	size_t free_space = b->allocation - b->length;
	size_t needed = strlen(string);
	if (needed > free_space)
		if (!strbuilder_realloc(b, b->allocation + needed + STRBUILDER_ALOC_INC))
			return false;
	move_chars_forward(b, pos, needed);
	memcpy(b->value + pos, string, needed);
	return true;
}


bool strbuilder_insert_char(StrBuilder* b, size_t pos, char c) {
	if (b == NULL) return false;
	size_t free_space = b->allocation - b->length;
	if (free_space < 1)
		if (!strbuilder_realloc(b, b->allocation + STRBUILDER_ALOC_INC))
			return false;
	move_chars_forward(b, pos, 1);
	*(b->value + pos) = c;
	return true;
}


bool strbuilder_insertf(StrBuilder* b, size_t pos, const char* format, ...) {
	// TODO: This could be optimized to not use buf and save one allocation
	if (b == NULL) return false;
	int r;
	va_list args;
	
	va_start (args, format);
	r = vsnprintf(NULL, 0, format, args);
	if (r < 0)
		goto strbuilder_insertf_this_shouldnt_ever_happen;
	va_end (args);
	
	char* buf = malloc((size_t)r + 1);
	va_start (args, format);
	r = vsnprintf(buf, (size_t)r + 1, format, args);
	if (r < 0)
		goto strbuilder_insertf_this_shouldnt_ever_happen;
	va_end (args);
	
	if (!strbuilder_insert(b, pos, buf)) {
		free(buf);
		return false;
	}
	
	free(buf);
	return true;
strbuilder_insertf_this_shouldnt_ever_happen:
	fprintf(stderr, "***** strbuilder_insertf: Failed to apply format '%s': %i\n", format, r);
	return false;
}


void strbuilder_rtrim(StrBuilder* b, size_t count) {
	if (b == NULL) return;
	if (count > b->length) {
		b->length = 0;
		b->value[0] = 0;
	} else {
		b->length -= count;
		b->next -= count;
		*b->next = 0;
	}
}

void strbuilder_ltrim(StrBuilder* b, size_t count) {
	if (b == NULL) return;
	count = min(b->length, count);
	if (count < 1) return;
	memmove(b->value, b->value + count, b->length - count);
	b->length -= count;
	b->next -= count;
	*b->next = 0;
}

bool strbuilder_upper(StrBuilder* b) {
	if (b == NULL) return false;
	for (size_t i=0; i<b->length; i++)
		b->value[i] = toupper(b->value[i]);
	return true;
}

bool strbuilder_lower(StrBuilder* b) {
	if (b == NULL) return false;
	for (size_t i=0; i<b->length; i++)
		b->value[i] = tolower(b->value[i]);
	return true;
}

bool strbuilder_escape(StrBuilder* b, const char* chars, char escape_char) {
	if (b == NULL) return false;
	if (escape_char == 0) return false;
	// Count space needed 1st
	size_t space_needed = 0;
	for (size_t i=0; i<b->length; i++)
		if (strchr(chars, b->value[i]) != NULL)
			space_needed++;
	
	if (!strbuilder_realloc(b, b->length + space_needed + 1))
		return false;
	
	for (size_t i=0; i<b->length; i++) {
		if (strchr(chars, b->value[i]) != NULL) {
			move_chars_forward(b, i, 1);
			b->value[i] = escape_char;
			i++;
		}
	}
	return true;
}

void strbuilder_replace(StrBuilder* b, char x, char y) {
	if (b == NULL) return;
	
	for (size_t i=0; i<b->length; i++) {
		if (b->value[i] == x) {
			b->value[i] = y;
			if (y == 0) {
				b->length = i;
				return;
			}
		}
	}
}


bool strbuilder_add_escaped(StrBuilder* b, const char* string, const char* chars, char escape_char) {
	if (b == NULL) return false;
	if (escape_char == 0) return false;
	int len = strlen(string);
	for (int i=0; i<len; i++) {
		char c = string[i];
		if (strchr(chars, c) != NULL)
			strbuilder_add_char(b, escape_char);
		strbuilder_add_char(b, c);
		if (strbuilder_failed(b))
			return false;
	}
	return true;
}


void strbuilder_rstrip(StrBuilder* b, const char* chars) {
	if (b == NULL) return;
	while ((b->length > 0) && (strchr(chars, b->value[b->length - 1]) != NULL)) {
		b->length --;
		b->value[b->length] = 0;
	}
}


bool strbuilder_join(StrBuilder* b, const char* array[], size_t size, const char* glue) {
	if (b == NULL) return false;
	size_t original_length = b->length;
	bool needs_glue = false;
	for (size_t i=0; i<size; i++) {
		const char* str = array[i];
		if ((str == NULL) || (str[0] == 0))
			continue;
		if (needs_glue && (glue != NULL)) {
			if (!strbuilder_add(b, glue))
				goto strbuilder_join_fail;
		}
		if (!strbuilder_add(b, str))
			goto strbuilder_join_fail;
		needs_glue = true;
	}
	return true;
strbuilder_join_fail:
	b->length = original_length;
	b->value[b->length] = 0;
	return false;
}


bool _strbuilder_add_all(StrBuilder* b, void* iterator,
					bool(*has_next)(void* i),
					void*(*get_next)(void *i), char*(*convert_fn)(void* item),
					const char* glue) {
	if (b == NULL) return false;
	if (!has_next(iterator)) return true;
	size_t original_length = b->length;
	bool needs_glue = false;
	while (has_next(iterator)) {
		void* item = get_next(iterator);
		char* str = convert_fn(item);
		if (str == NULL)
			goto _strbuilder_add_all_fail;
		if (str[0] == 0) {
			free(str);
			continue;
		}
		if (needs_glue && (glue != NULL)) {
			if (!strbuilder_add(b, glue))
				goto _strbuilder_add_all_fail;
		}
		if (!strbuilder_add(b, str)) {
			free(str);
			goto _strbuilder_add_all_fail;
		}
		needs_glue = true;
		free(str);
	}
	return true;
_strbuilder_add_all_fail:
	b->length = original_length;
	b->value[b->length] = 0;
	return false;
}


char* strbuilder_cpy(const char* src) {
	if (src == NULL) return NULL;
	char* copy = malloc(strlen(src) + 1);
	if (copy == NULL) return NULL;
	strcpy(copy, src);
	return copy;
}


char* strbuilder_fmt(const char* format, ...) {
	va_list args;
	char* longbuffer;
	char buffer[STRBUILDER_FMT_SIZE];	// Should be enough most of the times
	va_start (args, format);
	size_t len = vsnprintf(&buffer[0], STRBUILDER_FMT_SIZE - 1, format, args);
	va_end (args);
	if (len < STRBUILDER_FMT_SIZE - 1)
		// Sucesfully fit to buffer, no allocation is needed
		return strbuilder_cpy(buffer);
	
	longbuffer = malloc(len + 1);
	if (longbuffer == NULL) return NULL;
	va_start (args, format);
	vsnprintf(longbuffer, len + 1, format, args);
	va_end (args);
	return longbuffer;
}

