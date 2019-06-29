/**
 * SC Controller - Uinput Mouse
 */
#define LOG_TAG "UInput"
#include "scc/utils/logging.h"
#include "common.h"
#include <stdlib.h>
#include <unistd.h>
#include <math.h>

#define XSCALE 0.006
#define YSCALE 0.006
#define SCR_XSCALE 0.0005
#define SCR_YSCALE 0.0005

static uint16_t mouse_buttons[] = {
	BTN_LEFT, BTN_RIGHT, BTN_MIDDLE, BTN_SIDE, BTN_EXTRA
};

static uint16_t mouse_rels[] = {
	REL_X, REL_Y, REL_WHEEL, REL_HWHEEL
};


VirtualDevice* setup_mouse(const VirtualDeviceSettings* settings) {
	struct uinput_user_dev uidev;
	memset(&uidev, 0, sizeof(uidev));
	if ((settings == NULL) || (settings->name == NULL))
		strncpy(uidev.name, "SC Controller Mouse", UINPUT_MAX_NAME_SIZE);
	else
		strncpy(uidev.name, settings->name, UINPUT_MAX_NAME_SIZE);
	uidev.id.bustype = BUS_USB;
	uidev.id.vendor = 0x28de;
	uidev.id.product = 0x1142;
	uidev.id.version = 1;
	uidev.ff_effects_max = 0;

	struct Internal* idev = (struct Internal*)setup_device(VTP_MOUSE, uidev,
				NULL, 0,
				mouse_buttons, sizeof(mouse_buttons) / sizeof(uint16_t),
				mouse_rels, sizeof(mouse_rels) / sizeof(uint16_t)
	);
	if (idev == NULL) return NULL;
	idev->mx = idev->my = 0.0;
	idev->sx = idev->sy = 0.0;
	return (VirtualDevice*)idev;
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

void flush_mouse(struct Internal* idev) {
	if ((idev->mx > 1.0) || (idev->mx < -1.0) || (idev->my > 1.0) || (idev->my < -1.0)) {
		int32_t dx = (int32_t)idev->mx;
		int32_t dy = (int32_t)idev->my;
		idev->mx = fmod(idev->mx, 1.0);
		idev->my = fmod(idev->my, 1.0);
		
		struct input_event ev;
		memset(&ev, 0, sizeof(ev));
		ev.type = EV_REL;
		ev.code = REL_X - SCC_REL_OFFSET; ev.value = dx;
		write(idev->fd, &ev, sizeof(ev));
		ev.code = REL_Y - SCC_REL_OFFSET; ev.value = -dy;
		write(idev->fd, &ev, sizeof(ev));
	}
	
	if ((idev->sx > 1.0) || (idev->sx < -1.0) || (idev->sy > 1.0) || (idev->sy < -1.0)) {
		int32_t dx = (int32_t)idev->sx;
		int32_t dy = (int32_t)idev->sy;
		idev->sx = fmod(idev->sx, 1.0);
		idev->sy = fmod(idev->sy, 1.0);
		
		struct input_event ev;
		memset(&ev, 0, sizeof(ev));
		ev.type = EV_REL;
		ev.code = REL_HWHEEL - SCC_REL_OFFSET; ev.value = dx;
		write(idev->fd, &ev, sizeof(ev));
		ev.code = REL_WHEEL - SCC_REL_OFFSET; ev.value = -dy;
		write(idev->fd, &ev, sizeof(ev));
	}
}
