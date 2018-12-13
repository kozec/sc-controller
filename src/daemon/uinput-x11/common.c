/**
 * SC Controller - fake uinput implementation used on systems with no uinput but with X11
 */
#define LOG_TAG "UInput"
#include "scc/utils/logging.h"
#include "scc/driver.h"
#include "common.h"

#include <sys/stat.h>
#include <stdlib.h>
#include <unistd.h>

static int have_xtest = -1;			// 1 - yes, 0 - no, -1 - no idea
static struct Internal dummy = { VTP_DUMMY };

Daemon* get_daemon();

void scc_virtual_device_close(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY)
		// Dummy is singleton
		return;
	free(idev);
}

VirtualDeviceType scc_virtual_device_get_type(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	return idev->type;
}

const char* scc_virtual_device_to_string(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY)
		return "<Dummy device>";
	return idev->name;
}

void scc_virtual_device_flush(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY) return;
	if (idev->type == VTP_MOUSE) flush_mouse(idev);
}

void scc_virtual_device_key_release(VirtualDevice* dev, Keycode key) {
	struct Internal* idev = (struct Internal*)dev;
	switch (idev->type) {
	case VTP_KEYBOARD:
		if ((key >= keyboard_x11_keycode_count) || (keyboard_x11_keycodes[key] == 0))
			return;			// Invalid keycode
		XTestFakeKeyEvent(idev->dpy, keyboard_x11_keycodes[key], false, CurrentTime);
		XFlush(idev->dpy);
		return;
	case VTP_MOUSE:
		switch (key) {
		case BTN_LEFT:
			XTestFakeButtonEvent(idev->dpy, 1, false, CurrentTime);
			break;
		case BTN_MIDDLE:
			XTestFakeButtonEvent(idev->dpy, 2, false, CurrentTime);
			break;
		case BTN_RIGHT:
			XTestFakeButtonEvent(idev->dpy, 3, false, CurrentTime);
			break;
		case BTN_SIDE:
			XTestFakeButtonEvent(idev->dpy, 6, false, CurrentTime);
			break;
		case BTN_EXTRA:
			XTestFakeButtonEvent(idev->dpy, 7, false, CurrentTime);
			break;
		default:
			return;
		}
		XFlush(idev->dpy);
		return;
	case VTP_GAMEPAD:
	case VTP_DUMMY:
		return;
	}
}

void scc_virtual_device_key_press(VirtualDevice* dev, Keycode key) {
	struct Internal* idev = (struct Internal*)dev;
	switch (idev->type) {
	case VTP_KEYBOARD:
		if ((key >= keyboard_x11_keycode_count) || (keyboard_x11_keycodes[key] == 0))
			return;			// Invalid keycode
		XTestFakeKeyEvent(idev->dpy, keyboard_x11_keycodes[key], true, CurrentTime);
		XFlush(idev->dpy);
		return;
	case VTP_MOUSE:
		switch (key) {
		case BTN_LEFT:
			XTestFakeButtonEvent(idev->dpy, 1, true, CurrentTime);
			break;
		case BTN_MIDDLE:
			XTestFakeButtonEvent(idev->dpy, 2, true, CurrentTime);
			break;
		case BTN_RIGHT:
			XTestFakeButtonEvent(idev->dpy, 3, true, CurrentTime);
			break;
		case BTN_SIDE:
			XTestFakeButtonEvent(idev->dpy, 6, true, CurrentTime);
			break;
		case BTN_EXTRA:
			XTestFakeButtonEvent(idev->dpy, 7, true, CurrentTime);
			break;
		default:
			return;
		}
		XFlush(idev->dpy);
		return;
	case VTP_GAMEPAD:
	case VTP_DUMMY:
		return;
	}
}

void scc_virtual_device_set_axis(VirtualDevice* dev, Axis a, AxisValue value) {
}



VirtualDevice* scc_virtual_device_create(VirtualDeviceType type, VirtualDeviceSettings* settings) {
	Daemon* d = get_daemon();
	Display* dpy = (Display*)d->get_x_display();
	
	if (have_xtest < 0) {
		if (dpy == NULL) {
			LERROR("Connection to XServer failed, mouse and keyboard emulation is not possible.");
			have_xtest = 0;
		} else {
			int event_base, error_base;
			int major_ver, minor_ver;
			if (!XTestQueryExtension(dpy, &event_base, &error_base, &major_ver, &minor_ver)) {
				LERROR("XTest extension not available, mouse and keyboard emulation is not possible.");
				have_xtest = 0;
			}
		}
	}
	
	if (have_xtest == 0)
		return NULL;
	
	switch (type) {
	case VTP_KEYBOARD:
		return setup_keyboard(dpy, settings);
	case VTP_MOUSE:
		return setup_mouse(dpy, settings);
	case VTP_DUMMY:
		return (VirtualDevice*)&dummy;
	case VTP_GAMEPAD:
	default:
		return NULL;
	}
}
