/**
 * SC Controller - Uinput Keyboard
 */
#define LOG_TAG "UInput"
#include "scc/utils/logging.h"
#include "common.h"
#include <stdlib.h>
#include <unistd.h>

VirtualDevice* setup_keyboard(Display* dpy, const VirtualDeviceSettings* settings) {
	struct Internal* idev = malloc(sizeof(struct Internal));
	if (idev == NULL)
		return NULL;
	memset(idev, 0, sizeof(struct Internal));
	idev->type = VTP_KEYBOARD;
	idev->dpy = dpy;
	snprintf((char*)idev->name, NAME_SIZE, "<XTest keyboard outuput 0x%p>", idev);
	
	return (VirtualDevice*)idev;
}
