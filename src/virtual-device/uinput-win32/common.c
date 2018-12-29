/**
 * SC Controller - Virtual devices on Windows
 *
 * This is common code used by everything else
 */
#define LOG_TAG "WIN32"
#include "scc/utils/logging.h"
#include "common.h"


static struct Internal dummy = { VTP_DUMMY };


void scc_virtual_device_close(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	switch (idev->type) {
	case VTP_DUMMY:
	default:
		return;
	}
}

VirtualDeviceType scc_virtual_device_get_type(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	return idev->type;
}

const char* scc_virtual_device_to_string(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY)
		return "<Dummy win32 virtual device>";
	return idev->name;
}

void scc_virtual_device_flush(VirtualDevice* dev) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY) return;
	if (idev->type == VTP_MOUSE) flush_mouse(idev);
}

void scc_virtual_device_set_x_display(void* dpy) {
	// Not used on Windows
}

void scc_virtual_device_key_release(VirtualDevice* dev, Keycode key) {
	struct Internal* idev = (struct Internal*)dev;
	switch (idev->type) {
	case VTP_DUMMY:
		return;
	case VTP_GAMEPAD:
		if (idev->is_ds4)
			return scc_virtual_ds4_set_button(idev, key, false);
		else
			return scc_virtual_xusb_set_button(idev, key, false);
	case VTP_KEYBOARD:
		return winapi_keyboard_button(idev, key, false);
	case VTP_MOUSE:
		return winapi_mouse_button(idev, key, false);
	}
}

void scc_virtual_device_key_press(VirtualDevice* dev, Keycode key) {
	struct Internal* idev = (struct Internal*)dev;
	switch (idev->type) {
	case VTP_DUMMY:
		return;
	case VTP_GAMEPAD:
		if (idev->is_ds4)
			return scc_virtual_ds4_set_button(idev, key, true);
		else
			return scc_virtual_xusb_set_button(idev, key, true);
	case VTP_KEYBOARD:
		return winapi_keyboard_button(idev, key, true);
	case VTP_MOUSE:
		return winapi_mouse_button(idev, key, true);
	}
}

VirtualDevice* scc_virtual_device_create(VirtualDeviceType type, VirtualDeviceSettings* settings) {
	switch (type) {
	case VTP_GAMEPAD:
		return setup_gamepad(settings);
	case VTP_KEYBOARD:
	case VTP_MOUSE:
		return setup_winapi_device(type, settings);
	case VTP_DUMMY:
		return (VirtualDevice*)&dummy;
	default:
		return NULL;
	}
}
