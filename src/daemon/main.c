/**
 * SC Controller - Daemon - main.c
 *
 * Here is where everything starts and where everything ends.
 */
#define LOG_TAG "Daemon"
#include "scc/utils/logging.h"
#include "scc/utils/argparse.h"
#include "scc/utils/traceback.h"
#include "scc/utils/strbuilder.h"
#include "scc/tools.h"
#include "daemon.h"
#include <sys/stat.h>
#include <unistd.h>
#ifndef _WIN32
#include <sys/types.h>
#include <signal.h>
#else
#include "scc/client.h"
#endif
#include <errno.h>
#include <stdio.h>

static const char *const usage[] = {
	"scc-daemon [-h] [--alone] [--once] [profile_name] {start,stop,restart,debug}",
	NULL,
};

typedef enum {
	M_NOT_SET,
	M_RESTART,
	M_START,
	M_DEBUG,
	M_STOP,
} Mode;

static char* argv0;

#ifndef _WIN32

static size_t max_argv0_size = 0;


/// daemonize function is adapted from original python code, which was adapted
/// from 'Generic linux daemon base class' python library, which was, in turn,
/// adapted from http://www.jejik.com/files/examples/daemon3x.py
int sccd_daemonize() {
	// Fork #1
	pid_t pid = fork();
	if (pid == -1) {
		LERROR("fork failed: %s", strerror(errno));
		return 1;
	} else if (pid > 0) {
		// exit first parent
		exit(0);
	}
	// decouple from parent environment
	char* cwd = getcwd(NULL, 0);
	chdir("/");
	if (setsid() < 0) {
		LERROR("setsid failed: %s", strerror(errno));
		return 1;
	}
	umask(0);
	
	// Fork #2
	pid = fork();
	if (pid == -1) {
		LERROR("fork failed: %s", strerror(errno));
		return 1;
	} else if (pid > 0) {
		// exit 2nd parent
		exit(0);
	}
	
	/*
	// Close everything, reopen stdin, out and err
	for(int fd=sysconf(_SC_OPEN_MAX); fd>0; --fd) {
		fsync(fd);
		close(fd);
	}
	stdin = fopen("/dev/null", "r");
	stdout = fopen("/dev/null", "w+");
	stderr = fopen("/dev/null", "w+");
	*/
	
	if (cwd != NULL) {
		chdir(cwd);
		free(cwd);
	}
	return 0;
}
#endif


static int start_daemon() {
#ifndef _WIN32
	int err = sccd_daemonize();
	if (err != 0) return err;
	return sccd_start();
#else
	LOG("Spawning: %s debug", argv0);
	intptr_t pid = _spawnl(_P_NOWAIT, argv0, argv0, "debug", NULL);
	if (pid == 0) {
		LERROR("Failed to execute: %i", GetLastError());
		return 1;
	}
	return 0;
#endif
}

static int stop_daemon(bool once) {
#ifndef _WIN32
	char buffer[256];
	pid_t pid = -1;
	FILE* f = fopen(scc_get_pid_file(), "r");
	if (f == NULL) {
		LERROR("pidfile %s does not exist. Is daemon running?", scc_get_pid_file());
		return 1;
	}
	if (fread(buffer, 1, 255, f) > 1) {
		fclose(f);
		pid = atoi(buffer);
	}
	if (pid <= 1) {
		LERROR("Failed to read pid from pid file (%s)", scc_get_pid_file());
		return 1;
	}
	
	// Try stopping 1st and then killing daemon process
	if (kill(pid, SIGTERM) == 0) {
		if (!once) {
			DEBUG("Waiting for PID %i to terminate...", pid);
			for (int i=0; i<300; i++) {				// Waits max 3s
				if (kill(pid, 0) != 0) break;
				usleep(10 * 1000);
			}
			if (kill(pid, 0) != 0) {
				DEBUG("Done.");
			} else {
				DEBUG("PID %i not terminating, killing it now.", pid);
				kill(pid, SIGKILL);
			}
		}
	}
	
	return 0;
#else
	SCCClient* c = sccc_connect();
	if (c == NULL) {
		LERROR("Failed to connect to running scc-daemon. Is it running?");
		return 1;
	}
	char* r = sccc_get_response(c, sccc_request(c, "Exit."));
	int rv = 1;
	if ((r != NULL) && (0 == strcmp("OK.", r))) {
		// Done
		rv = 0;
	} else {
		LERROR("Request failed: %s", r);
	}
	
	free(r);
	RC_REL(c);
	return rv;
#endif
}

void sccd_set_proctitle(const char* procname) {
#ifndef _WIN32
	strncpy(argv0, procname, max_argv0_size);
	argv0[max_argv0_size] = 0;
#endif
}


int main(int argc, char** argv) {
	argv0 = argv[0];
	traceback_set_argv0(argv[0]);
#ifndef _WIN32
	for (int i=0; i<argc; i++)
		max_argv0_size += strlen(argv[i]) + 1;
#endif
	
	bool alone = false, once = false;
	Mode mode = M_NOT_SET;
	char* profile = NULL;
	struct argparse_option options[] = {
		OPT_HELP(),
		OPT_GROUP("Advanced options"),
		OPT_BOOLEAN(0, "alone", &alone,	"prevent scc-daemon from launching "
										"osd-daemon and autoswitch-daemon", NULL),
		OPT_BOOLEAN(0, "once", &once,	"use with 'stop' to send single SIGTERM "
										"without waiting for daemon to exit", NULL),
		OPT_END(),
	};
	struct argparse argparse;
	argparse_init(&argparse, options, usage, 0);
	argparse_describe(&argparse, "\nSC-Controller daemon.", NULL);
	argc = argparse_parse(&argparse, argc, (const char**)argv);
	if (argc < 0)
		return 1;

#ifdef _WIN32
	// Special case for Windows: running daemon with no arguments should be
	// same as running 'scc-daemon debug', so user can just double-click
	// scc-daemon.exe icon and get console window with working emulation.
	mode = M_DEBUG;
#endif

	for (int i=0; i<argc; i++) {
		if		(0 == strcmp("start",	argv[i])) mode = M_START;
		else if	(0 == strcmp("stop",	argv[i])) mode = M_STOP;
		else if	(0 == strcmp("restart",	argv[i])) mode = M_RESTART;
		else if	(0 == strcmp("debug",	argv[i])) mode = M_DEBUG;
		else if (profile == NULL) {
			// Any unrecognized argument is profile, only one is expected
			profile = strbuilder_cpy(argv[i]);
			char* extension = strstr(profile, ".sccprofile");
			if (extension != NULL) *extension = 0;
		} else {
			argparse_usage(&argparse);
			return 1;
		}
	}
	
	if (profile != NULL) sccd_set_default_profile(profile);
	if (argc > 0) argv[1] = NULL;
	
	switch (mode) {
	case M_START:
		return start_daemon();
	case M_STOP:
		return stop_daemon(once);
	case M_RESTART:
		stop_daemon(once);
		return start_daemon();
	case M_DEBUG:
		sccd_logger_init(true);
		return sccd_start();
	default:
		argparse_usage(&argparse);
		return 1;
	}
	
	free(profile);
	return 0;
}

