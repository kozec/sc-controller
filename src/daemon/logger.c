/*
 * SC Controller - Daemon - logger
 * Logger allocates chunk of memory and stores logs in it, so they can later be
 * sent to client.
 */
#define LOG_TAG "log"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "daemon.h"

#define BUFFER_SIZE		20480	/* 20kB */
static logging_handler original = NULL;
static char* buffer = NULL;
static size_t used = 0;
static const char* OOM = "(oom. failed to store message)";

/** Removes first message from buffer */
static void sccd_logger_unshift_message() {
	char* next = memchr(buffer, '\n', BUFFER_SIZE);
	if ((next == NULL) || (next == buffer)) {
		// There is only one message or buffer is horribly broken. Just wipe it out.
		buffer[0] = 0;
		used = 0;
	} else {
		size_t len = next - buffer;
		memmove(buffer, next, used + 1 - len);
		used -= len;
	}
}

static void sccd_logger_log(const char* tag, const char* filename, int level, const char* message) {
	if (original != NULL)
		original(tag, filename, level, message);
	char* msg = strbuilder_fmt("%i %s %s", level, tag, message);
	if (msg == NULL) msg = OOM;
	size_t len = strlen(msg);
	if (len >= BUFFER_SIZE) {
		WARN("Failed to store log message: message too long");
	} else {
		while (used + len >= BUFFER_SIZE)
			sccd_logger_unshift_message();
		strncpy(buffer + used, msg, len);
		if (used != 0)
			*(buffer + used - 1) = '\n';
		used += len + 1;
	}
	if (msg != OOM) free(msg);
}

const char* sccd_logger_get_log() {
	return buffer;
}

void sccd_logger_init(bool log_to_stdout) {
	buffer = malloc(BUFFER_SIZE);
	if (buffer == NULL) {
		LERROR("Failed to initialize logger storage: Out of memory");
	} else {
		original = logging_set_handler(sccd_logger_log);
		if (!log_to_stdout) original = NULL;
	}
}

