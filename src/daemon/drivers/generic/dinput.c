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
// #include <dinput.h>

// static LPVOID di;
static Driver driver = {
	.unload = NULL
};


static void hotplug_cb(Daemon* d, const InputDeviceData* idata) {
	LOG("> %s", idata->path);
}


Driver* scc_driver_init(Daemon* daemon) {
	LOG("dinput init");
	HotplugFilter filter_guid = {
		.type = SCCD_HOTPLUG_FILTER_GUID,
		.guid_string = "{6C7EB1D0-420A-11EA-8001-444553540000}"
	};
	if (!daemon->hotplug_cb_add(DINPUT, &hotplug_cb, &filter_guid, NULL)) {
		LERROR("Failed to register hotplug callback");
		return NULL;
	}
	LOG("hidapi ready");
	return &driver;
}

