/**
 * SC Controller - fake gamepad driver
 *
 * Fake physical gamepad used for testing. Set SCC_FAKES=1 (or larger) to enable.
 */

#define LOG_TAG "fakedrv"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/input_device.h"
#include "scc/input_test.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include <stdlib.h>
#include <unistd.h>
#include "fake.h"


static FakeGamepad** pads = NULL;


void on_load(void* _d) {
	Daemon* d = (Daemon*)_d;
	const char* envvar = getenv("SCC_FAKES");
	int count = atoi(envvar);
	if (count > 0) {
		LOG("Creating %i fake controllers", count);
		pads = malloc(sizeof(FakeGamepad*) * count);
		ASSERT(pads);
		for (int i=0; i<count; i++) {
			FakeGamepad* pad = fakegamepad_new();
			ASSERT(pad);
			pads[i] = pad;
			d->controller_add(&pad->controller);
		}
	}
}

static void driver_list_devices(Driver* drv, Daemon* daemon, const controller_available_cb ca) {
	char* get_name(const InputDeviceData* idev) {
		return strbuilder_cpy("Fake (test) controller driver");
	}
	char* get_prop(const InputDeviceData* idev, const char* name) {
		if ((0 == strcmp(name, "vendor_id")) || (0 == strcmp(name, "product_id")))
			return strbuilder_cpy("fake");
		return NULL;
	}
	InputDeviceData idev = {
		.subsystem = 0,
		.path = "(fake)",
		.get_name = get_name,
		.get_prop = get_prop,
	};
	ca("fake", 9, &idev);
}


static InputTestMethods input_test = {
	.list_devices = driver_list_devices,
};

static Driver driver = {
	.unload = NULL,
	.start = NULL,
	.input_test = &input_test,
};

Driver* scc_driver_init(Daemon* d) {
	if (getenv("SCC_FAKES") == NULL) return NULL;
	d->schedule(1000, on_load, d);
	return &driver;
}

