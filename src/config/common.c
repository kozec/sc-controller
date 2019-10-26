/**
 * SC Controller - code common for all platforms.
 */
#define LOG_TAG "config"
#include "scc/utils/logging.h"
#include "scc/tools.h"
#include "config.h"
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>


Config* config_init() {
	// TODO: Maybe re-enable this on Windows for other files
	if (access(scc_get_config_path(), F_OK) != 0) {
#ifdef _WIN32
		if (mkdir(scc_get_config_path()) != 0) {
#else
		if (mkdir(scc_get_config_path(), 0700) != 0) {
#endif
			LERROR(
				"Failed to create config directory '%s': %s",
				scc_get_config_path(),
				strerror(errno)
			);
			return NULL;
		}
		LOG("Created '%s'", scc_get_config_path());
	}
	if (access(scc_get_config_path(), R_OK | W_OK | X_OK) != 0) {
		LERROR(
			"Cannot access config directory '%s'. Please, make sure you are its owner and it's not read-only.",
			scc_get_config_path()
		);
		return NULL;
	}
	
	Config* c = config_load();
	if (c == NULL) return NULL;
	if (config_fill_defaults(c))
		config_save(c);
	return c;
}

