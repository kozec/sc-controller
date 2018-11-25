#include "scc/utils/logging.h"
#include <stdarg.h>
#include <stdio.h>

#define str(a) #a
#define xstr(a) str(a)

#ifndef _WIN32
static const char* red    = "\x1b[31m";
static const char* orange = "\x1b[33m";
static const char* gray   = "\x1b[90m";
#define RESET "\x1b[0m"
#else
static const char* red    = "";
static const char* orange = "";
static const char* gray   = "";
#define RESET ""
#endif
static const char* levels = "dWDIWE";
static char tag_padded[LOG_TAG_LEN + 1];

void _log(const char* tag, const char* filename, _LogLevel lvl, const char* fmt, ...) {
	va_list args;
	FILE* target = stdout;
	const char* color = "";
	if (lvl >= _LLV_WARN) {
		color = red;
		target = stderr;
	} else if (lvl == _LLV_DWARN) {
		color = orange;
		target = stderr;
	} else if ((lvl == _LLV_DEBUG) || (lvl == _LLV_DDEBUG)) {
		color = gray;
	}
	
	snprintf(tag_padded, LOG_TAG_LEN + 1, "%s", tag?tag:filename);
	fprintf(target, "[%c] %s%-" xstr(LOG_TAG_LEN) "s ", *(levels + lvl), color, tag_padded);
	va_start(args, fmt);
	vfprintf(target, fmt, args);
	va_end (args);
	fprintf(target, RESET "\n");
	fflush(target);
}
