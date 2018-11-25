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


/** Tests retrieving values using default s */
void test_defaults(CuTest* tc) {
	const char* filename = strbuilder_fmt("/tmp/test_config_%i.json", getpid());
	int f = open(filename, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	write(f, "{}", 2);
	close(f);
	
	f = open(filename, O_RDONLY);
	unlink(filename);
	assert(tc, f >= 0);
	
	char error[256];
	Config* c = config_load_from(f, error, sizeof(error));
	if (c == NULL) fprintf(stderr, "Error: %s\n", error);
	assert(tc, c != NULL);
	close(f);
	
	assert(tc, strcmp(config_get(c, "gui/news/last_version"), "0.3.12") == 0);
	assert(tc, config_get_int(c, "recent_max") == 10);
	assert(tc, config_get_double(c, "windows_opacity") == 0.95);
	RC_REL(c);
}


/** Tests retrieving values from config s */
void test_values(CuTest* tc) {
	const char* filename = strbuilder_fmt("/tmp/test_config_%i.json", getpid());
	int f = open(filename, O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
	write(f, "{ \"recent_max\": 8, \"windows_opacity\": 1.3, \"gui\":"
	 		 "{ \"news\": { \"last_version\": \"v0.5\" }} }", 88);
	close(f);
	
	f = open(filename, O_RDONLY);
	unlink(filename);
	assert(tc, f >= 0);
	
	char error[256];
	Config* c = config_load_from(f, error, sizeof(error));
	if (c == NULL) fprintf(stderr, "Error: %s\n", error);
	assert(tc, c != NULL);
	close(f);
	
	assert(tc, strcmp(config_get(c, "gui/news/last_version"), "v0.5") == 0);
	assert(tc, config_get_int(c, "recent_max") == 8);
	assert(tc, config_get_double(c, "windows_opacity") == 1.3);
	RC_REL(c);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	// DEFAULT_SUITE_ADD(test_defaults);
	DEFAULT_SUITE_ADD(test_values);
	
	return CuSuiteRunDefault();
}
