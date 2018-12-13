/**
 * SC Controller - Uinput - common definitions
 */
#pragma once

#include "scc/virtual_device.h"
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>

#define NAME_SIZE			256

struct Internal {
	VirtualDeviceType		type;
	const char				name[NAME_SIZE];
	Display*				dpy;
	union {
		struct {
			double			mx, my;
			double			sx, sy;
		};
	};
};

uint32_t* keyboard_x11_keycodes;
size_t keyboard_x11_keycode_count;

void flush_mouse(struct Internal* idev);

VirtualDevice* get_dummy_device();

VirtualDevice* setup_mouse(Display* dpy, const VirtualDeviceSettings* settings);
VirtualDevice* setup_keyboard(Display* dpy, const VirtualDeviceSettings* settings);
