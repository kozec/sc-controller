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
#include "scc/config.h"
#include <libevdev/libevdev.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <zlib.h>


typedef struct EvdevController {
	Controller				controller;
	GenericController		gc;
	int						fd;
	struct libevdev*		dev;
} EvdevController;


static Driver driver = {
	.unload = NULL
};

static const char* evdev_get_type(Controller* c) {
	return "evdev";
}


static void evdev_dealloc(Controller* c) {
	EvdevController* ev = container_of(c, EvdevController, controller);
	gc_dealloc(&ev->gc);
	if (ev->dev != NULL)
		libevdev_free(ev->dev);
	if (ev->fd >= 0)
		close(ev->fd);
	free(ev);
}


static void on_data_ready(Daemon* d, int fd, void* _ev) {
	EvdevController* ev = (EvdevController*)_ev;
	struct input_event event;
	SCButton old_buttons = ev->gc.input.buttons;
	while (libevdev_next_event(ev->dev, LIBEVDEV_READ_FLAG_NORMAL, &event) == LIBEVDEV_READ_STATUS_SUCCESS) {
		bool call_mapper = false;
		any_t val;
		switch (event.type) {
		case EV_KEY:
			if (intmap_get(ev->gc.button_map, event.code, &val) == MAP_OK) {
				SCButton b = (SCButton)val;
				if (event.value)
					ev->gc.input.buttons |= b;
				else
					ev->gc.input.buttons &= ~b;
				call_mapper = true;
			} else {
				WARN("Unknown keycode %i", event.code);
			}
			break;
		case EV_ABS:
			if (intmap_get(ev->gc.axis_map, event.code, &val) == MAP_OK) {
				AxisData* a = (AxisData*)val;
				apply_axis(a, (double)event.value, &ev->gc.input);
				call_mapper = true;
			} else {
				WARN("Unknown axis %i", event.code);
			}
			break;
		}
		if (call_mapper && (ev->gc.mapper != NULL))
			ev->gc.mapper->input(ev->gc.mapper, &ev->gc.input);
	}
	
	if ((ev->gc.input.buttons & ~old_buttons & (B_LPADTOUCH | B_RPADTOUCH)) != 0) {
		if (ev->gc.padpressemu_task != 0)
			d->cancel(ev->gc.padpressemu_task);
		ev->gc.padpressemu_task = d->schedule(PADPRESS_EMULATION_TIMEOUT,
										&gc_cancel_padpress_emulation, &ev->gc);
	}
}


static inline char* evdev_idev_to_config_key(const InputDeviceData* idev) {
	StrBuilder* sb = strbuilder_new();
	if (sb == NULL) return NULL;
	strbuilder_add(sb, "evdev");
	char* name = idev->get_prop(idev, "device/name");
	if (name != NULL) {
		strbuilder_add(sb, "-");
		strbuilder_add(sb, name);
		free(name);
	}
	char* uniq = idev->get_prop(idev, "device/uniq");
	if ((uniq != NULL) && (strlen(uniq) >= 2)) {
		strbuilder_add(sb, "-");
		strbuilder_add(sb, uniq);
	}
	free(uniq);
	
	if (strbuilder_failed(sb)) {
		strbuilder_free(sb);
		return NULL;
	}
	return strbuilder_consume(sb);
}


static void hotplug_cb(Daemon* d, const InputDeviceData* idev) {
	char* ckey = evdev_idev_to_config_key(idev);
	Config* cfg = config_load();
	if ((cfg == NULL) || (ckey == NULL)) {
		RC_REL(cfg);
		free(ckey);
		return;
	}
	Config* ccfg = config_get_controller_config(cfg, ckey, NULL);
	RC_REL(cfg);
	if (ccfg == NULL) {
		free(ckey);
		return;
	}
	
	int err;
	char* event_file = strbuilder_fmt("/dev/input%s", strrchr(idev->path, '/'));
	if (event_file == NULL) return;		// OOM
	
	EvdevController* ev = malloc(sizeof(EvdevController));
	if (ev == NULL) {
		free(event_file);
		RC_REL(ccfg);
		free(ckey);
		return;
	}
	
	memset(ev, 0, sizeof(EvdevController));
	ev->fd = open(event_file, O_RDONLY|O_NONBLOCK);
	if ((err = libevdev_new_from_fd(ev->fd, &ev->dev)) < 0) {
		LERROR("Failed to open evdev device %s: %s", event_file, strerror(-err));
		evdev_dealloc(&ev->controller);
		free(event_file);
		RC_REL(ccfg);
		free(ckey);
		return;
	}
	free(event_file);
	
	if (!gc_alloc(d, &ev->gc)) {
		evdev_dealloc(&ev->controller);
		RC_REL(ccfg);
		free(ckey);
		return;
	}
	
	StrBuilder* sb = strbuilder_new();
	char* uniq = idev->get_prop(idev, "device/uniq");
	if ((uniq == NULL) || (strlen(uniq) < 2)) {
		char* name = idev->get_prop(idev, "device/name");
		uLong crc;
		if (name == NULL) {
			crc = 0x101A17E;
		} else {
			crc = crc32(0, (const Bytef*)name, strlen(name));
			free(name);
		}
		strbuilder_addf(sb, "%x", crc);
	} else {
		strbuilder_addf(sb, "ev%s", uniq);
	}
	free(uniq);
	strbuilder_upper(sb);
	strbuilder_insert(sb, 0, "ev");
	gc_make_id(strbuilder_get_value(sb), &ev->gc);
	
	LOG("GONNA LOAD MAPPINGS for %s", ev->gc.id);
	if (!gc_load_mappings(ckey, &ev->gc, ccfg)) {
		evdev_dealloc(&ev->controller);
		RC_REL(ccfg);
		free(ckey);
		return;
	}
	RC_REL(ccfg);
	free(ckey);
	
	if (!d->poller_cb_add(ev->fd, &on_data_ready, ev)) {
		LERROR("Failed to register with poller");
		evdev_dealloc(&ev->controller);
		return;
	}
	
	snprintf(ev->gc.desc, MAX_DESC_LEN, "<EvDev %s>", libevdev_get_name(ev->dev));
	ev->gc.desc[MAX_DESC_LEN - 1] = 0;
	if (ev->gc.desc[MAX_DESC_LEN - 2] != 0)
		ev->gc.desc[MAX_DESC_LEN - 2] = '>';
	
	ev->controller.flags = CF_HAS_DPAD | CF_NO_GRIPS | CF_HAS_RSTICK | CF_SEPARATE_STICK;
	ev->controller.deallocate = evdev_dealloc;
	ev->controller.get_id = gc_get_id;
	ev->controller.get_type = evdev_get_type;
	ev->controller.get_description = gc_get_description;
	ev->controller.set_mapper = gc_set_mapper;
	ev->controller.turnoff = gc_turnoff;
	ev->controller.set_gyro_enabled = NULL;
	ev->controller.get_gyro_enabled = NULL;
	ev->controller.flush = NULL;
	
	if (!d->controller_add(&ev->controller)) {
		LERROR("Failed to add new controller");
		evdev_dealloc(&ev->controller);
	}
	
	libevdev_grab(ev->dev, LIBEVDEV_GRAB);
}


Driver* scc_driver_init(Daemon* daemon) {
	if (!daemon->hotplug_cb_add(EVDEV, &hotplug_cb, NULL)) {
		LERROR("Failed to register hotplug callback");
		return NULL;
	}
	return &driver;
}

