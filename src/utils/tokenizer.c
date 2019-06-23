#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/tokenizer.h"
#include "scc/parser.h"
#include <stdlib.h>
#include <string.h>

static const char* TOKEN_DELIMITERS = "\n\t ;,()'\\\"";

struct _Tokens {
	// Private version of Tokens
	Tokens			tokens;
	char			buffer[2];
	const char*		source;
	char*			copy;
	const char*		end;
	char*			i;
	bool			auto_skip_whitespace;
};


static bool tokens_has_next(void* _t) {
	struct _Tokens* t = container_of(_t, struct _Tokens, tokens);
	if (t->i > t->end)
		return false;
	if (*t->i == 0)
		if (t->source[t->i - t->copy] == 0)
			return false;
	return true;
}

static const char* grab_quoted(struct _Tokens* t) {
	char* rv = t->i;
	size_t skipped = 0;
	t->i++;
	while (*t->i != 0) {
		if (*t->i == '\\') {
			t->i++;
			switch (*t->i) {
			case 0:
				break;
			case 't':
				*(t->i - 1) = '\t';
				skipped ++;
				memmove(t->i, t->i+1, strlen(t->i));
				break;
			case 'n':
				*(t->i - 1) = '\n';
				skipped ++;
				memmove(t->i, t->i+1, strlen(t->i));
				break;
			case 'r':
				*(t->i - 1) = '\r';
				skipped ++;
				memmove(t->i, t->i+1, strlen(t->i));
				break;
			default:
				t->i--;
				skipped ++;
				memmove(t->i, t->i+1, strlen(t->i));
			}
			if (*(t->i) == rv[0]) {
				t->i ++;
				continue;
			}
		}
		if (*(t->i) == rv[0])
			break;
		t->i ++;
	}
	
	t->i ++;
	strcpy(t->i, t->source + (t->i - t->copy));
	*t->i = 0;
	t->i += skipped;
	return rv;
}

static const char* tokens_get_next(void* _t) {
	struct _Tokens* t = container_of(_t, struct _Tokens, tokens);
	if (*t->i == 0) {
		*t->i = t->source[t->i - t->copy];
	}
	const char* rv = t->buffer;
	if (strchr(TOKEN_DELIMITERS, *t->i) != NULL) {
		if ((*t->i == '"')||(*t->i == '\'')) {
			rv = grab_quoted(t);
		} else {
			t->buffer[0] = *t->i;
			t->i++;
		}
		if (t->auto_skip_whitespace)
			tokens_skip_whitespace(_t);
	} else {
		rv = strtok(t->i, TOKEN_DELIMITERS);
		t->i = (char*)rv + strlen(rv);
		if (t->auto_skip_whitespace)
			tokens_skip_whitespace(_t);
	}
	return rv;
}

char tokens_peek_char(Tokens* _t) {
	struct _Tokens* t = container_of(_t, struct _Tokens, tokens);
	if (t->i > t->end)
		return 0;
	if (*t->i == 0)
		return t->source[t->i - t->copy];
	return *t->i;
}

const char* tokens_get_rest(Tokens* _t) {
	struct _Tokens* t = container_of(_t, struct _Tokens, tokens);
	if (t->i > t->end)
		return "";
	if (*t->i == 0)
		return t->source + (t->i - t->copy);
	return t->i;
}

void tokens_skip_whitespace(Tokens* _t) {
	struct _Tokens* t = container_of(_t, struct _Tokens, tokens);
	char next = tokens_peek_char(_t);
	while ((next == ' ') || (next == '\t') || (next == '\n')) {
		t->i++;
		next = tokens_peek_char(_t);
	}
}

void tokens_auto_skip_whitespace(Tokens* _t) {
	struct _Tokens* t = container_of(_t, struct _Tokens, tokens);
	t->auto_skip_whitespace = true;
	tokens_skip_whitespace(_t);
}

void tokens_free(Tokens* _t) {
	struct _Tokens* t = container_of(_t, struct _Tokens, tokens);
	free(t->copy);
	free(t);
}

static void tokens_reset(void* _whatever) {
	FATAL("Tokens list cannot be reset");
}

Tokens* tokenize(const char* source) {
	struct _Tokens* t = malloc(sizeof(struct _Tokens));
	char* copy = malloc(strlen(source) + 1);
	if ((t == NULL) || (copy == NULL)) {
		free(t);
		free(copy);
		return NULL;
	}
	
	t->source = source;
	t->i = t->copy = strcpy(copy, source);
	t->buffer[1] = 0;
	t->end = t->copy + strlen(t->copy);
	t->auto_skip_whitespace = false;
	
	ITERATOR_INIT(&t->tokens, tokens_has_next, tokens_get_next, tokens_reset, NULL);
	return &t->tokens;
}
