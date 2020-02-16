/**
 * Generic SC-Controller driver - hidapi
 *
 * Implementation that uses hidapi on Windows
 */
#include "generic.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/input_device.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include <windows.h>
#include <winbase.h>
#include <dinput.h>

typedef struct EvdevController {
	Controller				controller;
	GenericController		gc;
	int						fd;
	struct libevdev*		dev;
} EvdevController;

static Driver driver = {
	.unload = NULL
};

static void input_interrupt_cb(Daemon* d, InputDevice* dev, uint8_t endpoint, const uint8_t* data, void* _c) {
	DIJOYSTATE2* state = (DIJOYSTATE2*)data;
	// LOG("%li %li", state->lX, state->lY);
}


static void hotplug_cb(Daemon* d, const InputDeviceData* idata) {
	InputDevice* dev = idata->open(idata);
	if (dev == NULL) {
		LERROR("Failed open '%s'", idata->path);
		return;
	}
	if (!dev->interupt_read_loop(dev, 0, sizeof(DIJOYSTATE2), input_interrupt_cb, dev)) {
		LERROR("Failed to configure controller");
		dev->close(dev);
		// free();
		return;
	}
	
}


Driver* scc_driver_init(Daemon* daemon) {
	HotplugFilter filter_guid = {
		.type = SCCD_HOTPLUG_FILTER_GUID,
		.guid_string = "{6C7EB1D0-420A-11EA-8001-444553540000}"
	};
	if (!daemon->hotplug_cb_add(DINPUT, &hotplug_cb, &filter_guid, NULL)) {
		LERROR("Failed to register hotplug callback");
		return NULL;
	}
	return &driver;
}

