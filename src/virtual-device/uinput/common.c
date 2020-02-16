/**
 * SC Controller - Uinput methods
 */
#define LOG_TAG "UInput"
#include "scc/utils/logging.h"
#include "scc/conversions.h"
#include "common.h"

#include <sys/stat.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

#define UINPUT_PATH "/dev/uinput"
#define NAME_SIZE (UINPUT_MAX_NAME_SIZE + 64)

static struct Internal dummy = { VTP_DUMMY };

/** Returns false on error */
VirtualDevice* setup_device(VirtualDeviceType type,
							struct uinput_user_dev uidev,
							struct axis* axes, size_t axis_count,
							uint16_t* keys, size_t key_count,
							uint16_t* rels, size_t rel_count) {
	struct Internal* vdev = malloc(sizeof(struct Internal));
	if (vdev == NULL) {
		LERROR("OOM while allocating uinput device");
		return NULL;
	}
	int fd = open(UINPUT_PATH, O_WRONLY | O_NONBLOCK);
	if (fd < 0) {
		LERROR("Failed to open '%s': %s", UINPUT_PATH, strerror(errno));
		free(vdev);
		return NULL;
	}
	
	snprintf((char*)vdev->name, NAME_SIZE, "<UInput 0x%02x: %s>", fd, uidev.name);
	
	#define IOCTLSETUP(ctl, value)											\
		if (ioctl(fd, ctl, value) < 0) {									\
			LERROR("" #ctl " " #value " failed: %s", strerror(errno));		\
			close(fd);														\
			free(vdev);														\
			return NULL;													\
		}
	
	if (key_count > 0) {
		IOCTLSETUP(UI_SET_EVBIT, EV_KEY);
		for (size_t i = 0; i<key_count; i++) {
			IOCTLSETUP(UI_SET_KEYBIT, keys[i]);
		}
	}
	
	if (axis_count > 0) {
		IOCTLSETUP(UI_SET_EVBIT, EV_ABS);
		for (size_t i = 0; i<axis_count; i++) {
			IOCTLSETUP(UI_SET_ABSBIT, axes[i].id);
			uidev.absmin[axes[i].id] = axes[i].min;
			uidev.absmax[axes[i].id] = axes[i].max;
			uidev.absfuzz[axes[i].id] = axes[i].fuzz;
			uidev.absflat[axes[i].id] = axes[i].flat;
		}
	}
	
	if (rel_count > 0) {
		IOCTLSETUP(UI_SET_EVBIT, EV_REL);
		for (size_t i = 0; i<rel_count; i++) {
			IOCTLSETUP(UI_SET_RELBIT, rels[i] - SCC_REL_OFFSET);
		}
	}
	
	if (type == VTP_KEYBOARD) {
		IOCTLSETUP(UI_SET_EVBIT, EV_MSC);
		IOCTLSETUP(UI_SET_MSCBIT, MSC_SCAN);
		IOCTLSETUP(UI_SET_EVBIT, EV_REP);
	}
	
	if (write(fd, &uidev, sizeof(uidev)) < 0) {
		LERROR("Failed setup uinput device");
		close(fd);
		free(vdev);
		return NULL;
	}
	
	IOCTLSETUP(UI_DEV_CREATE, 0);
	
	vdev->pressed = NULL;
	vdev->type = type;
	vdev->fd = fd;
	return (VirtualDevice*)vdev;
}

void scc_virtual_device_close(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY)
		// Dummy is singleton
		return;
	close(idev->fd);
	free(idev->pressed);
	free(idev);
}

VirtualDeviceType scc_virtual_device_get_type(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	return idev->type;
}

const char* scc_virtual_device_to_string(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY)
		return "<Dummy uinput device>";
	return idev->name;
}

void scc_virtual_device_flush(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY) return;
	if (idev->type == VTP_MOUSE) flush_mouse(idev);
	
	struct input_event ev;
	memset(&ev, 0, sizeof(ev));
	ev.type = EV_SYN;
	ev.code = SYN_REPORT;
	ev.value = 0;
	write(idev->fd, &ev, sizeof(ev));
}

void scc_virtual_device_set_x_display(void* dpy) {
	// Not needed by uinput
}

void scc_virtual_device_key_release(VirtualDevice* dev, Keycode key) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY) return;
	if (idev->type == VTP_KEYBOARD) {
		if ((scc_keycode_to_hw_scan(key) == 0) || !idev->pressed[key]) {
			// Invalid or not pressed key
			return;
		}
		keyboard_scan_event(idev, key);
		idev->pressed[key] = false;
	}
	struct input_event ev;
	memset(&ev, 0, sizeof(ev));
	ev.type = EV_KEY;
	ev.code = key;
	ev.value = 0;
	write(idev->fd, &ev, sizeof(ev));
	scc_virtual_device_flush(dev);
}

void scc_virtual_device_key_press(VirtualDevice* dev, Keycode key) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY) return;
	if (idev->type == VTP_KEYBOARD) {
		if ((scc_keycode_to_hw_scan(key) == 0) || idev->pressed[key]) {
			// Invalid or already pressed key
			return;
		}
		keyboard_scan_event(idev, key);
		idev->pressed[key] = true;
	}
	struct input_event ev;
	memset(&ev, 0, sizeof(ev));
	ev.type = EV_KEY;
	ev.code = key;
	ev.value = 1;
	write(idev->fd, &ev, sizeof(ev));
	scc_virtual_device_flush(dev);
}


VirtualDevice* scc_virtual_device_create(VirtualDeviceType type, VirtualDeviceSettings* settings) {
	switch (type) {
	case VTP_KEYBOARD:
		return setup_keyboard(settings);
	case VTP_GAMEPAD:
		return setup_gamepad(settings);
	case VTP_MOUSE:
		return setup_mouse(settings);
	case VTP_DUMMY:
		return (VirtualDevice*)&dummy;
	default:
		return NULL;
	}
}
