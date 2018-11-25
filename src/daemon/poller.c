/**
 * SC-Controller - Daemon - Poller
 *
 * Basically just epoll wrapper with some automatic management added on top.
 * On Windows, uses select() from Winsock2 and so it works only with sockets.
 */

#define LOG_TAG "Poller"
#include "scc/utils/logging.h"
#include "daemon.h"
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
static Cbdata callbacks[FD_SETSIZE];
static int nfds = 0;

static void sccd_poller_mainloop(Daemon* d) {
	struct timeval timeout;
	fd_set cur_readset = readset;
#ifdef _WIN32
	// On Windows, sccd_scheduler_get_sleep_time is used by usb_helper,
	// so select should return ASAP
	timeout.tv_sec = 0;
	timeout.tv_usec = 0;
#else
	sccd_scheduler_get_sleep_time(&timeout);
#endif
	int count = select(nfds, &cur_readset, NULL, NULL, &timeout);
	if (count < 0) {
#ifdef _WIN32
		WARN("select failed: error %i", WSAGetLastError());
		Daemon* d = get_daemon();
		d->mainloop_cb_remove(&sccd_poller_mainloop);
#else
		WARN("select failed: %s", strerror(errno));
#endif
		return;
	}
	if (count == 0)
		return;
#ifdef _WIN32
	for (int j = 0; j<count; j++) {
		int i = cur_readset.fd_array[j];
#else
	for (int i = 0; (i<nfds) && (count>0); i++) {
		if (FD_ISSET(i, &cur_readset))
#endif
			if (callbacks[i].callback != NULL)
				callbacks[i].callback(d, i, callbacks[i].userdata);
	}
}

void sccd_poller_init() {
	Daemon* d = get_daemon();
	FD_ZERO(&readset);
	memset(callbacks, 0, sizeof(Cbdata) * FD_SETSIZE);
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
	if (fd > FD_SETSIZE) {
		LERROR("Cannot monitor fd #%i. This is seriously bad and means code has to be rewitten.", fd);
		return false;
	}
	callbacks[fd].callback = cb;
	callbacks[fd].userdata = userdata;
	FD_SET(fd, &readset);
	if (fd + 1 > nfds)
		nfds = fd + 1;
	return true;
}

void sccd_poller_remove(int fd) {
	callbacks[fd].callback = NULL;
	callbacks[fd].userdata = NULL;
	FD_CLR(fd, &readset);
}
