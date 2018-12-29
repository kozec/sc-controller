/**
 * SC Controller - Virtual devices on Windows
 * Common definitions.
 */
#pragma once

#include "scc/virtual_device.h"

#include "windows.h"
#include "ViGEm/Client.h"

#define NAME_SIZE 256

struct Internal {
	VirtualDeviceType			type;
	const char					name[NAME_SIZE];
	union {
		struct {
			bool				is_ds4;
			PVIGEM_TARGET		target;
			AxisValue			dpad_x;
			AxisValue			dpad_y;
			union {
				DS4_REPORT		ds4_report;
				XUSB_REPORT		xusb_report;
			};
		};
		struct {
			double				mx, my;
			double				sx, sy;
		};
	};
};

VirtualDevice* get_dummy_device();

void scc_virtual_ds4_set_button(struct Internal* idev, Keycode key, bool pressed);
void scc_virtual_xusb_set_button(struct Internal* idev, Keycode key, bool pressed);

void winapi_keyboard_button(struct Internal* idev, Keycode key, bool pressed);
void winapi_mouse_button(struct Internal* idev, Keycode key, bool pressed);
void flush_mouse(struct Internal* idev);

VirtualDevice* setup_gamepad(const VirtualDeviceSettings* settings);
VirtualDevice* setup_winapi_device(VirtualDeviceType type, const VirtualDeviceSettings* settings);
