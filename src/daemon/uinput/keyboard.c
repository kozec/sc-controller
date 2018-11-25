/**
 * SC Controller - Uinput Keyboard
 */
#define LOG_TAG "UInput"
#include "scc/utils/logging.h"
#include "common.h"
#include <stdlib.h>
#include <unistd.h>


static void set_delay_period(struct Internal* idev, int32_t delay, int32_t period) {
	struct input_event ev;
	memset(&ev, 0, sizeof(ev));
	ev.type = EV_REP;
	ev.code = REP_DELAY;
	ev.value = delay;
	write(idev->fd, &ev, sizeof(ev));
	ev.code = REP_PERIOD;
	ev.value = period;
	write(idev->fd, &ev, sizeof(ev));
}


void keyboard_scan_event(struct Internal* idev, Keycode key) {
	struct input_event ev;
	memset(&ev, 0, sizeof(ev));
	ev.type = EV_MSC;
	ev.code = MSC_SCAN;
	ev.value = keyboard_scancodes[key];
	write(idev->fd, &ev, sizeof(ev));
}


VirtualDevice* setup_keyboard(const VirtualDeviceSettings* settings) {
	struct uinput_user_dev uidev;
	memset(&uidev, 0, sizeof(uidev));
	strncpy(uidev.name, (settings->name == NULL) ? "SC Controller Keyboard" :
										settings->name, UINPUT_MAX_NAME_SIZE);
	
	uidev.id.bustype = BUS_USB;
	uidev.id.vendor = 0x28de;
	uidev.id.product = 0x1142;
	uidev.id.version = 1;
	uidev.ff_effects_max = 0;
	
	bool* pressed = malloc(sizeof(bool) * keyboard_scancode_count);
	if (pressed == NULL) {
		LERROR("OOM while allocating uinput device");
		return NULL;
	}
	memset(pressed, 0, sizeof(bool) * keyboard_scancode_count);
	
	struct Internal* idev = (struct Internal*)setup_device(VTP_KEYBOARD, uidev,
				NULL, 0,
				keyboard_buttons, keyboard_button_count,
				NULL, 0
	);
	if (idev == NULL) {
		free(pressed);
		return NULL;
	}
	
	idev->pressed = pressed;
	set_delay_period(idev, 250, 33);
	return (VirtualDevice*)idev;
}
