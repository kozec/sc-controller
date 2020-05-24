#define LOG_TAG "Daemon"
#include "scc/utils/logging.h"
#include "scc/utils/hashmap.h"
#include "scc/utils/assert.h"
#include "scc/input_test.h"
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

map_t loaded_drivers = NULL;


static void initialize_driver(Daemon* d, const char* filename, enum DirverInitMode mode) {
	char error[256];
	extlib_t lib = NULL;
	char* nice_name = malloc(1 + strlen(filename));
	if (nice_name == NULL) {
		LERROR("Failed to allocate memory");
		goto initialize_driver_end;
	}
	strcpy(nice_name, filename + strlen(FILENAME_PREFIX));
	nice_name[strlen(nice_name) - strlen(FILENAME_SUFFIX)] = 0;
	
	if (sccd_drivers_get_by_name(nice_name) != NULL) {
		WARN("Duplicate driver name: '%s'. Skipping %s", nice_name, filename);
		goto initialize_driver_end;
	}
	
	lib = scc_load_library(SCLT_DRIVER, FILENAME_PREFIX, nice_name, error);
	if (lib == NULL) {
		LERROR("Failed to load '%s': %s", nice_name, error);
		goto initialize_driver_end;
	}
	scc_driver_init_fn init_fn = (scc_driver_init_fn)scc_load_function(lib, "scc_driver_init", error);
	if (init_fn == NULL) {
		LERROR("Failed to load 'scc_driver_init' function from '%s': %s", nice_name, error);
		scc_close_library(lib);
		goto initialize_driver_end;
	}
	
	Driver* drv = init_fn(d);
	if (drv == NULL) {
		LERROR("Failed to load '%s'", nice_name);
		scc_close_library(lib);
		goto initialize_driver_end;
	}
	if (mode == DIMODE_LIST_DEVICES_ONLY) {
		if ((drv->input_test == NULL) || (drv->input_test->list_devices == NULL))
			goto initialize_driver_unload;
	} else {
		if ((drv->start != NULL) && !drv->start(drv, d))
			goto initialize_driver_unload;
	}
	if (MAP_OK != hashmap_put(loaded_drivers, nice_name, drv)) {
		LERROR("Failed to load '%s': out of memory", nice_name);
		goto initialize_driver_unload;
	}
	goto initialize_driver_end;
	
initialize_driver_unload:
	if (drv->unload != NULL)
		drv->unload(drv, d);
	scc_close_library(lib);
initialize_driver_end:
	free(nice_name);
}

void sccd_drivers_list_devices(Daemon* d, const controller_available_cb cb) {
	HashMapIterator it = iter_get(loaded_drivers);
	FOREACH(const char*, name, it) {
		Driver* drv = NULL;
		if (MAP_OK != hashmap_get(loaded_drivers, name, (void*)&drv))
			continue;
		if ((drv->input_test == NULL) || (drv->input_test->list_devices == NULL))
			continue;
		drv->input_test->list_devices(drv, d, cb);
	}
	iter_free(it);
}

void sccd_drivers_init(Daemon* d, enum DirverInitMode mode) {
	INFO("Initializing drivers...");
	DIR *dir;
	struct dirent *ent;
	ASSERT(NULL != (loaded_drivers = hashmap_new()));
	if ((dir = opendir(scc_drivers_path())) == NULL) {
		// Failed to open directory
		LERROR("Failed to enumerate '%s': %s", scc_drivers_path(), strerror(errno));
		return;
	}
	while ((ent = readdir(dir)) != NULL) {
		bool is_driver = (strstr(ent->d_name, FILENAME_SUFFIX) == ent->d_name + strlen(ent->d_name) - strlen(FILENAME_SUFFIX));
		is_driver = is_driver && (strstr(ent->d_name, FILENAME_PREFIX) == ent->d_name);
		if (is_driver)
			initialize_driver(d, ent->d_name, mode);
	}
	closedir (dir);
}

Driver* sccd_drivers_get_by_name(const char* driver_name) {
	void* drv = NULL;
	if (MAP_OK == hashmap_get(loaded_drivers, driver_name, &drv))
		return (Driver*)drv;
	return NULL;
}

