/**
 * SC Controller - fake gamepad driver
 *
 * Fake physical gamepad used for testing. Set SCC_FAKES=1 (or larger) to enable.
 */
#define LOG_TAG "fakedrv"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/mapper.h"
#include <stdlib.h>
#include "fake.h"

static uint32_t next_id = 0;


static const char* fakegamepad_get_id(Controller* c) {
	FakeGamepad* pad = container_of(c, FakeGamepad, controller);
	return pad->id;
}

static const char* fakegamepad_get_type(Controller* c) {
	return "fake";
}

static const char* fakegamepad_get_description(Controller* c) {
	FakeGamepad* pad = container_of(c, FakeGamepad, controller);
	return pad->desc;
}

static void fakegamepad_set_mapper(Controller* c, Mapper* mapper) {
	FakeGamepad* pad = container_of(c, FakeGamepad, controller);
	pad->mapper = mapper;
}

static void fakegamepad_turnoff(Controller* c) {
	LOG("Turning off fake gamepad (not really)");
}

static void fakegamepad_dealloc(Controller* c) {
	FakeGamepad* pad = container_of(c, FakeGamepad, controller);
	free(pad);
}

FakeGamepad* fakegamepad_new(Daemon* daemon) {
	FakeGamepad* pad = malloc(sizeof(FakeGamepad));
	if (pad == NULL) return NULL;
	
	next_id ++;
	memset(pad, 0, sizeof(FakeGamepad));
	pad->controller.flags = CF_NO_FLAGS;
	pad->controller.deallocate = &fakegamepad_dealloc;
	pad->controller.get_id = &fakegamepad_get_id;
	pad->controller.get_type = &fakegamepad_get_type;
	pad->controller.get_description = &fakegamepad_get_description;
	pad->controller.set_mapper = &fakegamepad_set_mapper;
	pad->controller.turnoff = &fakegamepad_turnoff;
	pad->controller.set_gyro_enabled = NULL;
	pad->controller.get_gyro_enabled = NULL;
	
	snprintf(pad->id, MAX_ID_LEN, "fake%i", next_id);
	snprintf(pad->desc, MAX_DESC_LEN, "<FakeGamepad #%i>", next_id);
	return pad;
}

