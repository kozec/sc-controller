#define LOG_TAG "Daemon"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/tools.h"
#include "daemon.h"
#include <string.h>
#include <dirent.h>
#include <errno.h>

#ifdef _WIN32
#include <windows.h>
#define FILENAME_PREFIX "libscc-drv-"
#define FILENAME_SUFFIX ".dll"
#else
#include <dlfcn.h>
#define FILENAME_PREFIX "libscc-drv-"
#define FILENAME_SUFFIX ".so"
#endif


static void initialize_driver(Daemon* d, const char* filename) {
	char error[256];
	extlib_t lib = NULL;
	char* nice_name = malloc(1 + strlen(filename));
	if (nice_name == NULL) {
		LERROR("Failed to allocate memory");
		goto initialize_driver_end;
	}
	strcpy(nice_name, filename + strlen(FILENAME_PREFIX));
	nice_name[strlen(nice_name) - strlen(FILENAME_SUFFIX)] = 0;
	
	lib = scc_load_library(SCLT_DRIVER, FILENAME_PREFIX, nice_name, error);
	if (lib == NULL) {
		LERROR("Failed to load '%s': %s", nice_name, error);
		goto initialize_driver_end;
	}
	scc_driver_init_fn init_fn = (scc_driver_init_fn)scc_load_function(lib, "scc_driver_init", error);
	if (init_fn == NULL) {
		LERROR("Failed to load 'scc_driver_init_fn' function from '%s': %s", nice_name, error);
		scc_close_library(lib);
		goto initialize_driver_end;
	}
	
	Driver* drv = init_fn(d);
	if (drv == NULL) {
		LERROR("Failed to load '%s'", nice_name);
		scc_close_library(lib);
		goto initialize_driver_end;
	}
	// TODO: add driver
initialize_driver_end:
	free(nice_name);
}

void sccd_drivers_init() {
	Daemon* d = get_daemon();
	INFO("Initializing drivers...");
	DIR *dir;
	struct dirent *ent;
	if ((dir = opendir(scc_drivers_path())) == NULL) {
		// Failed to open directory
		LERROR("Failed to enumerate '%s': %s", scc_drivers_path(), strerror(errno));
		return;
	}
	while ((ent = readdir(dir)) != NULL) {
		bool is_driver = (strstr(ent->d_name, FILENAME_SUFFIX) == ent->d_name + strlen(ent->d_name) - strlen(FILENAME_SUFFIX));
		is_driver = is_driver && (strstr(ent->d_name, FILENAME_PREFIX) == ent->d_name);
		if (is_driver)
			initialize_driver(d, ent->d_name);
	}
	closedir (dir);
}

