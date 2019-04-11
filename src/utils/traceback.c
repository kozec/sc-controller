#ifndef NO_TRACEBACKS
#define _GNU_SOURCE
#include "scc/utils/traceback.h"
#include <stdio.h>
#include <execinfo.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <link.h>

#define BUFSIZE 1024
#define RED		"\x1b[31m"
#define GRAY	"\x1b[90m"
#define BLUE	"\x1b[94m"
#define CYAN	"\x1b[96m"
#define RESET	"\x1b[0m"

static const char* argv0 = NULL;
static struct sigaction sa = {};
static char buffer[BUFSIZE];


static int phdr_callback(struct dl_phdr_info *info, size_t size, void *data) {
	ElfW(Addr)* base_address = (ElfW(Addr)*)data;
	*base_address = info->dlpi_addr;
	return 1;
}

static bool get_fn_line(void* addr, char** fnname, char** filename, char** details) {
	if (argv0 == NULL)
		return false;
	snprintf(buffer, BUFSIZE - 1, "addr2line %p -f -s -p -e %s", addr, argv0);
	FILE *fp;
	
	if ((fp = popen(buffer, "r")) == NULL)
		// Failed to start addr2line
		return false;
	
	if (fgets(buffer, BUFSIZE - 1, fp) == NULL)
		// Failed to read response
		goto get_fn_fail;
	
	size_t len = strnlen(buffer, BUFSIZE - 2);
	buffer[len - 1] = 0;	// Strips newline at the end (or just terminates string that was not read entirelly)
	
	if (buffer[0] == '?')
		// Special case, addr2line was not able to get anything
		goto get_fn_fail;
	
	char* at = strstr(buffer, " at ");
	if (at == NULL) goto get_fn_fail;
	*at = 0;
	
	*fnname = buffer;
	*filename = at + 4;
	*details = strchr(at + 1, '(');
	if (*details != NULL)
		*((*details) - 1) = 0;
	if (*filename[0] == '?')
		goto get_fn_fail;
	return pclose(fp) == 0;
get_fn_fail:
	pclose(fp);
	return false;
}


void traceback_print_header() {
	fprintf(stderr, "\nTraceback (most recent last):\n");
}

void traceback_print(int skip) {
	void *trace[16];
	int trace_size = 0;
	ElfW(Addr) base_address;
	
	dl_iterate_phdr(&phdr_callback, &base_address); 
	
	trace_size = backtrace(trace, 16);
	for (int i=trace_size - 1; i>=skip; i--) {
		void* addr = trace[i] - base_address;
		char* filename;
		char* details;
		char* fnname;
		if (get_fn_line(addr, &fnname, &filename, &details)) {
			// Yes, I _am_ parsing that string just so it can be reassembled
			// into same string but colored. I like colors.
			if (details == NULL)
				fprintf(stderr, "  " GRAY "[0x%.12" PRIXPTR "] " BLUE "%s" RESET " at %s\n", (uintptr_t)addr, fnname, filename);
			else
				fprintf(stderr, "  " GRAY "[0x%.12" PRIXPTR "] " BLUE "%s" RESET " at %s" GRAY " %s\n", (uintptr_t)addr, fnname, filename, details);
		} else {
			char** messages = backtrace_symbols(&trace[i], 1);
			char* filename = messages[0];
			while (strchr(filename, '/') != NULL)
				filename = strchr(filename, '/') + 1;
			char* details = strchr(filename, '[');
			*details = 0;
			fprintf(stderr, "  " GRAY "[0x%.12" PRIXPTR "] " CYAN "%s" GRAY "[%s" RESET "\n", (uintptr_t)addr, filename, details + 1);
			free(messages);
		}
	}
	fflush(stdout);
}

static bool SIGSEGV_caught = false;

static void signal_handler(int sig) {
	switch (sig) {
	case SIGSEGV:
		if (SIGSEGV_caught) {
			fprintf(stderr, "\n" RED "Caught SIGSEGV while handling SIGSEGV, well done you." RESET "\n");
			exit(1);
		}
		SIGSEGV_caught = true;
		fprintf(stderr, "\n" RED "Caught SIGSEGV, segmentation fault on:" RESET "\n");
		traceback_print(3);
		exit(1);
	case SIGABRT:
		fprintf(stderr, "\n" RED "Caught SIGABRT, aborting on:" RESET "\n");
		traceback_print(5);
		exit(1);
	case SIGUSR1:
		fprintf(stderr, "\n" RESET "Caught SIGUSR1, printing stack trace:" RESET "\n");
		traceback_print(2);
		fprintf(stderr, "(this is not an error)\n\n");
	}
}

void traceback_set_argv0(const char* executablename) {
	argv0 = executablename;
	char* argv0_copy = malloc(strlen(argv0) + 1);
	if (argv0_copy != NULL) {
		strcpy(argv0_copy, argv0);
		argv0 = argv0_copy;
	}
	sa.sa_handler = signal_handler;
	sa.sa_flags = SA_NODEFER;
	sigaction(SIGSEGV, &sa, NULL);
	sigaction(SIGABRT, &sa, NULL);
	sigaction(SIGUSR1, &sa, NULL);
}


#else // NO_TRACEBACKS


/** Dummy implementation used when disabled by -DNO_TRACEBACKS */

void traceback_set_argv0(const char* executablename) {}

void traceback_print_header() {}

void traceback_print(int skip) {}

#endif
