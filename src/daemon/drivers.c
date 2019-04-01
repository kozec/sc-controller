#define LOG_TAG "Daemon"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/tools.h"
#include "daemon.h"
#include <string.h>
#include <dirent.h>

#ifdef _WIN32
#include <windows.h>
#define FILENAME_PREFIX "libscc-drv-"
#define FILENAME_SUFFIX ".dll"
#else
#include <dlfcn.h>
#define FILENAME_PREFIX "libscc-drv-"
#define FILENAME_SUFFIX ".so"
#endif


static void initialize_driver(Daemon* d, const char* path, const char* filename) {
	char* full_path = malloc(2 + strlen(path) + strlen(filename));
	char* nice_name = malloc(1 + strlen(filename));
	if ((full_path == NULL) || (nice_name == NULL)) {
		LERROR("Failed to allocate memory");
		goto initialize_driver_end;
	}
	sprintf(full_path, "%s/%s", path, filename);
	strcpy(nice_name, filename + strlen(FILENAME_PREFIX));
	nice_name[strlen(nice_name) - strlen(FILENAME_SUFFIX)] = 0;
	
	// TODO: Allow disabling drivers
#ifdef _WIN32
	const char* error_message = "Failed to load '%s': Windows error 0x%x";
	HMODULE mdl = NULL;
	mdl = LoadLibrary(full_path);
	if (mdl == NULL) goto initialize_driver_dlerror;
	scc_driver_init_fn init_fn = (scc_driver_init_fn)GetProcAddress(mdl, "scc_driver_init");
	if (init_fn == NULL) {
		error_message = "Failed to load 'scc_driver_init_fn' function from '%s': Windows error 0x%x";
		goto initialize_driver_dlerror;
	}
#else
	void* img = NULL;
	img = dlopen(full_path, RTLD_LAZY);
	if (img == NULL) goto initialize_driver_dlerror;
	scc_driver_init_fn init_fn = dlsym(img, "scc_driver_init");
	if (init_fn == NULL) goto initialize_driver_dlerror;
#endif
	
	Driver* drv = init_fn(d);
	if (drv == NULL) {
		LERROR("Failed to load '%s'", nice_name);
		goto initialize_driver_fail;
	}
	// TODO: add driver
	goto initialize_driver_end;
initialize_driver_dlerror:
#ifdef _WIN32
	while (0) {};	// empty statement so label above is valid
	DWORD err = GetLastError();
	LERROR(error_message, nice_name, err);
initialize_driver_fail:
	if (mdl != NULL)
		FreeLibrary(mdl);
#else
	LERROR("Failed to load '%s': %s", nice_name, dlerror());
initialize_driver_fail:
	if (img != NULL)
		dlclose(img);
#endif
initialize_driver_end:
	free(full_path);
	free(nice_name);
}

void sccd_drivers_init() {
	Daemon* d = get_daemon();
	INFO("Initializing drivers...");
	// TODO: This path should be somehow configurable or determined on runtime
#ifdef _WIN32
	const char* path = strbuilder_fmt("%s\\..\\drivers", scc_get_share_path());
#elif defined(__BSD__)
	const char* path = "build-bsd/src/daemon/drivers";
#else
	const char* path = "build/src/daemon/drivers";
#endif
	DIR *dir;
	struct dirent *ent;
	if ((dir = opendir (path)) == NULL) {
		// Failed to open directory
		LERROR("Failed to enumerate '%s'", path);
		return;
	}
	/* print all the files and directories within directory */
	while ((ent = readdir (dir)) != NULL) {
		bool is_driver = (strstr(ent->d_name, FILENAME_SUFFIX) == ent->d_name + strlen(ent->d_name) - strlen(FILENAME_SUFFIX));
		is_driver = is_driver && (strstr(ent->d_name, FILENAME_PREFIX) == ent->d_name);
		if (is_driver)
			initialize_driver(d, path, ent->d_name);
	}
	closedir (dir);
}
