/**
 * SC Controller - Winapi backed mouse & keyboard
 */
#define LOG_TAG "UInput"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/conversions.h"
#include "common.h"
#include <winuser.h>
#include <math.h>

#define XSCALE 0.006
#define YSCALE 0.006
#define SCR_XSCALE 0.01
#define SCR_YSCALE 0.01


VirtualDevice* setup_winapi_device(VirtualDeviceType type, const VirtualDeviceSettings* settings) {
	struct Internal* vdev = malloc(sizeof(struct Internal));
	if (vdev == NULL) {
		LERROR("OOM while allocating virtual device");
		return NULL;
	}
	
	ASSERT((type == VTP_MOUSE) || (type == VTP_KEYBOARD));
	vdev->mx = vdev->my = vdev->sx = vdev->sy = 0;
	
	if (type == VTP_MOUSE)
		snprintf((char*)vdev->name, NAME_SIZE, "<Winapi mouse device 0x%p>", vdev);
	else
		snprintf((char*)vdev->name, NAME_SIZE, "<Winapi keyboard device 0x%p>", vdev);
	vdev->type = type;
	return (VirtualDevice*)vdev;
}


void scc_virtual_device_mouse_move(VirtualDevice* dev, double dx, double dy) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type != VTP_MOUSE) return;
	idev->mx += dx * XSCALE;
	idev->my += dy * YSCALE;
}

void scc_virtual_device_mouse_scroll(VirtualDevice* dev, double dx, double dy) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type != VTP_MOUSE) return;
	idev->sx += dx * SCR_XSCALE;
	idev->sy += dy * SCR_YSCALE;
}

void winapi_mouse_button(struct Internal* idev, Keycode key, bool pressed) {
	INPUT input;
	input.type = INPUT_MOUSE;
	input.mi.time = 0;
	input.mi.dx = input.mi.dy = input.mi.mouseData = 0;
	
	switch (key) {
	case BTN_LEFT:
		input.mi.dwFlags = pressed ? MOUSEEVENTF_LEFTDOWN : MOUSEEVENTF_LEFTUP;
		break;
	case BTN_RIGHT:
		input.mi.dwFlags = pressed ? MOUSEEVENTF_RIGHTDOWN : MOUSEEVENTF_RIGHTUP;
		break;
	case BTN_MIDDLE:
		input.mi.dwFlags = pressed ? MOUSEEVENTF_MIDDLEDOWN : MOUSEEVENTF_MIDDLEUP;
		break;
	case BTN_SIDE:
	case BTN_EXTRA:
		// Windows doesn't support these
		return;
	}
	SendInput(1, &input, sizeof(input));
}

void winapi_keyboard_button(struct Internal* idev, Keycode key, bool pressed) {
	INPUT input;
	if (scc_keycode_to_win32_scan(key) == 0) {
		// Invalid keycode
		return;
	}
	
	input.type = INPUT_KEYBOARD;
	input.ki.wVk = 0;
	input.ki.dwFlags = (pressed ? 0 : KEYEVENTF_KEYUP) | KEYEVENTF_SCANCODE;
	uint16_t scancode = scc_keycode_to_win32_scan(key);
	if (scancode & 0xE000) {
		input.ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;
		input.ki.wScan = scancode & 0x00FF;
	} else {
		input.ki.wScan = scancode;
	}
	
	UINT r = SendInput(1, &input, sizeof(input));
	if (r < 1)
		LERROR("SendInput failed: %i", GetLastError());
}

void flush_mouse(struct Internal* idev) {
	INPUT input;
	input.type = INPUT_MOUSE;
	input.mi.time = 0;
	
	if ((idev->mx > 1.0) || (idev->mx < -1.0) || (idev->my > 1.0) || (idev->my < -1.0)) {
		LONG dx = (LONG)idev->mx;
		LONG dy = (LONG)idev->my;
		idev->mx = fmod(idev->mx, 1.0);
		idev->my = fmod(idev->my, 1.0);
		
		input.mi.dx = dx;
		input.mi.dy = -dy;
		input.mi.mouseData = 0;
		input.mi.dwFlags = MOUSEEVENTF_MOVE;
		SendInput(1, &input, sizeof(input));
	}
	
	if ((idev->sx > 1.0) || (idev->sx < -1.0) || (idev->sy > 1.0) || (idev->sy < -1.0)) {
		int32_t dy = (int32_t)idev->sy;
		idev->sx = fmod(idev->sx, 1.0);
		idev->sy = fmod(idev->sy, 1.0);
		
		input.mi.dx = 0;
		input.mi.dy = 0;
		input.mi.mouseData = -dy;
		input.mi.dwFlags = MOUSEEVENTF_WHEEL;
		SendInput(1, &input, sizeof(input));
	}
}
