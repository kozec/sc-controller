/**
 * SC-Controller - Userdata
 *
 * Methods for searching for stuff.
 */
#include "scc/utils/logging.h"
#include "scc/utils/traceback.h"
#include "scc/utils/strbuilder.h"
#include "scc/tools.h"
#include <dirent.h>
#include <unistd.h>
#include <errno.h>

static char* find_stuff(const char* paths[], size_t path_count, const char* name, const char* extension) {
	if (name == NULL) return NULL;
	StrBuilder* sb = strbuilder_new();
	if (sb == NULL) return NULL;
	for (size_t i=0; i<path_count; i++) {
		strbuilder_add(sb, paths[i]);
		strbuilder_add_path(sb, name);
		strbuilder_add(sb, extension);
		
		if (!strbuilder_failed(sb)) {
			if (access(strbuilder_get_value(sb), F_OK) != -1)
				return strbuilder_consume(sb);
		}
		
		strbuilder_clear(sb);
	}

	strbuilder_free(sb);
	return NULL;
}

char* scc_find_profile(const char* name) {
	const char* paths[] = {
		scc_get_profiles_path(),
		scc_get_default_profiles_path()
	};
	return find_stuff(paths, sizeof(paths) / sizeof(char*), name, ".sccprofile");
}

char* scc_find_menu(const char* name) {
	const char* paths[] = {
		scc_get_menus_path(),
		scc_get_default_menus_path()
	};
	return find_stuff(paths, sizeof(paths) / sizeof(char*), name, "");
}
