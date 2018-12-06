/**
 * SC-Controller - Paths
 *
 * Methods in this module are used to determine stuff like where user data is stored,
 * where scc-daemon can be executed from and similar.
 *
 * All this is needed since I want to have entire thing installable, runnable
 * from source tarball *and* debugable in working folder.
 *
 * All functions here are returning value that's cached when function is called
 * for 1st time and so returned string should NOT be free'd by caller.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/traceback.h"
#include "scc/tools.h"
#include <dirent.h>
#include <errno.h>

#ifdef _WIN32
	#include <windows.h>
	#include <shlobj.h>
	#define SEP "\\"
#else
	#include <pwd.h>
	#define SEP "/"
#endif
#include <sys/types.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

// I know that PATH_MAX is bad idea, but I'm kinda relying on nobody having 
// path to home directory over 1kB long...
static char config_path[PATH_MAX] = {0};
static char socket_path[PATH_MAX + 128] = {0};
static char share_path[PATH_MAX] = {0};
static char profiles_path[PATH_MAX + 128] = {0};
static char default_profiles_path[PATH_MAX + 128] = {0};
static char menus_path[PATH_MAX + 128] = {0};
static char default_menus_path[PATH_MAX + 128] = {0};

const char* scc_get_config_path() {
	if (config_path[0] != 0)
		// Return cached value
		return config_path;
	
#ifdef _WIN32
	SHGetFolderPathA(NULL, CSIDL_APPDATA|CSIDL_FLAG_CREATE, NULL, 0, config_path);
	ASSERT(strlen(config_path) < PATH_MAX - 6);
	strcat(config_path, "\\scc");
#else
	const char* xdg_config_home = getenv("XDG_CONFIG_HOME");
	if (xdg_config_home != NULL) {
		if (snprintf(config_path, PATH_MAX, "%s/scc", xdg_config_home) >= PATH_MAX) {
			LERROR("Your $XDG_CONFIG_HOME doesn't fit PATH_MAX. How's that even possible? Using /tmp instead.");
			LERROR("Everything is wrong and expect to lose data! Your $XDG_CONFIG_HOME is:");
			LERROR("%s", xdg_config_home);
			sprintf(config_path, "/tmp");
		}
		return config_path;
	}
	
	struct passwd* pw = getpwuid(getuid());
	if (snprintf(config_path, PATH_MAX, "%s/.config/scc", pw->pw_dir) >= PATH_MAX) {
		LERROR("Your $HOME doesn't fit PATH_MAX. How's that even possible? Using /tmp instead.");
		LERROR("Everything is wrong and expect to lose data! Your $HOME is:");
		LERROR("%s", pw->pw_dir);
		sprintf(config_path, "/tmp");
	}
#endif	
	return config_path;
}

const char* scc_get_share_path() {
	if (share_path[0] != 0)
		// Return cached value
		return share_path;
	
	const char* scc_shared = getenv("SCC_SHARED");
	if (scc_shared != NULL) {
		if (snprintf(share_path, PATH_MAX, "%s", scc_shared) >= PATH_MAX)
			FATAL("$SCC_SHARED doesn't fit PATH_MAX.");
		return share_path;
	}
	
#ifdef _WIN32
	// What this does is taking path to current executable and going
	// up one directory until directory with "default_menus" subdir is found.
	// That one is our "SHARE_PATH", place where default scc stuff is stored.
	char arg0[PATH_MAX];
	char test[PATH_MAX];
	GetModuleFileName(NULL, arg0, MAX_PATH);
	while (1) {
		snprintf(test, PATH_MAX, "%s\\default_menus", arg0);
		if (access(test, F_OK) != -1) {
			strncpy(share_path, arg0, PATH_MAX);
			return share_path;
		}
		char* slash = strrchr(arg0, '\\');
		if (slash == NULL) break;
		*slash = 0;
	}
	strncpy(share_path, "./", PATH_MAX);
#else
	const char* possibilities[] = {
		"/usr/local/share/scc",
		"/usr/share/scc",
		"~/.local/share/scc",
		NULL,
	};
	
	for (int i=0; possibilities[i] != NULL; i++) {
		if (possibilities[i][0] == '~') {
			// Begins with home directory
			const char* home = getenv("HOME");
			if (home == NULL)
				continue;
			snprintf(share_path, PATH_MAX, "%s%s", home, &possibilities[i][1]);
		} else {
			strncpy(share_path, possibilities[i], PATH_MAX);
		}
		
		DIR* dir = opendir(share_path);
		if (dir) {
			// exists
			closedir(dir);
			return share_path;
		}
		// Dir doesn't exists, try another
	}
	
	// No path found, assume default and hope for best
	strncpy(share_path, "/usr/share/scc", PATH_MAX);
#endif
	return share_path;
}

const char* scc_get_profiles_path() {
	if (profiles_path[0] != 0)
		// Return cached value
		return profiles_path;
	
	sprintf(profiles_path, "%s" SEP "profiles", scc_get_config_path());
	return profiles_path;
}

const char* scc_get_default_profiles_path() {
	if (default_profiles_path[0] != 0)
		// Return cached value
		return default_profiles_path;
	
	sprintf(default_profiles_path, "%s" SEP "default_profiles", scc_get_share_path());
	return default_profiles_path;
}

const char* scc_get_menus_path() {
	if (menus_path[0] != 0)
		// Return cached value
		return menus_path;
	
	sprintf(menus_path, "%s" SEP "menus", scc_get_config_path());
	return menus_path;
}

const char* scc_get_default_menus_path() {
	if (default_menus_path[0] != 0)
		// Return cached value
		return default_menus_path;
	
	sprintf(default_menus_path, "%s" SEP "default_menus", scc_get_share_path());
	return default_menus_path;
}


// TODO: This, but properly
char* scc_find_binary(const char* name) {
	const char* paths[] = {
#ifndef _WIN32
		"./",
		"./tools",
#else
		scc_get_share_path(),
		"./build-win32/src/osd",
#endif
		"./build/src/osd",
	};
	
	StrBuilder* sb = strbuilder_new();
	if (sb == NULL) return NULL;
	for (size_t i=0; i<sizeof(paths) / sizeof(char*); i++) {
		strbuilder_add(sb, paths[i]);
		strbuilder_add_path(sb, name);
#ifdef _WIN32
		strbuilder_add(sb, ".exe");
		if (!strbuilder_failed(sb))
			if (access(strbuilder_get_value(sb), F_OK) != -1)
				return strbuilder_consume(sb);
#else
		if (!strbuilder_failed(sb))
			if (access(strbuilder_get_value(sb), X_OK) != -1)
				return strbuilder_consume(sb);
#endif
		
		strbuilder_clear(sb);
	}
	
	LOG("F1");
	strbuilder_free(sb);
	LOG("F2");
	return NULL;
}


/*
def get_menuicons_path():
	"""
	Returns directory where menu icons are stored.
	~/.config/scc/menu-icons under normal conditions.
	"""
	return os.path.join(get_config_path(), "menu-icons")


def get_default_menuicons_path():
	"""
	Returns directory where default menu icons are stored.
	Probably something like /usr/share/scc/images/menu-icons,
	or $SCC_SHARED/images/menu-icons if program is being started from
	script extracted from source tarball
	"""
	return os.path.join(get_share_path(), "images/menu-icons")


def get_button_images_path():
	"""
	Returns directory where button images are stored.
	/usr/share/scc/images/button-images by default.
	"""
	return os.path.join(get_share_path(), "images/button-images")


def get_menus_path():
	"""
	Returns directory where profiles are stored.
	~/.config/scc/profiles under normal conditions.
	"""
	return os.path.join(get_config_path(), "menus")


def get_default_menus_path():
	"""
	Returns directory where default profiles are stored.
	Probably something like /usr/share/scc/default_profiles,
	or ./default_profiles if program is being started from
	extracted source tarball
	"""
	return os.path.join(get_share_path(), "default_menus")


def get_controller_icons_path():
	"""
	Returns directory where controller icons are stored.
	~/.config/scc/controller-icons under normal conditions.
	
	This directory may not exist.
	"""
	return os.path.join(get_config_path(), "controller-icons")


def get_default_controller_icons_path():
	"""
	Returns directory where controller icons are stored.
	Probably something like /usr/share/scc/images/controller-icons,
	or ./images/controller-icons if program is being started from
	extracted source tarball.
	
	This directory should always exist.
	"""
	return os.path.join(get_share_path(), "images", "controller-icons")


def get_share_path():
	"""
	Returns directory where shared files are kept.
	Usually "/usr/share/scc" or $SCC_SHARED if program is being started from
	script extracted from source tarball
	"""
	if "SCC_SHARED" in os.environ:
		return os.environ["SCC_SHARED"]
	paths = (
		"/usr/local/share/scc/",
		os.path.expanduser("~/.local/share/scc"),
		os.path.join(sys.prefix, "share/scc")
	)
	for path in paths:
		if os.path.exists(path):
			return path
	# No path found, assume default and hope for best
	return "/usr/share/scc"


def get_pid_file():
	"""
	Returns path to PID file.
	~/.config/scc/daemon.pid under normal conditions.
	"""
	return os.path.join(get_config_path(), "daemon.pid")

*/


const char* scc_get_daemon_socket() {
	if (socket_path[0] != 0)
		// Return cached value
		return socket_path;
	// scc_get_config_path ensures that value returned by it fits PATH_MAX, so this cannot fail
	snprintf(socket_path, PATH_MAX + 128, "%s" SEP "daemon.socket", scc_get_config_path());
	return socket_path;
}
