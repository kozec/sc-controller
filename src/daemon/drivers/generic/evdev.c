/**
 * Generic SC-Controller driver - evdev
 *
 * Implementation used to communicate with generic controllers on Linux
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
#include <libevdev/libevdev.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <zlib.h>

#define PADPRESS_EMULATION_TIMEOUT 2

typedef struct EvdevController {
	Controller				controller;
	Mapper*					mapper;
	Daemon*					daemon;
	intmap_t				button_map;
	intmap_t				axis_map;
	ControllerInput			input;
	char					id[MAX_ID_LEN];
	char					desc[MAX_DESC_LEN];
	TaskID					padpressemu_task;
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
	if (ev->axis_map != NULL) {
		axis_map_free(ev->axis_map);
	}
	if (ev->fd >= 0)
		close(ev->fd);
	free(ev);
}

static bool evdev_load_mappings(Daemon* d, EvdevController* ev) {
	StrBuilder* sb = strbuilder_new();
	ev->button_map = intmap_new();
	ev->axis_map = axis_map_new();
	aojls_ctx_t* ctx = NULL;
	if ((sb == NULL) || (ev->button_map == NULL) || (ev->axis_map == NULL))
		goto evdev_load_mappings_oom;
	
	const char* uniq = libevdev_get_uniq(ev->dev);
	if (uniq == NULL)
		uniq = libevdev_get_name(ev->dev);		// Not so unique :(
	strbuilder_add(sb, d->get_config_path());
	strbuilder_add_path(sb, "devices");
	strbuilder_add_path(sb, "evdev-");
	strbuilder_addf(sb, "%s.json", uniq);
	if (strbuilder_failed(sb))
		goto evdev_load_mappings_oom;
	int fd = open(strbuilder_get_value(sb), O_RDONLY);
	if (fd < 0) {
		strbuilder_free(sb);
		WARN("No mappings for '%s'", uniq);
		return false;
	}
	strbuilder_clear(sb);
	strbuilder_add_fd(sb, fd);
	close(fd);
	if (strbuilder_failed(sb))
		goto evdev_load_mappings_oom;
	
	aojls_deserialization_prefs prefs = { 0 };
	ctx = aojls_deserialize((char*)strbuilder_get_value(sb), strbuilder_len(sb), &prefs);
	if ((ctx == NULL) || (prefs.error != NULL)) {
		LERROR("Failed to decode mappings for '%s': %s", uniq, prefs.error);
		strbuilder_free(sb);
		json_free_context(ctx);
		return false;
	}
	
	json_object* root = json_as_object(json_context_get_result(ctx));
	json_object* buttons = json_object_get_object(root, "buttons");
	json_object* axes = json_object_get_object(root, "axes");
	
	if (!load_button_map(uniq, buttons, ev->button_map))
		goto evdev_load_mappings_oom;
	if (!load_axis_map(uniq, axes, ev->axis_map))
		goto evdev_load_mappings_oom;
	
	strbuilder_free(sb);
	json_free_context(ctx);
	return true;

evdev_load_mappings_oom:
	strbuilder_free(sb);
	json_free_context(ctx);
	LERROR("Out of memory");
	return false;
}

static void cancel_padpress_emulation(void* _ev) {
	EvdevController* ev = (EvdevController*)_ev;
	Daemon* d = ev->daemon;
	bool needs_reschedule = false;
	if ((ev->input.buttons & B_LPADTOUCH) != 0) {
		if ((ev->input.lpad_x == 0) && (ev->input.lpad_y == 0))
			ev->input.buttons &= ~(B_LPADPRESS | B_LPADTOUCH);
		else
			needs_reschedule = true;
	}
	if ((ev->input.buttons & B_RPADTOUCH) != 0) {
		if ((ev->input.rpad_x == 0) && (ev->input.rpad_y == 0))
			ev->input.buttons &= ~B_RPADTOUCH;
		else
			needs_reschedule = true;
	}
	if (needs_reschedule)
		ev->padpressemu_task = d->schedule(PADPRESS_EMULATION_TIMEOUT, cancel_padpress_emulation, ev);
	else
		ev->padpressemu_task = 0;
	
	if (ev->mapper != NULL)
		ev->mapper->input(ev->mapper, &ev->input);
}

static void on_data_ready(Daemon* d, int fd, void* _ev) {
	EvdevController* ev = (EvdevController*)_ev;
	struct input_event event;
	SCButton old_buttons = ev->input.buttons;
	while (libevdev_next_event(ev->dev, LIBEVDEV_READ_FLAG_NORMAL, &event) == LIBEVDEV_READ_STATUS_SUCCESS) {
		bool call_mapper = false;
		any_t val;
		switch (event.type) {
		case EV_KEY:
			if (intmap_get(ev->button_map, event.code, &val) == MAP_OK) {
				SCButton b = (SCButton)val;
				if (event.value)
					ev->input.buttons |= b;
				else
					ev->input.buttons &= ~b;
				call_mapper = true;
			} else {
				WARN("Unknown keycode %i", event.code);
			}
			break;
		case EV_ABS:
			if (intmap_get(ev->axis_map, event.code, &val) == MAP_OK) {
				AxisData* a = (AxisData*)val;
				apply_axis(a, (double)event.value, &ev->input);
				call_mapper = true;
			} else {
				WARN("Unknown axis %i", event.code);
			}
			break;
		}
		if (call_mapper && (ev->mapper != NULL))
			ev->mapper->input(ev->mapper, &ev->input);
	}
	
	if ((ev->input.buttons & ~old_buttons & (B_LPADTOUCH | B_RPADTOUCH)) != 0) {
		if (ev->padpressemu_task != 0)
			d->cancel(ev->padpressemu_task);
		ev->padpressemu_task = d->schedule(PADPRESS_EMULATION_TIMEOUT,
											&cancel_padpress_emulation, ev);
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
	
	if (!evdev_load_mappings(d, ev)) {
		evdev_dealloc(&ev->controller);
		return;
	}
	
	if (!d->poller_cb_add(ev->fd, &on_data_ready, ev)) {
		LERROR("Failed to register with poller");
		evdev_dealloc(&ev->controller);
		return;
	}
	
	StrBuilder* sb = strbuilder_new();
	const char* uniq = libevdev_get_uniq(ev->dev);
	if (uniq == NULL) {
		const char* name = libevdev_get_name(ev->dev);
		if (name == NULL) name = "(null)";
		uLong crc = crc32(0, (const Bytef*)name, strlen(name));
		strbuilder_addf(sb, "%x", crc);
	} else {
		strbuilder_addf(sb, "ev%s", uniq);
	}
	strbuilder_upper(sb);
	strbuilder_insert(sb, 0, "ev");
	int counter = 0;
	do {
		make_id(strbuilder_get_value(sb), ev->id, counter ++);
	} while (d->get_controller_by_id(ev->id) != NULL);
	
	snprintf(ev->desc, MAX_DESC_LEN, "<EvDev %s>", libevdev_get_name(ev->dev));
	ev->desc[MAX_DESC_LEN - 1] = 0;
	if (ev->desc[MAX_DESC_LEN - 2] != 0)
		ev->desc[MAX_DESC_LEN - 2] = '>';
	
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

