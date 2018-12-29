#define LOG_TAG "Daemon"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "daemon.h"

static void* x11display;
#ifndef NO_X11
#include "X11/Xlib.h"

void sccd_x11_init() {
	x11display = (void*)XOpenDisplay(NULL);
	if (x11display == NULL) {
		WARN("Failed to connect to XServer. Some functionality will be unavailable.");
#ifdef __BSD__
		WARN("Running on BSD. 'Some functionality' includes keyboard and mouse emulation.");
#endif
	} else {
		scc_virtual_device_set_x_display((void*)x11display);
		LOG("Connected to XServer %s", DisplayString(x11display));
	}
}

void sccd_x11_close() {
	if (x11display != NULL) {
		XCloseDisplay(x11display);
		x11display = NULL;
	}
}

#else

void sccd_x11_init() {
	x11display = NULL;
}

void sccd_x11_close() {
}

#endif

/**
 * Returns open connection to X11 display.
 * Returns NULL on Windows, Android, or on *nix if connection to display failed
 */
void* sccd_x11_get_display() {
	return x11display;
}
