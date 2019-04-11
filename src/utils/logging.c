#include "scc/utils/logging.h"
#include <stdarg.h>
#include <stdio.h>

#define MAX_MSG_LEN		1024

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

static void _default_log_helper(const char* tag, const char* filename, int lvl, FILE** target) {
	// Basically just code that would be common for default_log_handler and
	// branch of _log that doesn't end up calling log_hander at all
	*target = stdout;
	const char* color = "";
	if (lvl >= _LLV_WARN) {
		color = red;
		*target = stderr;
	} else if (lvl == _LLV_DWARN) {
		color = orange;
		*target = stderr;
	} else if ((lvl == _LLV_DEBUG) || (lvl == _LLV_DDEBUG)) {
		color = gray;
	}
	snprintf(tag_padded, LOG_TAG_LEN + 1, "%s", tag?tag:filename);
	fprintf(*target, "[%c] %s%-" xstr(LOG_TAG_LEN) "s ", *(levels + lvl), color, tag_padded);
}

/**
 * default_log_handler is not really used, but it's returned as original hander
 * from logging_set_handler method. If that method is not called at all,
 * version of logging code that doesn't need to allocate additional buffer for
 * log message is used.
 */
static void default_log_handler(const char* tag, const char* filename, int lvl, const char* msg) {
	FILE* target;
	_default_log_helper(tag, filename, lvl, &target);
	fwrite(msg, strlen(msg), 1, target);
	fprintf(target, RESET "\n");
	fflush(target);
}

static logging_handler current_handler = NULL;
static char* log_msg_buffer = NULL;

void _log(const char* tag, const char* filename, _LogLevel lvl, const char* fmt, ...) {
	va_list args;
	if (current_handler == NULL) {
		FILE* target;
		_default_log_helper(tag, filename, lvl, &target);
		
		va_start(args, fmt);
		vfprintf(target, fmt, args);
		va_end (args);
		fprintf(target, RESET "\n");
		fflush(target);
	} else {
		va_start(args, fmt);
		vsnprintf(log_msg_buffer, MAX_MSG_LEN, fmt, args);
		va_end (args);
		current_handler(tag, filename, lvl, log_msg_buffer);
	}
}


logging_handler logging_set_handler(logging_handler new_handler) {
	logging_handler original = current_handler;
	if (original == NULL)
		original = default_log_handler;
	if (log_msg_buffer == NULL) {
		log_msg_buffer = malloc(MAX_MSG_LEN);
		if (log_msg_buffer == NULL) {
			LERROR("logging_set_handler: Failed to allocate memory. Ignoring logging_set_handler request.");
			return original;
		}
	}
	current_handler = new_handler;
	return original;
}

