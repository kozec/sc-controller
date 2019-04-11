#pragma once
#include "scc/utils/traceback.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef void (*logging_handler)(const char* tag, const char* filename, int level, const char* message);

/**
 * Sets log handler, function that's responsible for getting logged messages to screen
 * (or to any other output file or device)
 * Returns previously set logging_handler.
 */
logging_handler logging_set_handler(logging_handler new_handler);

#define LOG_TAG_LEN 12

typedef enum {
	_LLV_DDEBUG			= 0,	// Lower-than-debug. Level that will be turned off in release.
	_LLV_DWARN			= 1,	// Warning, but only if debugging
	_LLV_DEBUG			= 2,
	_LLV_INFO			= 3,
	_LLV_WARN			= 4,
	_LLV_ERROR			= 5,
} _LogLevel;

void _log(const char* tag, const char* filename, _LogLevel lvl, const char* fmt, ...);

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-variable"
#ifdef LOG_TAG
#define DDEBUG(fmt, ...)	_log(LOG_TAG, NULL, _LLV_DDEBUG,	fmt, ##__VA_ARGS__ )
#define DEBUG(fmt, ...)		_log(LOG_TAG, NULL, _LLV_DEBUG,		fmt, ##__VA_ARGS__ )
#define DWARN(fmt, ...)		_log(LOG_TAG, NULL, _LLV_DWARN,		fmt, ##__VA_ARGS__ )
#define INFO(fmt, ...)		_log(LOG_TAG, NULL, _LLV_INFO,		fmt, ##__VA_ARGS__ )
/** LOG is same as INFO */
#define LOG(fmt, ...)		_log(LOG_TAG, NULL, _LLV_INFO,		fmt, ##__VA_ARGS__ )
#define WARN(fmt, ...)		_log(LOG_TAG, NULL, _LLV_WARN,		fmt, ##__VA_ARGS__ )
#define LERROR(fmt, ...)	_log(LOG_TAG, NULL, _LLV_ERROR	,	fmt, ##__VA_ARGS__ )
#else
#define __FILENAME__ (strrchr(__FILE__, '/') ? strrchr(__FILE__, '/') + 1 : __FILE__)
#define DDEBUG(fmt, ...)	_log(NULL, __FILENAME__, _LLV_DDEBUG,	fmt, ##__VA_ARGS__ )
#define DEBUG(fmt, ...)		_log(NULL, __FILENAME__, _LLV_DEBUG,	fmt, ##__VA_ARGS__ )
#define DWARN(fmt, ...)		_log(NULL, __FILENAME__, _LLV_DWARN,	fmt, ##__VA_ARGS__ )
#define INFO(fmt, ...)		_log(NULL, __FILENAME__, _LLV_INFO,	 	fmt, ##__VA_ARGS__ )
/** LOG is same as INFO */
#define LOG(fmt, ...)		_log(NULL, __FILENAME__, _LLV_INFO,	 	fmt, ##__VA_ARGS__ )
#define WARN(fmt, ...)		_log(NULL, __FILENAME__, _LLV_WARN,	 	fmt, ##__VA_ARGS__ )
#define LERROR(fmt, ...)	_log(NULL, __FILENAME__, _LLV_ERROR, 	fmt, ##__VA_ARGS__ )
#endif
#pragma GCC diagnostic pop

/**
 * Displays "[FATAL] blah blah blah" message, prints stack trace if possible
 * and dies.
 */
#define FATAL(fmt, ...) do {									\
	fprintf(stderr, "\n[FATAL] " fmt "\n", ##__VA_ARGS__);		\
	traceback_print_header();									\
	traceback_print(1);											\
	exit(1);													\
} while (0)

