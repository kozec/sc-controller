// Note: These tests should be tested separatelly on Linux and on Windows
#include "CuTest.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/traceback.h"
#include "scc/utils/rc.h"
#include "scc/config.h"
#include <sys/stat.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <fcntl.h>

#ifdef _WIN32
#include <windows.h>
#define TEST_CFG_PATH "Software\\SCController-test-%i"
#define config_load_from config_load_from_key
#define unlink(x)
#else
#define TEST_CFG_PATH "/tmp/test_config_%i.json"
#define TEST_CFG_DEV_PATH "/tmp/test_config_%i"
#endif


/** Tests retrieving values using default s */
void test_defaults(CuTest* tc) {
	char error[1024];
	const char* filename = strbuilder_fmt(TEST_CFG_PATH, getpid());
#ifndef _WIN32
	int f = open(filename, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	write(f, "{}", 2);
	close(f);
#else
	HKEY hkcu;
	HKEY subkey;
	REGSAM sam = KEY_READ;
	assert(tc, ERROR_SUCCESS == RegOpenCurrentUser(KEY_READ, &hkcu));
	assert(tc, ERROR_SUCCESS == RegCreateKeyExA(hkcu, filename, 0, NULL, 0, sam, NULL, &subkey, NULL));
	RegCloseKey(subkey);
#endif
	
	Config* c = config_load_from(filename, error);
	unlink(filename);
	if (c == NULL) fprintf(stderr, "Error: %s\n", error);
	assert(tc, c != NULL);
	
	assert(tc, strcmp(config_get(c, "gui/news/last_version"), "0.3.12") == 0);
	assert(tc, config_get_int(c, "recent_max") == 10);
	assert(tc, config_get_double(c, "windows_opacity") == 0.95);
	RC_REL(c);
	
#ifdef _WIN32
	RegDeleteKey(hkcu, filename);
	RegCloseKey(hkcu);
#endif
}


/** Tests retrieving values from config */
void test_values(CuTest* tc) {
	char error[1024];
	const char* filename = strbuilder_fmt(TEST_CFG_PATH, getpid());
#ifndef _WIN32
	int f = open(filename, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	write(f, "{ \"recent_max\": 8, \"windows_opacity\": 1.3, "
			 "\"autoswitch_osd\": true, \"gui\":{ \"news\": "
			 "{ \"last_version\": \"v0.5\" }} }", 112);
	close(f);
#else
	HKEY hkcu;
	HKEY subkey;
	REGSAM sam = KEY_READ;
	assert(tc, ERROR_SUCCESS == RegOpenCurrentUser(KEY_READ, &hkcu));
	assert(tc, ERROR_SUCCESS == RegCreateKeyExA(hkcu, filename, 0, NULL, 0, sam, NULL, &subkey, NULL));
	RegCloseKey(subkey);
	Config* c0 = config_load_from(filename, error);
	assert(tc, c0 != NULL);
	config_set(c0, "gui/news/last_version", "v0.5");
	config_set_int(c0, "recent_max", 8);
	config_set_int(c0, "autoswitch_osd", 1);
	config_set_double(c0, "windows_opacity", 1.3);
	assert(tc, config_save(c0));
	RC_REL(c0);
#endif
	
	Config* c = config_load_from(filename, error);
	unlink(filename);
	if (c == NULL) fprintf(stderr, "Error: %s\n", error);
	assert(tc, c != NULL);
	
	assert(tc, strcmp(config_get(c, "gui/news/last_version"), "v0.5") == 0);
	assert(tc, config_get_int(c, "recent_max") == 8);
	assert(tc, config_get_int(c, "autoswitch_osd"));
	assert(tc, config_get_double(c, "windows_opacity") == 1.3);
	RC_REL(c);
	
#ifdef _WIN32
	RegDeleteKey(hkcu, filename);
	RegCloseKey(hkcu);
#endif
}


/** Tests setting and retrieving values with no default */
void test_set(CuTest* tc) {
	char error[1024];
	const char* filename = strbuilder_fmt(TEST_CFG_PATH, getpid());
#ifndef _WIN32
	int f = open(filename, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	write(f, "{}", 2);
	close(f);
#else
	HKEY hkcu;
	HKEY subkey;
	REGSAM sam = KEY_READ;
	assert(tc, ERROR_SUCCESS == RegOpenCurrentUser(KEY_READ, &hkcu));
	assert(tc, ERROR_SUCCESS == RegCreateKeyExA(hkcu, filename, 0, NULL, 0, sam, NULL, &subkey, NULL));
	RegCloseKey(subkey);
#endif
	
	Config* c = config_load_from(filename, error);
	unlink(filename);
	if (c == NULL) fprintf(stderr, "Error: %s\n", error);
	assert(tc, c != NULL);
	
	assert(tc, !config_is_parent(c, "test"));
	
	assert(tc, config_set(c, "test/string", "hello_world") == 1);
	assert(tc, config_is_parent(c, "test"));
	assert(tc, config_set_int(c, "test/number", 42) == 1);
	assert(tc, config_set_int(c, "test/bool", true) == 1);
	assert(tc, config_set_double(c, "test/double", 13.3) == 1);
	
	assert(tc, strcmp(config_get(c, "test/string"), "hello_world") == 0);
	assert(tc, config_get_int(c, "test/number") == 42);
	assert(tc, config_get_int(c, "test/bool"));
	assert(tc, config_get_double(c, "test/double") == 13.3);
	RC_REL(c);
	
#ifdef _WIN32
	RegDeleteKey(hkcu, filename);
	RegCloseKey(hkcu);
#endif
}


/** Tests working with controller configs */
void test_controller_config(CuTest* tc) {
	const char* data[1024];
	char buffer[1024];
	char error[1024];
	// Prepare controller config
#ifndef _WIN32
	char* prefix = strbuilder_fmt(TEST_CFG_DEV_PATH, getpid());
	char* devpath = strbuilder_fmt(TEST_CFG_DEV_PATH "/devices/", getpid());
	char* filename = strbuilder_fmt(TEST_CFG_DEV_PATH "/devices/test.json", getpid());
	char* filename2 = strbuilder_fmt(TEST_CFG_DEV_PATH "/devices/test2.json", getpid());
	assert(tc, mkdir(prefix, 0700) == 0);
	assert(tc, mkdir(devpath, 0700) == 0);
	free(devpath);
	int f = open(filename, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	int f2 = open(filename2, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	free(filename2);
	char* json = strbuilder_cpy("{"
			"\"axes\": { \"1\": { \"axis\": \"stick_y\", \"deadzone\": 2000, \"max\": -32768, \"min\": 32767 } },"
			"\"buttons\": { \"305\": \"B\", \"307\": \"X\", \"308\": \"Y\" },"
			"\"dpads\": {},"
			"\"gui\": {"
			"	\"icon\": \"test-01\","
			"	\"buttons\": [\"A\",\"B\",\"X\",\"Y\",\"BACK\",\"C\",\"START\",\"LB\",\"RB\",\"LT\",\"RT\",\"LG\",\"RG\"]"
			"}"
	"}");
	write(f, json, strlen(json));
	write(f2, "{}", 2);
	close(f);
	close(f2);
	free(json);
	
	// Prepare (empty) SCC config
	filename2 = strbuilder_fmt(TEST_CFG_PATH, getpid());
	f = open(filename2, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	write(f, "{}", 2);
	close(f);
#else
	HKEY hkcu;
	char* prefix = strbuilder_fmt(TEST_CFG_PATH, getpid());
	assert(tc, ERROR_SUCCESS == RegOpenCurrentUser(KEY_READ, &hkcu));
	
	sprintf(buffer, TEST_CFG_PATH "\\devices\\test\\dpads", getpid());
	HKEY key = config_make_subkey(hkcu, buffer);
	RegCloseKey(key);
	
	sprintf(buffer, TEST_CFG_PATH "\\devices\\test2\\dpads", getpid());
	key = config_make_subkey(hkcu, buffer);
	RegCloseKey(key);
	
	sprintf(buffer, TEST_CFG_PATH "\\devices\\test\\axes\\1", getpid());
	key = config_make_subkey(hkcu, buffer);
	int64_t v;
	v = -32768;		assert(tc, ERROR_SUCCESS == RegSetKeyValueA(key, NULL, "min", REG_QWORD, &v, sizeof(int64_t)));
	v = 32768;		assert(tc, ERROR_SUCCESS == RegSetKeyValueA(key, NULL, "max", REG_QWORD, &v, sizeof(int64_t)));
	v = 2000;		assert(tc, ERROR_SUCCESS == RegSetKeyValueA(key, NULL, "deadzone", REG_QWORD, &v, sizeof(int64_t)));
					assert(tc, ERROR_SUCCESS == RegSetKeyValueA(key, NULL, "axis", REG_SZ, "stick_y", 8));
	RegCloseKey(key);
	
	sprintf(buffer, TEST_CFG_PATH "\\devices\\test\\buttons", getpid());
	key = config_make_subkey(hkcu, buffer);
	assert(tc, ERROR_SUCCESS == RegSetKeyValueA(key, NULL, "305", REG_SZ, "B", 2));
	assert(tc, ERROR_SUCCESS == RegSetKeyValueA(key, NULL, "307", REG_SZ, "X", 2));
	assert(tc, ERROR_SUCCESS == RegSetKeyValueA(key, NULL, "308", REG_SZ, "Y", 2));
	RegCloseKey(key);
	
	sprintf(buffer, TEST_CFG_PATH "\\devices\\test\\gui", getpid());
	key = config_make_subkey(hkcu, buffer);
	assert(tc, ERROR_SUCCESS == RegSetKeyValueA(key, NULL, "icon", REG_SZ, "test-01", 8));
	const char* buttons = "A\0B\0X\0Y\0BACK\0C\0START\0LB\0RB\0LT\0RT\0LG\0RG";
	assert(tc, ERROR_SUCCESS == RegSetKeyValueA(key, NULL, "buttons", REG_MULTI_SZ, buttons, 38));
	RegCloseKey(hkcu);
	RegCloseKey(key);
#endif
	
	// Open SCC config
#ifndef _WIN32
	Config* c = config_load_from(filename2, error);
	unlink(filename2);
	free(filename2);
	
	if (c == NULL) fprintf(stderr, "Error: %s\n", error);
	assert(tc, c != NULL);
	assert(tc, config_set_prefix(c, prefix));
#else
	Config* c = config_load_from(prefix, error);
	assert(tc, c != NULL);
#endif
	free(prefix);
	
	// Check config_get_controllers returns expected values
	assert(tc, -2 == config_get_controllers(c, data, 1));	// array too small
	assert(tc, 2 == config_get_controllers(c, data, 2));
	assert(tc, (0 == strcmp("test", data[0]))
			|| (0 == strcmp("test2", data[0])));
	
	// Open controller config
	Config* ccfg = config_get_controller_config(c, "test", error);
	if (ccfg == NULL) fprintf(stderr, "Error: %s\n", error);
	assert(tc, ccfg != NULL);
	
	// Grab various kind of data to test it works
	assert(tc, CVT_OBJECT == config_get_type(ccfg, "gui"));
	assert(tc, config_is_parent(ccfg, "gui"));
	assert(tc, 0 == strcmp("test-01", config_get(ccfg, "gui/icon")));
	assert(tc, 0 == strcmp("stick_y", config_get(ccfg, "axes/1/axis")));
	assert(tc, 0 == strcmp("X", config_get(ccfg, "buttons/307")));
	
	assert(tc, -2 == config_get_strings(ccfg, "buttons", data, 2));			// array too small
	assert(tc, 3 == config_get_strings(ccfg, "buttons", data, 4));
	assert(tc, 0 == strcmp("305", data[0]));
	assert(tc, 0 == strcmp("307", data[1]));
	assert(tc, 0 == strcmp("308", data[2]));
	
	assert(tc, -2 == config_get_strings(ccfg, "gui/buttons", data, 5));		// array to small
	assert(tc, 13 == config_get_strings(ccfg, "gui/buttons", data, 14));
	assert(tc, 0 == strcmp("B", data[1]));
	assert(tc, 0 == strcmp("RG", data[12]));
	
	// Try changing some data and save controller config file
	config_set(ccfg, "gui/icon", "better-icon");
	assert(tc, 0 == strcmp("better-icon", config_get(ccfg, "gui/icon")));
	config_save(ccfg);
	
#ifndef _WIN32
	// Load config back and, since I'm not going to implement another JSON parser,
	// just check if string is there.
	f = open(filename, O_RDONLY);
	assert(tc, read(f, buffer, 1024) > 600);
	buffer[1023] = 0;
	close(f);
	assert(tc, NULL != strstr(buffer, "better-icon"));
	free(filename);
#else
	sprintf(buffer, TEST_CFG_PATH "\\devices\\test\\gui", getpid());
	assert(tc, ERROR_SUCCESS == RegOpenCurrentUser(KEY_READ, &hkcu));
	key = config_make_subkey(hkcu, buffer);
	DWORD size = 256;
	assert(tc, ERROR_SUCCESS == RegGetValueA(key, NULL, "icon", RRF_RT_REG_SZ, NULL, buffer, &size));
	assert(tc, 0 == strcmp("better-icon", buffer));
	RegCloseKey(key);
	
	// Cleanup
	sprintf(buffer, TEST_CFG_PATH, getpid());
	RegDeleteTree(HKEY_CURRENT_USER, buffer);
	RegCloseKey(hkcu);
	// TODO: Use HKEY_CURRENT_USER instead of hcku
#endif
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_defaults);
	DEFAULT_SUITE_ADD(test_values);
	DEFAULT_SUITE_ADD(test_set);
	DEFAULT_SUITE_ADD(test_controller_config);
	
	return CuSuiteRunDefault();
}

