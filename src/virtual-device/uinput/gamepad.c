/**
 * SC Controller - Uinput Gamepad
 */
#define LOG_TAG "UInput"
#include "scc/utils/logging.h"
#include "common.h"
#include <stdlib.h>
#include <unistd.h>


static uint16_t gamepad_buttons[] = {
	BTN_START, BTN_MODE, BTN_SELECT, BTN_A, BTN_B, BTN_X,
	BTN_Y, BTN_TL, BTN_TR, BTN_THUMBL, BTN_THUMBR
};

static struct axis gamepad_axes[] = {
	{ ABS_X, -32768, 32767, 16, 128 },
	{ ABS_Y, -32768, 32767, 16, 128 },
	{ ABS_RX, -32768, 32767, 16, 128 },
	{ ABS_RY, -32768, 32767, 16, 128 },
	{ ABS_Z, 0, 255, 0, 0 },
	{ ABS_RZ, 0, 255, 0, 0 },
	{ ABS_HAT0X, -1, 1, 0, 0 },
	{ ABS_HAT0Y, -1, 1, 0, 0 },
};


VirtualDevice* setup_gamepad(const VirtualDeviceSettings* settings) {
	struct uinput_user_dev uidev;
	memset(&uidev, 0, sizeof(uidev));
	uidev.id.bustype = BUS_USB;
	if ((settings == NULL) || (settings->name == NULL)) {
		strncpy(uidev.name, "Microsoft X-Box 360 pad", UINPUT_MAX_NAME_SIZE);
		uidev.id.vendor = settings->gamepad.vendor_id;
		uidev.id.product = settings->gamepad.product_id;
		uidev.id.version = settings->gamepad.version;
	} else {
		strncpy(uidev.name, settings->name, UINPUT_MAX_NAME_SIZE);
		uidev.id.vendor = 0x045e;
		uidev.id.product = 0x110;
		uidev.id.version = 1;
	}
	uidev.ff_effects_max = 0;
	
	return setup_device(VTP_GAMEPAD, uidev,
				gamepad_axes, sizeof(gamepad_axes) / sizeof(struct axis),
				gamepad_buttons, sizeof(gamepad_buttons) / sizeof(uint16_t),
				NULL, 0);
}


void scc_virtual_device_set_axis(VirtualDevice* dev, Axis a, AxisValue value) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY) return;
	
	struct input_event ev;
	memset(&ev, 0, sizeof(ev));
	ev.type = EV_ABS;
	ev.code = a;
	ev.value = value;
	write(idev->fd, &ev, sizeof(ev));
}

