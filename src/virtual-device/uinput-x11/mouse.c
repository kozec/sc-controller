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
#define SCR_XSCALE 0.00075
#define SCR_YSCALE 0.00075


VirtualDevice* setup_mouse(Display* dpy, const VirtualDeviceSettings* settings) {
	struct Internal* idev = malloc(sizeof(struct Internal));
	if (idev == NULL)
		return NULL;
	memset(idev, 0, sizeof(struct Internal));
	idev->type = VTP_MOUSE;
	idev->dpy = dpy;
	snprintf((char*)idev->name, NAME_SIZE, "<XTest mouse outuput 0x%p>", idev);
	
	return (VirtualDevice*)idev;
}


void scc_virtual_device_mouse_move(VirtualDevice* dev, double dx, double dy) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type != VTP_MOUSE) return;
	idev->mx += dx * XSCALE;
	idev->my -= dy * YSCALE;
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
		
		XTestFakeRelativeMotionEvent(idev->dpy, dx, dy, CurrentTime);
		XFlush(idev->dpy);
	}
	
	if ((idev->sx > 1.0) || (idev->sx < -1.0) || (idev->sy > 1.0) || (idev->sy < -1.0)) {
		int32_t dx = (int32_t)idev->sx;
		int32_t dy = (int32_t)idev->sy;
		idev->sx = fmod(idev->sx, 1.0);
		idev->sy = fmod(idev->sy, 1.0);
		
		// TODO: This
	}
}

