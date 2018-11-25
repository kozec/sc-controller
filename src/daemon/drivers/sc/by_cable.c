/**
 * Steam Controller Controller Steam Controller Driver
 *
 * Used to communicate with single Steam Controller
 * connected directly by USB cable.
 */
#define LOG_TAG "sc_by_cable"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include "sc.h"
#include <stddef.h>

#define VENDOR_ID			0x28de
#define PRODUCT_ID			0x1102
#define ENDPOINT			3
#define CONTROLIDX			2
#define CHUNK_LENGTH		64

static Driver driver = {
	.unload = NULL
};


void input_interrupt_cb(Daemon* d, USBDevHandle hndl, uint8_t endpoint, const uint8_t* data, void* userdata) {
	SCController* sc = (SCController*)userdata;
	if (data == NULL) {
		// Means controller disconnected (or failed in any other way)
		DEBUG("%s disconnected", sc->desc);
		// sc->daemon->usb_close(sc->usb_hndl);
		// TODO: Calling close at this point may hang. Closing should be
		//       scheduled for later time instead, ideally in sccd_usb_dev_close.
		sc->usb_hndl = NULL;
		// Releases all buttons, centers all sticks and sends fake input to mapper
		memset(&sc->input, 0, sizeof(ControllerInput));
		sc->mapper->input(sc->mapper, &sc->input);
		d->controller_remove(&sc->controller);
		return;
	}
	handle_input(sc, (SCInput*)data);
}


static void hotplug_cb(Daemon* daemon, const char* syspath, Subsystem sys, Vendor vendor, Product product) {
	USBDevHandle hndl = daemon->usb_open(syspath);
	SCController* sc = NULL;
	if (hndl == NULL) {
		LERROR("Failed to open '%s'", syspath);
		return;		// and nothing happens
	}
	if ((sc = create_usb_controller(daemon, hndl, SC_WIRED, CONTROLIDX)) == NULL) {
		LERROR("Failed to allocate memory");
		goto hotplug_cb_fail;
	}
	if (daemon->usb_claim_interfaces_by(hndl, 3, 0, 0) <= 0) {
		LERROR("Failed to claim interfaces");
		goto hotplug_cb_fail;
	}
	if (!read_serial(sc))
		goto hotplug_cb_failed_to_configure;
#ifdef _WIN32
	if (!clear_mappings(sc))
		// clear_mappings is needed on Windows, as kernel driver cannot be deatached there
		goto hotplug_cb_failed_to_configure;
#endif
	if (!configure(sc))
		goto hotplug_cb_failed_to_configure;
	if (!daemon->usb_interupt_read_loop(hndl, ENDPOINT, 64, &input_interrupt_cb, sc))
		goto hotplug_cb_failed_to_configure;
	DEBUG("New wired Steam Controller with serial %s connected", sc->serial);
	sc->state = SS_READY;
	if (!daemon->controller_add(&sc->controller)) {
		// This shouldn't happen unless memory is running out
		DEBUG("Failed to add controller to daemon");
		goto hotplug_cb_fail;
	}
	return;
hotplug_cb_failed_to_configure:
	LERROR("Failed to configure controlller");
hotplug_cb_fail:
	if (sc != NULL)
		free(sc);
	daemon->usb_close(hndl);
}

Driver* scc_driver_init(Daemon* daemon) {
	ASSERT(sizeof(TriggerValue) == 1);
	ASSERT(sizeof(AxisValue) == 2);
	ASSERT(sizeof(GyroValue) == 2);
	// ^^ If any of above assertions fails, input_interrupt_cb code has to be
	//    modified so it doesn't use memcpy calls, as those depends on those sizes
	
	if (!daemon->hotplug_cb_add(USB, VENDOR_ID, PRODUCT_ID, &hotplug_cb)) {
		LERROR("Failed to register hotplug callback");
		return NULL;
	}
	return &driver;
}
