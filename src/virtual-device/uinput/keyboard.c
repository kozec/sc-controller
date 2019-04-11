/**
 * SC Controller - Uinput Keyboard
 */
#define LOG_TAG "UInput"
#include "scc/utils/logging.h"
#include "scc/conversions.h"
#include "common.h"
#include <stdlib.h>
#include <unistd.h>


static uint16_t* keyboard_buttons = NULL;


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
	ev.value = scc_keycode_to_hw_scan(key);
	write(idev->fd, &ev, sizeof(ev));
}


VirtualDevice* setup_keyboard(const VirtualDeviceSettings* settings) {
	struct uinput_user_dev uidev;
	memset(&uidev, 0, sizeof(uidev));
	if ((settings == NULL) || (settings->name == NULL))
		strncpy(uidev.name, "SC Controller Keyboard", UINPUT_MAX_NAME_SIZE);
	else
		strncpy(uidev.name, settings->name, UINPUT_MAX_NAME_SIZE);
	
	uidev.id.bustype = BUS_USB;
	uidev.id.vendor = 0x28de;
	uidev.id.product = 0x1142;
	uidev.id.version = 1;
	uidev.ff_effects_max = 0;
	
	bool* pressed = malloc(sizeof(bool) * (SCC_KEYCODE_MAX + 1));
	if (keyboard_buttons == NULL) {
		// This array is generated only once
		keyboard_buttons = malloc(sizeof(uint16_t) * (SCC_KEYCODE_MAX + 1));
		if (keyboard_buttons != NULL)
			for (uint16_t i=0; i<=SCC_KEYCODE_MAX; i++)
				keyboard_buttons[i] = i;
	}
	if ((pressed == NULL) || (keyboard_buttons == NULL)) {
		free(pressed);
		LERROR("OOM while allocating uinput device");
		return NULL;
	}
	memset(pressed, 0, sizeof(bool) * (SCC_KEYCODE_MAX + 1));
	
	struct Internal* idev = (struct Internal*)setup_device(VTP_KEYBOARD, uidev,
				NULL, 0,
				keyboard_buttons, SCC_KEYCODE_MAX,
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
