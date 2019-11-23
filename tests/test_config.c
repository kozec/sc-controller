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
#define unlink(x)
#else
#define TEST_CFG_PATH "/tmp/test_config_%i.json"
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
	RegDeleteKeyA(hkcu, filename);
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
	RegDeleteKeyA(hkcu, filename);
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
	
	assert(tc, config_set(c, "test/string", "hello_world") == 1);
	assert(tc, config_set_int(c, "test/number", 42) == 1);
	assert(tc, config_set_int(c, "test/bool", true) == 1);
	assert(tc, config_set_double(c, "test/double", 13.3) == 1);
	
	
	assert(tc, strcmp(config_get(c, "test/string"), "hello_world") == 0);
	assert(tc, config_get_int(c, "test/number") == 42);
	assert(tc, config_get_int(c, "test/bool"));
	assert(tc, config_get_double(c, "test/double") == 13.3);
	RC_REL(c);
	
#ifdef _WIN32
	RegDeleteKeyA(hkcu, filename);
	RegCloseKey(hkcu);
#endif
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_defaults);
	DEFAULT_SUITE_ADD(test_values);
	DEFAULT_SUITE_ADD(test_set);
	
	return CuSuiteRunDefault();
}

