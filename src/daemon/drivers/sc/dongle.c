/**
 * Steam Controller Controller Steam Controller Driver
 *
 * Communicates with Steam Controller, which can handle up to 4 controllers at once.
 */
#define LOG_TAG "sc_dongle"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/input_device.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include "sc.h"
#include <stddef.h>

#define VENDOR_ID			0x28de
#define PRODUCT_ID			0x1142
#define FIRST_ENDPOINT		2
#define CTRLS_PER_DONGLE	4
#define FIRST_CONTROLIDX	1
#define CHUNK_LENGTH		64

#ifndef __BSD__

typedef struct Dongle {
	InputDevice*			dev;
	struct SCController*	controllers[CTRLS_PER_DONGLE];
} Dongle;

typedef LIST_TYPE(Dongle) DonglesList;

static DonglesList dongles;

#endif

static Driver driver = {
	.unload = NULL
};

void input_interrupt_cb(Daemon* d, InputDevice* dev, uint8_t endpoint, const uint8_t* data, void* userdata) {
#ifndef __BSD__
	Dongle* dg = (Dongle*)userdata;
	if (data == NULL) {
		// Means dongle disconnected (or failed in any other way)
		DEBUG("Dongle disconnected");
		for (size_t j=0; j<CTRLS_PER_DONGLE; j++) {
			SCController* sc = dg->controllers[j];
			disconnected(sc);
			// TODO: Deallocate sc
		}
		
		list_remove(dongles, dg);
		// TODO: Deallocating this.
		// free(dg);
		return;
	}
	
	if (endpoint < FIRST_ENDPOINT) {
		LOG("Got data on ep %i!", endpoint);
		return;
	}
	if (endpoint > FIRST_ENDPOINT + CTRLS_PER_DONGLE)
		return;
	
	SCController* sc = dg->controllers[endpoint - FIRST_ENDPOINT];
#else
	SCController* sc = (SCController*)userdata;
	if (data == NULL) {
		// Controller disconnected (or failed in any other way)
		DEBUG("%s disconnected", sc->desc);
		sc->dev->close(sc->dev);
		disconnected(sc);
		// TODO: Deallocate sc
		return;
	}
#endif
	SCInput* i = (SCInput*)data;
	if (i->ptype == PT_HOTPLUG) {
		if (data[4] == 1) {
			// Controller disconnected
			sc->state = SS_NOT_CONFIGURED;
			d->controller_remove(&sc->controller);
			return;
		}
	}
	if (i->ptype != PT_INPUT)
		return;
	
	if (sc->state == SS_FAILED)
		return;		// failed in the past, ignore
	else if (sc->state == SS_NOT_CONFIGURED) {
		// Just connected / not configured
		if (!read_serial(sc)) {
			// Freshly connected controller, not yet able to communicate.
			// Just wait for next input_interrupt, it should be OK then
			sc->state = SS_NOT_CONFIGURED;
			return;
		}
		if (!clear_mappings(sc) || !configure(sc)) {
			sc->state = SS_FAILED;
			return;
		}
		sc->state = SS_READY;
		if (!d->controller_add(&sc->controller)) {
			// This shouldn't happen unless memory is running out
			DEBUG("Failed to add controller to daemon");
			sc->state = SS_FAILED;
			return;
		}
		return;
	}
	
	if (i->ptype == PT_INPUT)
		handle_input(sc, (SCInput*)data);
}

static void turnoff(Controller* c) {
	SCController* sc = container_of(c, SCController, controller);
	uint8_t data[64] = { PT_OFF, 0x04, 0x6f, 0x66, 0x66, 0x21 };
	if (sc->dev->hid_request(sc->dev, sc->idx, data, -64) == NULL)
		LERROR("Failed to turn off controller");
}

#ifndef __BSD__
////// Linux and Windows, there is dongle, controllers are connected to it

static void hotplug_cb(Daemon* daemon, const char* syspath, Subsystem sys, Vendor vendor, Product product, int idx) {
	InputDevice* dev = daemon->open_input_device(syspath);
	Dongle* dongle = NULL;
	if (dev == NULL) {
		LERROR("Failed to open '%s'", syspath);
		return;		// and nothing happens
	}
	if (dev->sys == USB) {
		if (dev->claim_interfaces_by(dev, 3, 0, 0) <= 0) {
			LERROR("Failed to claim interfaces");
			goto hotplug_cb_fail;
		}
	}
	
	if (!list_allocate(dongles, 1))
		goto hotplug_cb_oom;
	dongle = malloc(sizeof(Dongle));
	if (dongle == NULL)
		goto hotplug_cb_oom;
	for (size_t j=0; j<CTRLS_PER_DONGLE; j++)
		dongle->controllers[j] = NULL;
	for (size_t j=0; j<CTRLS_PER_DONGLE; j++) {
		dongle->controllers[j] = create_usb_controller(daemon, dev, SC_WIRELESS, FIRST_CONTROLIDX + j);
		if (dongle->controllers[j] == NULL)
			goto hotplug_cb_oom;
		dongle->controllers[j]->controller.turnoff = &turnoff;
		if (!dev->interupt_read_loop(dev, FIRST_ENDPOINT + j, 64, &input_interrupt_cb, dongle)) {
			LERROR("Failed to configure dongle");
			goto hotplug_cb_fail;
		}
	}
	
	list_add(dongles, dongle);
	return;
	
hotplug_cb_oom:
	LERROR("Failed to allocate memory");
	if (dongle != NULL) {
		for (size_t j=0; j<CTRLS_PER_DONGLE; j++)
			if (dongle->controllers[j] != NULL)
				dongle->controllers[j]->controller.deallocate(&dongle->controllers[j]->controller);
		free(dongle);
	}
hotplug_cb_fail:
	dev->close(dev);
}

#else
////// BSD - there is no dongle, each controller has its own /dev/uhidX node
////// that is created all the time and it is registered with daemon only
////// after 1st input is recieved

static void hotplug_cb(Daemon* daemon, const char* syspath, Subsystem sys, Vendor vendor, Product product) {
	InputDevice* dev = daemon->open_input_device(syspath);
	if (dev == NULL) {
		LERROR("Failed to open '%s'", syspath);
		return;		// and nothing happens
	}
	SCController* sc = create_usb_controller(daemon, dev, SC_WIRELESS, 0);
	if (sc == NULL) {
		LERROR("Failed to allocate memory");
		dev->close(dev);
		return;
	}
	
	sc->controller.turnoff = &turnoff;
	if (!dev->interupt_read_loop(dev, 0, 64, &input_interrupt_cb, sc)) {
		LERROR("Failed to configure dongle");
		dev->close(dev);
		free(sc);
		return;
	}
}

#endif


Driver* scc_driver_init(Daemon* daemon) {
	ASSERT(sizeof(TriggerValue) == 1);
	ASSERT(sizeof(AxisValue) == 2);
	ASSERT(sizeof(GyroValue) == 2);
	// ^^ If any of above assertions fails, input_interrupt_cb code has to be
	//    modified so it doesn't use memcpy calls, as those depends on those sizes
	
#ifndef __BSD__
	dongles = list_new(Dongle, 4);
	if (dongles == NULL) {
		LERROR("Out of memory");
		return NULL;
	}
#endif
	if (!daemon->hotplug_cb_add(USB, VENDOR_ID, PRODUCT_ID, 0, &hotplug_cb)) {
		LERROR("Failed to register hotplug callback");
		return NULL;
	}
	return &driver;
}
