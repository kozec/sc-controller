#include "scc/utils/strbuilder.h"
#include "scc/tools.h"
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#define FILENAME_SUFFIX ".dll"
#else
#include <dlfcn.h>
#include <errno.h>
#define FILENAME_SUFFIX ".so"
#endif


/** Returns 1 on success */
static int make_path(SCCLibraryType type, StrBuilder* sb, char* error_return) {
	switch (type) {
	case SCLT_GENERATOR:
#ifdef _WIN32
		// TODO: This path should be somehow configurable or determined on runtime
		strbuilder_add(sb, scc_get_exe_path());
		strbuilder_add_path(sb, "..\\menu-generators");
#elif defined(__BSD__)
		strbuilder_add(sb, "build-bsd/src/menu-generators");
#else
		strbuilder_add(sb, "build/src/menu-generators");
#endif
		return 1;
	case SCLT_DRIVER:
		strbuilder_add(sb, scc_drivers_path());
		return 1;
	case SCLT_OSD_MENU_PLUGIN:
		strbuilder_add(sb, "build/src/osd/menus");
		return 1;
	}
	if (error_return != NULL)
		strncpy(error_return, "Unsupported library type", 255);
	return 0;
}


extlib_t scc_load_library(SCCLibraryType type, const char* prefix, const char* lib_name, char* error_return) {
	// Build filename
	StrBuilder* sb = strbuilder_new();
	if (!make_path(type, sb, error_return))
		return NULL;
	if (prefix != NULL) {
		strbuilder_add_path(sb, prefix);
		strbuilder_add(sb, lib_name);
	} else {
		strbuilder_add_path(sb, lib_name);
	}
	strbuilder_add(sb, FILENAME_SUFFIX);
	if (strbuilder_failed(sb)) {
		strbuilder_free(sb);
		if (error_return != NULL)
			strncpy(error_return, "Out of memory", 255);
		return NULL;
	}
	char* filename = strbuilder_consume(sb);
	
	// Load library
#ifdef _WIN32
	extlib_t lib = = LoadLibrary(filename);
	free(filename);
	if (lib == NULL) {
		DWORD err = GetLastError();
		if (error_return != NULL)
			snprintf(error_return, 255, "Windows error 0x%x", err);
		return NULL;
	}
#else
	extlib_t lib = dlopen(filename, RTLD_LAZY);
	free(filename);
	if (lib == NULL) {
		if (error_return != NULL)
			strncpy(error_return, dlerror(), 255);
		return NULL;
	}
#endif
	return lib;
}


void* scc_load_function(extlib_t lib, const char* name, char* error_return) {
#ifdef _WIN32
	void* fn = (scc_menu_generator_generate_fn)GetProcAddress(lib, name);
	if (fn == NULL) {
		DWORD err = GetLastError();
		if (error_return != NULL)
			snprintf(error_return, 255, "Windows error 0x%x", err);
		return NULL
	}
#else
	void* fn = dlsym(lib, name);
	if (fn == NULL) {
		if (error_return != NULL)
			strncpy(error_return, dlerror(), 255);
		return NULL;
	}
#endif
	return fn;
}


void scc_close_library(extlib_t lib) {
	if (lib == NULL) return;
#ifdef _WIN32
	FreeLibrary(lib);
#else
	dlclose(lib);
#endif
}

