/**
 * SC-Controller - tools
 *
 * Various stuff that I don't care to fit anywhere else.
 * This also includes path-related tools originally placed in paths.py module.
 */
#pragma once
#include "scc/controller.h"
#include <stdbool.h>
#ifdef _WIN32
	#include <windows.h>
	// Windows have MAX_PATH instead and that's 250. Like, characters. Really.
	// Luckily, NT can handle much more than that, so SCC uses redefined value
	#undef PATH_MAX
	#define PATH_MAX 4096
	typedef HMODULE extlib_t;
#elif __linux__
	#include <linux/limits.h>
	typedef void* extlib_t;
#else
	#include <sys/syslimits.h>
	typedef void* extlib_t;
#endif


/**
 * Returns configuration directory, that is ~/.config/scc under normal conditions.
 * Returned value is cached internally and should NOT be free'd by caller.
 */
const char* scc_get_config_path();

/**
 * Returns path to socket that can be used to control scc-daemon,
 * that usually is ~/.config/scc/daemon.socket
 * Returned value is cached internally and should NOT be free'd by caller.
 */
const char* scc_get_daemon_socket();

/**
 * Returns directory where shared files are kept.
 * Usually /usr/share/scc, cwd() or $SCC_SHARED if defined
 * Returned value is cached internally and should NOT be free'd by caller.
 */
const char* scc_get_share_path();

/**
 * Returns directory where profiles are stored.
 * ~/.config/scc/profiles under normal conditions.
 */
const char* scc_get_profiles_path();

/**
 * Returns directory where default profiles are stored.
 * Probably something like /usr/share/scc/default_profiles,
 * or $SCC_SHARED/default_profiles if program is being started from
 * script extracted from source tarball
 */
const char* scc_get_default_profiles_path();

/**
 * Returns directory where menus are stored.
 * ~/.config/scc/menus under normal conditions.
 */
const char* scc_get_menus_path();

/**
 * Returns directory where menu icons are stored.
 * ~/.config/scc/menu-icons under normal conditions.
 */
const char* scc_get_menuicons_path();

/**
 * Returns directory where default menu icons are stored.
 * Probably something like /usr/share/scc/images/menu-icons,
 * or $SCC_SHARED/images/menu-icons if program is being started from
 * script extracted from source tarball
 */
const char* scc_get_default_menuicons_path();

/**
 * Returns directory where controller icons are stored.
 * ~/.config/scc/controller-icons under normal conditions.
 *
 * This directory may not exist.
 */
const char* scc_get_controller_icons_path();

/**
 * Returns directory where controller icons are stored.
 * Probably something like /usr/share/scc/images/controller-icons,
 * or ./images/controller-icons if program is being started from
 * extracted source tarball.
 *
 * This directory should always exist.
 */
const char* scc_get_default_controller_icons_path();

/**
 * Returns directory where button images are stored, that is
 * /usr/share/scc/images/button-images or $SCC_SHARED/images/button-images
 * if program is being started from script extracted from source tarball.
 *
 * Note that there is no 'scc_get_button_images_path'.
 * Button images are not user-overridable (yet).
 */
const char* scc_get_default_button_images_path();

/**
 * Returns directory when python (gui) modules are stored.
 */
const char* scc_get_python_src_path();

/**
 * Returns directory where default menus are stored.
 * Probably something like /usr/share/scc/default_menus,
 * or $SCC_SHARED/default_menus if program is being started from
 * script extracted from source tarball
 */
const char* scc_get_default_menus_path();

/**
 * Returns directory where drivers are located.
 * Usually /usr/lib/scc/drivers or $SCC_SHARED/drivers
 * if program is being started from script extracted from source tarball
 */
const char* scc_drivers_path();


/**
 * Returns path to scc-daemon PID file.
 * Usually ~/.config/scc/daemon.pid
 */
const char* scc_get_pid_file();

/**
 * Returns filename for specified profile name.
 * This is done by searching for name + '.sccprofile' in ~/.config/scc/profiles
 * first and in /usr/share/scc/default_profiles if file is not found in first
 * location.
 *
 * Returns NULL if profile cannot be found (or on failed memory allocation)
 * Returned string has to be deallocated by caller.
 */
char* scc_find_profile(const char* name);

/**
 * Returns filename for specified menu.
 * This is done by searching for filename in ~/.config/scc/menus first
 * and in /usr/share/scc/default_menus if file is not found in first
 * location.
 *
 * Returns NULL if profile cannot be found (or on failed memory allocation)
 * Returned string has to be deallocated by caller.
 */
char* scc_find_menu(const char* name);

/**
 * Returns filename for specified icon name.
 * This is done by searching for <name>.png and <name>.bw.png, <name>.svg
 * and <name>.bw.svg in user and default menu-icons folders.
 *
 * If both colored and grayscale version is found, colored is returned, unless
 * prefer_colored is set to false.
 *
 * If has_colors is not set NULL, value it points to is set to true if colored
 * version of icon is found or to false if only grayscale icon is found. If no
 * icon is found at all, value is not changed.
 *
 * both 'paths' and 'extensions' has to be NULL-terminated. If set to NULL, defaults are used.
 * Returns NULL if icon cannot be found.
 * Returned value has to be freed by called.
 */
char* scc_find_icon(const char* name, bool prefer_colored, bool* has_colors, const char** paths, const char** extensions);

/**
 * Works as scc_find_icon, but searches for button image instead.
 * Button may have both color and black-n-white image, but it will always be svg.
 *
 * Returns NULL if image cannot be found.
 * Returned value has to be freed by called.
 */
char* scc_find_button_image(SCButton button, bool prefer_colored, bool* has_colors);

/**
 * Returns full path to script or binary.
 * With some exceptions, this is done by searching in paths as defined by PATH environment variable.
 *
 * Returns NULL if binary cannot be found (or on failed memory allocation)
 * Returned string has to be deallocated by caller.
 */
char* scc_find_binary(const char* name);

/**
 * For given value of PadStickTrigger enum (a.k.a What?), returns button
 * signalizing that corresponding pad / stick / trigger is pressed.
 *
 * Returns 0 when conversion is not possible;
 */
SCButton scc_what_to_pressed_button(PadStickTrigger what);

/**
 * For value of PadStickTrigger enum representing left, right or PS4 pad,
 * returns button used to signalize that corresponding pad is being touched.
 *
 * Returns 0 when conversion is not possible;
 */
SCButton scc_what_to_touch_button(PadStickTrigger what);

/**
 * Translates button name (expressed as upper-case string) to corresponding
 * value of SCButton enum.
 *
 * Returns 0 for unknown value.
 */
SCButton scc_string_to_button(const char* s);

/**
 * Translates pad, stick or trigger name (expressed as upper-case string)
 * to corresponding value of PadStickTrigger enum.
 *
 * Returns 0 for unknown value.
 */
PadStickTrigger scc_string_to_pst(const char* s);

/**
 * Returns string matching PadStickTrigger value or NULL if value is not recognized.
 * Returned string shall not be deallocated.
 */
const char* scc_what_to_string(PadStickTrigger what);

/**
 * Returns string matching SCButton value or NULL if value is not recognized.
 * Returned string shall not be deallocated.
 */
const char* scc_button_to_string(SCButton b);

#ifdef _WIN32
/**
 * Replaces backslashes with forward slashes in given string.
 * String is modified in-place.
 * Returns number of replacements made.
 */
size_t scc_path_fix_slashes(char* path);

/**
 * Works as scc_path_fix_slashes, but replaces forward slashes with backslashes.
 */
size_t scc_path_break_slashes(char* path);

/** Returns path to directory where sc-controller.exe is located */
const char* scc_get_exe_path();
#endif


/**
 * Works as realpath, which is not available in mingw32.
 * 'resolved_path' has to have place for at least PATH_MAX bytes.
 * If 'resolved_path' is NULL, new buffer is allocated.
 *
 * Returns 'resolved_path', new allocated buffer if 'resolved_path' is NULL.
 * Returns NULL in case of error or if memory cannot be allocated.
 */
char* scc_realpath(char* path, char* resolved_path);

/**
 * Simply strips part after last '.' (including '.')
 * Caller is responsible for deallocating returned string.
 *
 * Returns copy of string if there is no '.' in it.
 * Returns NULL if memory cannot be allocated.
 */
char* scc_path_strip_extension(const char* path);

/**
 * Spawns background process using posix_spawn or _spawnv.
 * argv has to be NULL-terminated and contain arg0.
 * 'options' is currenly unused and has to be set to 0.
 *
 * Returns PID of created process or negative number in case of failure.
 */
intptr_t scc_spawn(char* const* argv, uint32_t options);

typedef enum {
	SCLT_DRIVER				= 1,
	SCLT_GENERATOR			= 2,
	SCLT_OSD_MENU_PLUGIN	= 3,
} SCCLibraryType;

/**
 * Loads library with given name (no extension).
 * 'type' determines path from which library should be loaded, which is very platform-dependant.
 * 'prefix' is just appended in between path and filename and may be NULL.
 *
 * On failure, returns NULL and sets error message in error_return, if set.
 * If error_return is set, it has to have place for at least 256 characters.
 */
extlib_t scc_load_library(SCCLibraryType type, const char* prefix, const char* lib_name, char* error_return);

/**
 * Loads function from already open library.
 *
 * On failure, returns NULL and sets error message in error_return, if set.
 * If error_return is set, it has to have place for at least 256 characters.
 */
void* scc_load_function(extlib_t lib, const char* name, char* error_return);

/** Closes library opened with scc_load_library. If called with NULL, does nothing */
void scc_close_library(extlib_t lib);

