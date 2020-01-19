/**
 * Generic SC-Controller driver - udev
 *
 * Implementation used to communicate with generic controllers on Linux
 */
#define LOG_TAG "udev_drv"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/intmap.h"
#include "scc/input_device.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include "scc/tools.h"
#include <libevdev/libevdev.h>
#include <unistd.h>
#include <fcntl.h>

#define MAX_DESC_LEN	32
#define MAX_ID_LEN		24


typedef struct EvdevController {
	Controller				controller;
	Mapper*					mapper;
	Daemon*					daemon;
	intmap_t				button_map;
	intmap_t				axis_map;
	ControllerInput			input;
	char					id[MAX_ID_LEN];
	char					desc[MAX_DESC_LEN];
	int						fd;
	struct libevdev*		dev;
} EvdevController;


static Driver driver = {
	.unload = NULL
};


static const char* evdev_get_id(Controller* c) {
	EvdevController* ev = container_of(c, EvdevController, controller);
	return ev->id;
}

static const char* evdev_get_type(Controller* c) {
	return "evdev";
}

static const char* evdev_get_description(Controller* c) {
	EvdevController* ev = container_of(c, EvdevController, controller);
	return ev->desc;
}

static void evdev_set_mapper(Controller* c, Mapper* mapper) {
	EvdevController* ev = container_of(c, EvdevController, controller);
	ev->mapper = mapper;
}

static void evdev_turnoff(Controller* c) {
}

static void evdev_dealloc(Controller* c) {
	EvdevController* ev = container_of(c, EvdevController, controller);
	if (ev->dev != NULL)
		libevdev_free(ev->dev);
	if (ev->button_map != NULL)
		intmap_free(ev->button_map);
	if (ev->axis_map != NULL)
		intmap_free(ev->axis_map);
	if (ev->fd >= 0)
		close(ev->fd);
	free(ev);
}

static bool evdev_load_mappings(EvdevController* ev) {
	ev->button_map = intmap_new();
	ev->axis_map = intmap_new();
	if ((ev->button_map == NULL) || (ev->axis_map == NULL))
		return false;
	
	intmap_put(ev->button_map, 304, (any_t)B_A);
	intmap_put(ev->button_map, 305, (any_t)B_B);
	intmap_put(ev->button_map, 307, (any_t)B_X);
	intmap_put(ev->button_map, 308, (any_t)B_Y);
	intmap_put(ev->button_map, 314, (any_t)B_BACK);
	intmap_put(ev->button_map, 315, (any_t)B_START);
	intmap_put(ev->button_map, 317, (any_t)B_STICKPRESS);
	intmap_put(ev->button_map, 318, (any_t)B_RPADPRESS);
	intmap_put(ev->button_map, 310, (any_t)B_LB);
	intmap_put(ev->button_map, 311, (any_t)B_RB);
	intmap_put(ev->button_map, 316, (any_t)B_C);
	
	return true;
}


static void on_data_ready(Daemon* d, int fd, void* userdata) {
	EvdevController* ev = (EvdevController*)userdata;
	struct input_event event;
	while (libevdev_next_event(ev->dev, LIBEVDEV_READ_FLAG_NORMAL, &event) == LIBEVDEV_READ_STATUS_SUCCESS) {
		bool call_mapper = false;
		if (event.type == EV_KEY) {
			intptr_t _b;
			if (intmap_get(ev->button_map, event.code, (any_t)&_b) == MAP_OK) {
				SCButton b = (SCButton)_b;
				if (event.value)
					ev->input.buttons |= b;
				else
					ev->input.buttons &= ~b;
				call_mapper = true;
			} else {
				LOG("Unknown code %i", event.code);
			}
		}
		if (call_mapper && (ev->mapper != NULL))
			ev->mapper->input(ev->mapper, &ev->input);
	}
}


static void hotplug_cb(Daemon* d, const InputDeviceData* idev) {
	int err;
	char* event_file = strbuilder_fmt("/dev/input%s", strrchr(idev->path, '/'));
	if (event_file == NULL) return;		// OOM
	
	EvdevController* ev = malloc(sizeof(EvdevController));
	if (ev == NULL) {
		free(event_file);
		return;
	}
	
	memset(ev, 0, sizeof(EvdevController));
	ev->fd = open(event_file, O_RDONLY|O_NONBLOCK);
	if ((err = libevdev_new_from_fd(ev->fd, &ev->dev)) < 0) {
		LERROR("Failed to open evdev device %s: %s", event_file, strerror(-err));
		evdev_dealloc(&ev->controller);
		free(event_file);
		return;
	}
	free(event_file);
	
	if (!evdev_load_mappings(ev)) {
		LERROR("Failed to load mappings");
		evdev_dealloc(&ev->controller);
		return;
	}
	
	if (!d->poller_cb_add(ev->fd, &on_data_ready, ev)) {
		LERROR("Failed to register with poller");
		evdev_dealloc(&ev->controller);
		return;
	}
	
	ev->controller.flags = CF_HAS_DPAD | CF_NO_GRIPS | CF_HAS_RSTICK | CF_SEPARATE_STICK;
	ev->controller.deallocate = &evdev_dealloc;
	ev->controller.get_id = &evdev_get_id;
	ev->controller.get_type = &evdev_get_type;
	ev->controller.get_description = &evdev_get_description;
	ev->controller.set_mapper = &evdev_set_mapper;
	ev->controller.turnoff = &evdev_turnoff;
	ev->controller.set_gyro_enabled = NULL;
	ev->controller.get_gyro_enabled = NULL;
	ev->controller.flush = NULL;
	ev->mapper = NULL;
	ev->daemon = d;
	snprintf(ev->id, MAX_ID_LEN, "evdev%i", 77);
	snprintf(ev->desc, MAX_DESC_LEN, "<EvDev at %p>", ev);
	
	if (!d->controller_add(&ev->controller)) {
		LERROR("Failed to add new controller");
		evdev_dealloc(&ev->controller);
	}
	
	libevdev_grab(ev->dev, LIBEVDEV_GRAB);
}


Driver* scc_driver_init(Daemon* daemon) {
	HotplugFilter filter_name = { .type=SCCD_HOTPLUG_FILTER_NAME, .name="Logitech Gamepad F310" };
	if (!daemon->hotplug_cb_add(EVDEV, &hotplug_cb, &filter_name, NULL)) {
		LERROR("Failed to register hotplug callback");
		return NULL;
	}
	return &driver;
}

