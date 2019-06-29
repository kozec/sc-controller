/**
 * SC Controller - Uinput - common definitions
 */
#pragma once

#include "scc/virtual_device.h"
#include <linux/input-event-codes.h>
#include <linux/uinput.h>
#include "scc/rel-event-codes.h"

#define UINPUT_PATH "/dev/uinput"
#define NAME_SIZE (UINPUT_MAX_NAME_SIZE + 64)

#if REL_X == 0
#error "scc/rel-event-codes.h not included"
#endif


struct Internal {
	VirtualDeviceType		type;
	int						fd;
	const char				name[NAME_SIZE];
	union {
		struct {
			double			mx, my;
			double			sx, sy;
		};
		bool*				pressed;
	};
};

struct axis {
	uint16_t	id;
	int32_t		min;
	int32_t		max;
	int32_t		fuzz;
	int32_t		flat;
};

void keyboard_scan_event(struct Internal* idev, Keycode key);
void flush_mouse(struct Internal* idev);

VirtualDevice* get_dummy_device();

VirtualDevice* setup_device(VirtualDeviceType type,
							struct uinput_user_dev uidev,
							struct axis* axes, size_t axis_count,
							uint16_t* keys, size_t key_count,
							uint16_t* rels, size_t rel_count);

VirtualDevice* setup_gamepad(const VirtualDeviceSettings* settings);
VirtualDevice* setup_mouse(const VirtualDeviceSettings* settings);
VirtualDevice* setup_keyboard(const VirtualDeviceSettings* settings);
