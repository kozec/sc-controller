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
#include "scc/input_test.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include "scc/config.h"
#include <linux/input-event-codes.h>
#include <libevdev/libevdev.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <zlib.h>

static controller_available_cb controller_available = NULL;
static controller_test_cb controller_test = NULL;

typedef struct EvdevController {
	Controller				controller;
	GenericController		gc;
	int						fd;
	struct libevdev*		dev;
} EvdevController;


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
		switch (event.type) {
		case EV_KEY:
			if (controller_test != NULL) {
				controller_test(&ev->controller, TME_BUTTON,
						event.code, event.value ? 1 : 0);
				break;
			}
			if (apply_button(d, &ev->gc, event.code, event.value))
				call_mapper = true;
			break;
		case EV_ABS:
			if (controller_test != NULL) {
				controller_test(&ev->controller, TME_AXIS, event.code, event.value);
				break;
			}
			if (apply_axis(&ev->gc, event.code, (double)event.value))
				call_mapper = true;
			break;
		}
		if (call_mapper && (ev->gc.mapper != NULL))
			ev->gc.mapper->input(ev->gc.mapper, &ev->gc.input);
	}
	
	// TODO: DPad
	// TODO: Allow to disable PADPRESS_EMULATION
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
	char* uniq = idev->get_prop(idev, "device/uniq");
	if ((uniq != NULL) && (strlen(uniq) >= 2)) {
		strbuilder_add(sb, "-");
		strbuilder_add(sb, uniq);
	} else {
		char* name = idev->get_prop(idev, "device/name");
		if (name != NULL) {
			strbuilder_add(sb, "-");
			strbuilder_add(sb, name);
			free(name);
		}
	}
	free(uniq);
	
	if (strbuilder_failed(sb)) {
		strbuilder_free(sb);
		return NULL;
	}
	return strbuilder_consume(sb);
}

static void open_device(Daemon* d, const InputDeviceData* idev, Config* ccfg, const char* ckey) {
	int err;
	char* event_file = strbuilder_fmt("/dev/input%s", strrchr(idev->path, '/'));
	if (event_file == NULL)
		return;		// OOM
	
	EvdevController* ev = malloc(sizeof(EvdevController));
	if (ev != NULL) memset(ev, 0, sizeof(EvdevController));
	if ((ev == NULL) || !gc_alloc(d, &ev->gc)) {
		// OOM
		free(event_file);
		free(ev);
		return;
	}
	
	snprintf(ev->gc.desc, MAX_DESC_LEN, "<EvDev %s>", ckey);
	ev->gc.desc[MAX_DESC_LEN - 1] = 0;
	if (ev->gc.desc[MAX_DESC_LEN - 2] != 0)
		ev->gc.desc[MAX_DESC_LEN - 2] = '>';
	
	if (!gc_load_mappings(&ev->gc, ccfg)) {
		evdev_dealloc(&ev->controller);
		return;
	}
	
	ev->fd = open(event_file, O_RDONLY|O_NONBLOCK);
	if ((err = libevdev_new_from_fd(ev->fd, &ev->dev)) < 0) {
		LERROR("Failed to open evdev device %s: %s", event_file, strerror(-err));
		evdev_dealloc(&ev->controller);
		free(event_file);
		return;
	}
	free(event_file);
	
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
		strbuilder_add(sb, uniq);
	}
	free(uniq);
	strbuilder_upper(sb);
	strbuilder_insert(sb, 0, "evdev-");
	if (strbuilder_failed(sb)) {
		evdev_dealloc(&ev->controller);
		return;
	}
	gc_make_id(strbuilder_get_value(sb), &ev->gc);
	
	if (!d->poller_cb_add(ev->fd, &on_data_ready, ev)) {
		LERROR("Failed to register with poller");
		evdev_dealloc(&ev->controller);
		return;
	}
	
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

static bool hotplug_cb(Daemon* d, const InputDeviceData* idev) {
	char error[1024];
	char* ckey = evdev_idev_to_config_key(idev);
	Config* cfg = config_load();
	if ((cfg == NULL) || (ckey == NULL)) {
		RC_REL(cfg);
		free(ckey);
		return false;
	}
	Config* ccfg = config_get_controller_config(cfg, ckey, error);
	RC_REL(cfg);
	if (ccfg == NULL) {
		if (strstr(error, "No such file") == NULL)
			WARN("%s: %s", ckey, error);
		free(ckey);
		return false;
	}
	
	open_device(d, idev, ccfg, ckey);
	RC_REL(ccfg);
	free(ckey);
	return true;
}

static inline int test_bit(const char* bitmask, int bit) {
    return bitmask[bit/8] & (1 << (bit % 8));
}

static int open_idev(const InputDeviceData* idev) {
	char dev_input_path[256];
	strcpy(dev_input_path, "/dev/input");
	strncat(dev_input_path, strrchr(idev->path, '/'), 230);
	return open(dev_input_path, O_RDONLY);
	
}

static bool list_devices_hotplug_cb(Daemon* d, const InputDeviceData* idev) {
	// Examine device capabilities and decides if it passes for gamepad.
	// Device is considered gamepad-like if has at least one button with
	// keycode in gamepad range and at least two axes.
	int probablity_of_gamepad = 0;
	char code_bits[KEY_MAX/8 + 1];
	int fd = open_idev(idev);
	
	// buttons
	memset(&code_bits, 0, sizeof(code_bits));
	ioctl(fd, EVIOCGBIT(EV_KEY, sizeof(code_bits)), code_bits);
	for (int ev_code=0; ev_code<KEY_MAX; ev_code++) {
		if (test_bit(code_bits, ev_code)) {
			if ((ev_code >= BTN_JOYSTICK) && (ev_code <= BTN_THUMBR)) {
				probablity_of_gamepad += 5;
				break;
			}
		}
	}
	// axes
	memset(&code_bits, 0, sizeof(code_bits));
	ioctl(fd, EVIOCGBIT(EV_ABS, sizeof(code_bits)), code_bits);
	for (int ev_code=0; ev_code<ABS_MAX; ev_code++) {
		if (test_bit(code_bits, ev_code)) {
			if (ev_code <= ABS_RZ)
				probablity_of_gamepad += 2;
		}
	}
	close(fd);
	
	controller_available("evdev", min(9, probablity_of_gamepad), idev);
	return true;
}

static void driver_list_devices(Driver* drv, Daemon* d,
										const controller_available_cb ca) {
	controller_available = ca;
	d->hotplug_cb_add(EVDEV, list_devices_hotplug_cb, NULL);
}

static void driver_get_device_capabilities(Driver* drv, Daemon* daemon,
									const InputDeviceData* idev,
									InputDeviceCapabilities* capabilities) {
	char code_bits[KEY_MAX/8 + 1];
	int fd = open_idev(idev);
	capabilities->button_count = 0;
	capabilities->axis_count = 0;
	if (fd < 0) {
		LERROR("get_device_capabilities: failed to open device");
		return;
	}
	
	// buttons
	memset(&code_bits, 0, sizeof(code_bits));
	ioctl(fd, EVIOCGBIT(EV_KEY, sizeof(code_bits)), code_bits);
	for (int ev_code=0; ev_code<KEY_MAX; ev_code++) {
		if (test_bit(code_bits, ev_code)) {
			if (capabilities->button_count >= capabilities->max_button_count)
				break;
			capabilities->buttons[capabilities->button_count++] = ev_code;
		}
	}
	// axes
	memset(&code_bits, 0, sizeof(code_bits));
	ioctl(fd, EVIOCGBIT(EV_ABS, sizeof(code_bits)), code_bits);
	for (int ev_code=0; ev_code<ABS_MAX; ev_code++) {
		if (test_bit(code_bits, ev_code)) {
			if (capabilities->axis_count >= capabilities->max_axis_count)
				break;
			capabilities->axes[capabilities->axis_count++] = ev_code;
		}
	}
}

static void driver_test_device(Driver* drv, Daemon* daemon,
			const InputDeviceData* idata,  const controller_test_cb test_cb) {
	controller_test = test_cb;
	open_device(daemon, idata, NULL, "test");
}

static bool driver_start(Driver* drv, Daemon* daemon) {
	// TODO: Don't register everything, list known devices and register handlers
	// TODO: only for those instead
	if (!daemon->hotplug_cb_add(EVDEV, hotplug_cb, NULL)) {
		LERROR("Failed to register hotplug callback");
		return false;
	}
	return true;
}

static Driver driver = {
	.unload = NULL,
	.start = driver_start,
	.input_test = &((InputTestMethods) {
		.list_devices = driver_list_devices,
		.test_device = driver_test_device,
		.get_device_capabilities = driver_get_device_capabilities,
	})
};

Driver* scc_driver_init(Daemon* daemon) {
	return &driver;
}

