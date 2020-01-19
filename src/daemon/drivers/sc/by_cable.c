/**
 * Steam Controller Controller Steam Controller Driver
 *
 * Used to communicate with single Steam Controller
 * connected directly by USB cable.
 */
#define LOG_TAG "sc_by_cable"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/input_device.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include "scc/tools.h"
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


void input_interrupt_cb(Daemon* d, InputDevice* dev, uint8_t endpoint, const uint8_t* data, void* userdata) {
	SCController* sc = (SCController*)userdata;
	if (data == NULL) {
		// Means controller disconnected (or failed in any other way)
		DEBUG("%s disconnected", sc->desc);
		// USBHelper* usb = d->get_usb_helper();
		// usb->close(sc->usb_hndl);
		// TODO: Calling close at this point may hang. Closing should be
		//       scheduled for later time instead, ideally in sccd_usb_dev_close.
		disconnected(sc);
		// TODO: Deallocate sc
		return;
	}
	SCInput* i = (SCInput*)data;
	if (i->ptype == PT_INPUT)
		handle_input(sc, i);
}


static void hotplug_cb(Daemon* daemon, const InputDeviceData* idata) {
	SCController* sc = NULL;
	InputDevice* dev = idata->open(idata);
	if (dev == NULL) {
		LERROR("Failed to open '%s'", idata->path);
		return;		// and nothing happens
	}
	if ((sc = create_usb_controller(daemon, dev, SC_WIRED, CONTROLIDX)) == NULL) {
		LERROR("Failed to allocate memory");
		goto hotplug_cb_fail;
	}
	if (dev->sys == USB) {
		if (dev->claim_interfaces_by(dev, 3, 0, 0) <= 0) {
			LERROR("Failed to claim interfaces");
			goto hotplug_cb_fail;
		}
	}
	if (!read_serial(sc)) {
		LERROR("Failed to read serial number");
		goto hotplug_cb_failed_to_configure;
	}
	if (!clear_mappings(sc))
		// clear_mappings is needed on Windows, as kernel driver cannot be deatached there
		goto hotplug_cb_failed_to_configure;
	if (!configure(sc))
		goto hotplug_cb_failed_to_configure;
	if (!dev->interupt_read_loop(dev, ENDPOINT, 64, &input_interrupt_cb, sc))
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
	dev->close(dev);
}

Driver* scc_driver_init(Daemon* daemon) {
	ASSERT(sizeof(TriggerValue) == 1);
	ASSERT(sizeof(AxisValue) == 2);
	ASSERT(sizeof(GyroValue) == 2);
	// ^^ If any of above assertions fails, input_interrupt_cb code has to be
	//    modified so it doesn't use memcpy calls, as those depends on those sizes
	
	HotplugFilter filter_vendor  = { .type=SCCD_HOTPLUG_FILTER_VENDOR,  .vendor=VENDOR_ID };
	HotplugFilter filter_product = { .type=SCCD_HOTPLUG_FILTER_PRODUCT, .product=PRODUCT_ID };
#ifndef __BSD__
	Subsystem s = daemon->get_hidapi_enabled() ? HIDAPI : USB;
	#define FILTERS &filter_vendor, &filter_product
#else
	Subsystem s = UHID;
	HotplugFilter filter_idx = { .type=SCCD_HOTPLUG_FILTER_UHID_IDX, .idx=CONTROLIDX };
	#define FILTERS &filter_vendor, &filter_product, &filter_idx
#endif
	if (!daemon->hotplug_cb_add(s, &hotplug_cb, FILTERS, NULL)) {
		LERROR("Failed to register hotplug callback");
		return NULL;
	}
	return &driver;
}

