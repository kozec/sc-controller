/**
 * Steam Controller Controller Steam Controller Driver
 *
 * Implementation over HidAPI, preffered on Windows
 */
#define LOG_TAG "sc_by_cable"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include "sc.h"
#include <hidapi/hidapi.h>
#include <stddef.h>

#define VENDOR_ID			0x28de
#define PRODUCT_ID			0x1102
#define ENDPOINT			3
#define CONTROLIDX			2
#define CHUNK_LENGTH		64


static void hotplug_cb(Daemon* daemon, const char* syspath, Subsystem sys, Vendor vendor, Product product) {
	// TODO: This is actually completly wrong, as it opens not device that was
	// connected, but device matching expected vendor and product id. That will,
	// often, be just connected device, unless someone connects multiple
	// wired controllers at once.
	
	// Open & allocated
	SCController* sc = NULL;
	hid_device* handle = NULL;
	// TODO: Change create_usb_controller so it doesn't take USB device handle
	if ((sc = create_usb_controller(daemon, NULL, SC_WIRED, 0)) == NULL) {
		LERROR("Failed to allocate memory");
		goto hotplug_cb_fail;
	}
	if ((handle = hid_open(VENDOR_ID, PRODUCT_ID, NULL)) == NULL) {
		LERROR("Failed to open '%s'", syspath);
		goto hotplug_cb_fail;
		return;
	}
	sc->handle = handle;
	
	// Read serial number
	wchar_t wstr[255];
	if (hid_get_serial_number_string(handle, wstr, 255) != 0) {
		LERROR("Failed to retrieve serial number");
		goto hotplug_cb_fail;
	}
	wcstombs(sc->serial, wstr, MAX_SERIAL_LEN);
	LOG("SN: %s\n", sc->serial);
	return;

hotplug_cb_fail:
	if (sc != NULL)
		free(sc);
	if (handle != NULL)
		hid_close(handle);
}


static void unload(struct Driver* drv, struct Daemon* d) {
	hid_exit();
}

static bool driver_start(Driver* drv, Daemon* daemon) {
	if (!daemon->hotplug_cb_add(USB, VENDOR_ID, PRODUCT_ID, hotplug_cb)) {
		LERROR("Failed to register hotplug callback");
		return false;
	}
	returm true;
}


static Driver driver = {
	.unload = &unload
	.start = driver_start,
	.list_devices = NULL,
};

Driver* scc_driver_init(Daemon* daemon) {
	ASSERT(sizeof(TriggerValue) == 1);
	ASSERT(sizeof(AxisValue) == 2);
	ASSERT(sizeof(GyroValue) == 2);
	// ^^ If any of above assertions fails, input_interrupt_cb code has to be
	//    modified so it doesn't use memcpy calls, as those depends on those sizes
	
	if (hid_init() != 0) {
		LERROR("Failed to initialize hid_api");
		return NULL;
	}
	
	return &driver;
}

