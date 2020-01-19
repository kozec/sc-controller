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
#include "scc/utils/assert.h"
#include "scc/tools.h"
#include <dirent.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>

#ifdef _WIN32
#include <windows.h>
#include <shlobj.h>
#define SEP "\\"
#else
#include <spawn.h>
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
static char python_path[PATH_MAX] = {0};
static char profiles_path[PATH_MAX + 128] = {0};
static char default_profiles_path[PATH_MAX + 128] = {0};
static char menus_path[PATH_MAX + 128] = {0};
static char default_menus_path[PATH_MAX + 128] = {0};
static char menuicons_path[PATH_MAX + 128] = {0};
static char controller_icons_path[PATH_MAX + 128] = {0};
static char default_menuicons_path[PATH_MAX + 128] = {0};
static char default_button_images_path[PATH_MAX + 128] = {0};
static char default_controller_icons_path[PATH_MAX + 128] = {0};
static char pid_file_path[PATH_MAX] = {0};
static char drivers_path[PATH_MAX] = {0};

extern char** environ;

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

static bool dir_exists(const char* path) {
	DIR* dir = opendir(share_path);
	if (dir) {
		closedir(dir);
		return true;
	}
	return false;
}

const char* scc_get_share_path() {
	if (share_path[0] != 0)
		// Return cached value
		return share_path;
	
	const char* scc_shared = getenv("SCC_SHARED");
	if (scc_shared != NULL) {
		// Automatically adding '/share' to end just because it's more
		// comfortable to write SCC_SHARED=$(pwd)
		if (snprintf(share_path, PATH_MAX, "%s/share", scc_shared) >= PATH_MAX)
			FATAL("$SCC_SHARED doesn't fit PATH_MAX.");
		if (dir_exists(share_path))
			return share_path;
		snprintf(share_path, PATH_MAX, "%s", scc_shared);
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
		snprintf(test, PATH_MAX, "%s\\share\\default_menus", arg0);
		if (access(test, F_OK) == 0) {
			strncpy(share_path, arg0, PATH_MAX);
			strcat(share_path, "\\share");
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
		
		if (dir_exists(share_path))
			return share_path;
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

const char* scc_get_menuicons_path() {
	if (menuicons_path[0] != 0)
		// Return cached value
		return menuicons_path;
	
	sprintf(menuicons_path, "%s" SEP "menu-icons", scc_get_config_path());
	return menuicons_path;
}

const char* scc_get_default_menuicons_path() {
	if (default_menuicons_path[0] != 0)
		// Return cached value
		return default_menuicons_path;
	
	sprintf(default_menuicons_path, "%s" SEP "images" SEP "menu-icons", scc_get_share_path());
	return default_menuicons_path;
}

const char* scc_get_controller_icons_path() {
	if (controller_icons_path[0] != 0)
		// Return cached value
		return controller_icons_path;
	
	sprintf(controller_icons_path, "%s" SEP "controller-icons", scc_get_config_path());
	return controller_icons_path;
}

const char* scc_get_default_controller_icons_path() {
	if (default_controller_icons_path[0] != 0)
		// Return cached value
		return default_controller_icons_path;
	
	sprintf(default_controller_icons_path, "%s" SEP "images" SEP "controller-icons", scc_get_share_path());
	return default_controller_icons_path;
}

const char* scc_get_default_button_images_path() {
	if (default_button_images_path[0] != 0)
		// Return cached value
		return default_button_images_path;
	
	sprintf(default_button_images_path, "%s" SEP "images" SEP "button-images", scc_get_share_path());
	return default_button_images_path;
}

const char* scc_get_pid_file() {
	if (pid_file_path[0] != 0)
		// Return cached value
		return pid_file_path;
	
	sprintf(pid_file_path, "%s" SEP "daemon.pid", scc_get_config_path());
	return pid_file_path;
}

const char* scc_drivers_path() {
	if (drivers_path[0] != 0)
		// Return cached value
		return drivers_path;
	// TODO: This path should be somehow configurable or determined on runtime
#ifdef _WIN32
	snprintf(drivers_path, PATH_MAX, "%s\\..\\drivers", scc_get_share_path());
#else
	strncpy(drivers_path, "src/daemon/drivers", PATH_MAX);
#endif
	return drivers_path;
}


#ifdef _WIN32
static char exe_path[PATH_MAX] = {0};

const char* scc_get_exe_path() {
	if (exe_path[0] != 0)
		// Return cached value
		return exe_path;
	char path[PATH_MAX];
	snprintf(path, PATH_MAX, "%s\\..", scc_get_share_path());
	ASSERT(exe_path == scc_realpath(path, exe_path));
	return exe_path;
}
#endif

// TODO: This, but properly
char* scc_find_binary(const char* name) {
	const char* paths[] = {
#ifdef _WIN32
		scc_get_exe_path(),
#else
		"./",
		"./tools",
#endif
		"src/osd",
		"src/daemon",
	};
	
	StrBuilder* sb = strbuilder_new();
	if (sb == NULL) return NULL;
	for (size_t i=0; i<sizeof(paths) / sizeof(char*); i++) {
		strbuilder_add(sb, paths[i]);
		strbuilder_add_path(sb, name);
#ifdef _WIN32
		strbuilder_add(sb, ".exe");
		if (!strbuilder_failed(sb))
			if (access(strbuilder_get_value(sb), F_OK) == 0)
				return strbuilder_consume(sb);
#else
		if (!strbuilder_failed(sb))
			if (access(strbuilder_get_value(sb), X_OK) == 0)
				return strbuilder_consume(sb);
#endif
		
		strbuilder_clear(sb);
	}
	
	strbuilder_free(sb);
	return NULL;
}

intptr_t scc_spawn(char* const* argv, uint32_t options) {
	ASSERT(options == 0);
#ifdef _WIN32
	const char* arg0 = argv[0];
	// So, yeah, Windows is just fucked. Arguments with spaces needs quotes,
	// arguments with quotes needs escaping.
	// https://github.com/kozec/sc-controller/issues/510
	// https://docs.microsoft.com/en-us/cpp/c-runtime-library/spawn-wspawn-functions?view=vs-2019
	StrBuilder* wargv = strbuilder_new();
	if (wargv != NULL) {
		int i = 1;
		for (const char* arg = argv[i]; arg != NULL; arg = argv[++i]) {
			if (i > 1)
				strbuilder_add(wargv, " ");
			if (strchr(arg, ' ') != NULL) {
				strbuilder_add(wargv, "\"");
				strbuilder_add_escaped(wargv, arg, "\"", '\\');
				strbuilder_add(wargv, "\"");
			} else {
				strbuilder_add_escaped(wargv, arg, "\"", '\\');
			}
		}
	}
	if ((wargv == NULL) || strbuilder_failed(wargv)) {
		strbuilder_free(wargv);
		LERROR("Failed to execute %s: Out of memory", argv[0]);
		return -1;
	}
	const char* new_argv[] = { arg0, strbuilder_get_value(wargv), NULL };
	intptr_t pid = _spawnv(_P_NOWAIT, arg0, new_argv);
	strbuilder_free(wargv);
	if (pid == 0) {
		LERROR("Failed to execute %s: %i", argv[0], GetLastError());
		return -1;
	}
	return pid;
#else
	pid_t pid;
	int err = posix_spawn(&pid, argv[0], NULL, NULL, argv, environ);
	if (err < 0) {
		LERROR("Fork failed: %s", strerror(err));
		return -1;
	}
	return pid;
#endif
}

#ifdef _WIN32
static inline size_t _slashes(char* path, char from, char to) {
	size_t count = 0;
	while (*path != 0) {
		if (*path == from) {
			*path = to;
			count++;
		}
		path ++;
	}
	return count;
}

size_t scc_path_fix_slashes(char* path) {
	return _slashes(path, '\\', '/');
}

size_t scc_path_break_slashes(char* path) {
	return _slashes(path, '/', '\\');
}
#endif

char* scc_path_strip_extension(const char* path) {
	char* dot = strrchr(path, '.');
	if (dot == NULL)
		return strbuilder_cpy(path);
	
	StrBuilder* b = strbuilder_new();
	if (b == NULL) return NULL;
	if (!strbuilder_add(b, path)) {
		strbuilder_free(b);
		return NULL;
	}
	strbuilder_rtrim(b, (path + strlen(path)) - dot);
	return strbuilder_consume(b);
}

char* scc_find_icon(const char* name, bool prefer_colored, bool* has_colors, const char** paths, const char** extensions) {
	static const char* default_extensions[] = { "png", "svg", NULL };
	static const char* default_paths[] = { NULL, NULL, NULL };
	char* rv = NULL;
	char* gray_filename = NULL;
	char* colr_filename = NULL;
	char* gray = NULL;
	char* colr = NULL;
	if (default_paths[0] == NULL) {
		default_paths[0] = scc_get_default_menuicons_path();
		default_paths[1] = scc_get_menuicons_path();
	}
	
	if (name == NULL) return NULL;
	if ((strlen(name) > 3) && (0 == strcmp(name + strlen(name) - 3, ".bw"))) {
		// TODO: Tests for this
		char* no_suffix = strbuilder_cpy(name);
		if (no_suffix == NULL)
			goto scc_find_icon_oom;
		*(no_suffix + strlen(no_suffix) - 3) = 0;
		char* rv = scc_find_icon(name, prefer_colored, has_colors, paths, extensions);
		free(no_suffix);
		return rv;
	}
	
	if (paths == NULL) paths = default_paths;
	if (extensions == NULL) extensions = default_extensions;
	
	while (*extensions != NULL) {
		const char* extension = *extensions;
		gray_filename = strbuilder_fmt("%s.bw.%s", name, extension);
		colr_filename = strbuilder_fmt("%s.%s", name, extension);
		if ((gray_filename == NULL) || (colr_filename == NULL))
			goto scc_find_icon_oom;
		gray = NULL;
		colr = NULL;
		const char** paths_ = paths;
		while (*paths_ != NULL) {
			// Check grayscale
			if (gray == NULL) {
				char* path = strbuilder_fmt("%s" SEP "%s", *paths_, gray_filename);
				if (path == NULL) {
					free(path);
					goto scc_find_icon_oom;
				}
				if (access(path, F_OK) == 0) {
					if (!prefer_colored) {
						if (has_colors != NULL) *has_colors = false;
						rv = path;
						goto scc_find_icon_cleanup;
					} else {
						gray = path;
					}
				} else {
					free(path);
				}
			}
			if (colr == NULL) {
				char* path = strbuilder_fmt("%s" SEP "%s", *paths_, colr_filename);
				if (path == NULL) {
					free(path);
					goto scc_find_icon_oom;
				}
				if (access(path, F_OK) == 0) {
					if (prefer_colored) {
						if (has_colors != NULL) *has_colors = true;
						rv = path;
						goto scc_find_icon_cleanup;
					} else {
						colr = path;
					}
				} else {
					free(path);
				}
			}
			paths_ ++;
		}
		if (colr != NULL) {
			if (has_colors != NULL) *has_colors = true;
			rv = colr;
			goto scc_find_icon_cleanup;
		} else if (gray != NULL) {
			if (has_colors != NULL) *has_colors = false;
			rv = gray;
			goto scc_find_icon_cleanup;
		}
		extensions ++;
	}
	rv = NULL;
	goto scc_find_icon_cleanup;
	
scc_find_icon_oom:
	LERROR("scc_find_icon: out of memory");
	rv = NULL;
scc_find_icon_cleanup:
	if (gray != rv) free(gray);
	if (colr != rv) free(colr);
	free(gray_filename);
	free(colr_filename);
	return rv;
}

char* scc_find_button_image(SCButton button, bool prefer_colored, bool* has_colors) {
	static const char* paths[] = { NULL, NULL };
	static const char* extensions[] = { "svg", NULL };
	const char* bstr = scc_button_to_string(button);
	if (bstr == NULL) return NULL;
	
	if (paths[0] == NULL)
		paths[0] = scc_get_default_button_images_path();
	
	return scc_find_icon(bstr, prefer_colored, has_colors, paths, extensions);
}

char* scc_realpath(char* path, char* resolved_path) {
	if (resolved_path == NULL) {
		resolved_path = malloc(PATH_MAX);
		if (resolved_path == NULL)
			return NULL;
	}
#ifdef _WIN32
	DWORD r = GetFullPathName(path, PATH_MAX, resolved_path, NULL);
	if ((r > PATH_MAX) || (r == 0)) return NULL;
	return resolved_path;
#else
	return realpath(path, resolved_path);
#endif
}

const char* scc_get_python_src_path() {
	if (python_path[0] != 0)
		// Return cached value
		return python_path;
	char path[PATH_MAX];
#ifdef _WIN32
	snprintf(path, PATH_MAX, "%s\\..\\python", scc_get_share_path());
#else
	snprintf(path, PATH_MAX, "%s/../python/scc", scc_get_share_path());
	if (access(path, F_OK) != -1) {
		snprintf(path, PATH_MAX, "%s/../python", scc_get_share_path());
	} else {
		snprintf(path, PATH_MAX, "/usr/lib/python2.7/site-packages");
	}
#endif
	ASSERT(python_path == scc_realpath(path, python_path));
	return python_path;
}

const char* scc_get_daemon_socket() {
	if (socket_path[0] != 0)
		// Return cached value
		return socket_path;
	// scc_get_config_path ensures that value returned by it fits PATH_MAX, so this cannot fail
	snprintf(socket_path, PATH_MAX + 128, "%s" SEP "daemon.socket", scc_get_config_path());
	return socket_path;
}

