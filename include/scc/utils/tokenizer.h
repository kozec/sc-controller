/*
 * SC Controller - Tokenizer
 * 
 * Breaks string into tokens (using strtok) and returns Iterable structure.
 */
#pragma once
#include "scc/utils/iterable.h"

typedef struct Tokens {
	ITERATOR_STRUCT_HEADER(const char*)
} Tokens;

/**
 * Breaks string into tokens and returns structure that can be used as Iterator
 * as defined in iterable.h (ie. iter_has_next and iter_next works).
 *
 * Note that 'source' string can't be deallocated until before returned Tokens
 * is freed (using tokens_free);
 *
 * Returns NULL if memory cannot be allocated.
 */
Tokens* tokenize(const char* source);

/**
 * Skips as many characters as needed to ensure that next next call
 * to iter_next() will not return white space character.
 */
void tokens_skip_whitespace(Tokens* tokens);

/**
 * Once enabled, whitespace is automatically skipped after every parsed token.
 */
void tokens_auto_skip_whitespace(Tokens* tokens);

/** Return next character (not token) or 0 if end of string was reached */
char tokens_peek_char(Tokens* t);

/** Retrieves rest of string (everything from last parsed token to end) */
const char* tokens_get_rest(Tokens* t);

/** Deallocates Tokens instance */
void tokens_free(Tokens* t);
