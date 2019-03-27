/**
 * SC Controller - fake gamepad driver
 *
 * Fake physical gamepad used for testing. Set SCC_FAKES=1 (or larger) to enable.
 */

#define LOG_TAG "fakedrv"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/assert.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include <stdlib.h>
#include <unistd.h>
#include "fake.h"


static Driver driver = {
	.unload = NULL
};


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


Driver* scc_driver_init(Daemon* d) {
	if (getenv("SCC_FAKES") == NULL) return NULL;
	d->schedule(1000, on_load, d);
	return &driver;
}

