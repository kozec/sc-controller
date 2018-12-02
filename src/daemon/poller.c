/**
 * SC-Controller - Daemon - Poller
 *
 * Basically just epoll wrapper with some automatic management added on top.
 * On Windows, uses select() from Winsock2 and so it works only with sockets.
 */

#define LOG_TAG "Poller"
#include "scc/utils/logging.h"
#include "daemon.h"
#include "scc/utils/intmap.h"
#include "scc/utils/assert.h"
#ifdef _WIN32
	#define FD_SETSIZE 512
	#include <winsock2.h>
	#include <windows.h>
	#include <iphlpapi.h>
#else
	#include <sys/select.h>
	#include <sys/time.h>
	#include <sys/types.h>
#endif
#include <errno.h>
#include <unistd.h>

// TODO: Use epoll_wait instead of select

typedef struct {
	sccd_poller_cb		callback;
	void*				userdata;
} Cbdata;

static fd_set readset;
static intmap_t callbacks;
static int nfds = 0;

static void sccd_poller_mainloop(Daemon* d) {
#ifndef _WIN32
	////// Unix //////
	Cbdata* cbd;
	struct timeval timeout;
	fd_set cur_readset = readset;
	sccd_scheduler_get_sleep_time(&timeout);
	int count = select(nfds, &cur_readset, NULL, NULL, &timeout);
	if (count < 0) {
		WARN("select failed: %s", strerror(errno));
		return;
	}
	if (count == 0)
		return;
	for (int i = 0; (i<nfds) && (count>0); i++) {
		if (FD_ISSET(i, &cur_readset))
			if (intmap_get(callbacks, i, (any_t*)&cbd) == MAP_OK)
				cbd->callback(d, i, cbd->userdata);
	}
	
#else
	////// Windows //////
	Cbdata* cbd;
	struct timeval timeout;
	fd_set cur_readset = readset;
	// On Windows, sccd_scheduler_get_sleep_time is used by usb_helper,
	// so select should return ASAP
	timeout.tv_sec = 0;
	timeout.tv_usec = 0;
	int count = select(nfds, &cur_readset, NULL, NULL, &timeout);
	if (count < 0) {
		WARN("select failed: error %i", WSAGetLastError());
		Daemon* d = get_daemon();
		d->mainloop_cb_remove(&sccd_poller_mainloop);
		return;
	}
	if (count == 0)
		return;
	for (int j = 0; j<count; j++) {
		int i = cur_readset.fd_array[j];
		if (intmap_get(callbacks, i, (any_t*)&cbd) == MAP_OK)
			cbd->callback(d, i, cbd->userdata);
	}
#endif
}


void sccd_poller_init() {
	Daemon* d = get_daemon();
	FD_ZERO(&readset);
	callbacks = intmap_new();
	ASSERT(callbacks != NULL);
	ASSERT(d->mainloop_cb_add(&sccd_poller_mainloop));
}

void sccd_poller_close() {
	// nothing
}

bool sccd_poller_add(int fd, sccd_poller_cb cb, void* userdata) {
#ifdef _WIN32
	if (readset.fd_count >= FD_SETSIZE) {
		LERROR("Too many sockets");
		return false;
	}
#endif
	Cbdata* cbd;
	if (intmap_get(callbacks, fd, (any_t*)&cbd) == MAP_OK) {
		WARN("Request was made to monitor same file descriptor twice. This is not supported");
		return false;
	}
	cbd = malloc(sizeof(Cbdata));
	if ((cbd == NULL) || (intmap_put(callbacks, fd, cbd) != MAP_OK))  {
		WARN("Cannot monitor fd #%i: Out of memory", fd);
		free(cbd);
		return false;
	}
	cbd->callback = cb;
	cbd->userdata = userdata;
	FD_SET(fd, &readset);
	if (fd + 1 > nfds)
		nfds = fd + 1;
	return true;
}

void sccd_poller_remove(int fd) {
	Cbdata* cbd;
	if (intmap_get(callbacks, fd, (any_t*)&cbd) != MAP_OK) {
		WARN("Request was made to stop monitoring file descriptor that is not monitored. This is weird.");
		return;
	}
	intmap_remove(callbacks, fd);
	FD_CLR(fd, &readset);
	free(cbd);
}
