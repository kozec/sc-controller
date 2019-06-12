/**
 * SC Controller - Virtual device
 * 
 * This is common interface for UInput, Vigem and whateve will I use on Android.
 */

// I would call this "uinput.h", but name's already taken
#pragma once
#include "scc/controller.h"
#include <stdint.h>
#include <stdbool.h>

typedef struct VirtualDevice VirtualDevice;

typedef enum {
	/** Dummy device can take any kind of input and does nothing with it */
	VTP_DUMMY				= 0,
	VTP_GAMEPAD				= 1 << 0,
	VTP_MOUSE				= 1 << 1,
	VTP_KEYBOARD			= 1 << 2,
} VirtualDeviceType;

/**
 * VirtualGamepadType is used in VirtualDeviceSettings struct.
 *
 * On Windows, 'gamepad' member of that struct is ignored and only gamepad_type
 * is used. VGT_AUTO then means 'DS4' on Windows 7 and 'X360' on later.
 *
 * On Linux, VGT_AUTO means using data from 'gamepad' struct and VGT_DS4 or
 * VGT_X360 can be used as shortcuts instead of filling all values.
 */
typedef enum {
	VGT_AUTO				= 0,
	VGT_DS4					= 1,
	VGT_X360				= 2,
} VirtualGamepadType;

typedef struct VirtualDeviceSettings {
	/** Name can be NULL in which case default is used */
	const char*					name;
	union {
		int						mouse_button_count;
		struct {
			int					button_count;
			int					axis_count;
			uint16_t			vendor_id;
			uint16_t			product_id;
			uint16_t			version;
		} gamepad;
		VirtualGamepadType		gamepad_type;
		// There is no keyboard button count, keyboard is not configurable
	};
} VirtualDeviceSettings;

// Unlike everything else, this doesn't work as 'interface', because there are
// methods that make sense only on gamepad or only on mouse and I'm not going
// to create 3 types differing by one method.

/**
 * Creates new virtual device with given name and using provided options.
 * settings or settings->name can be NULL, in which case default(s) are used.
 * Returns NULL on failure;
 */
VirtualDevice* scc_virtual_device_create(VirtualDeviceType type, VirtualDeviceSettings* settings);
/** Closes all handles and deallocates device. No method on method can be called after this. */
void scc_virtual_device_close(VirtualDevice* dev);
/** Returns device type. If you need to call this, you are already doing it wrong :) */
VirtualDeviceType scc_virtual_device_get_type(VirtualDevice* dev);

/**
 * On platforms where X11 is relevant (Linux and BSD), this function should be
 * called with active connection to Xserver before scc_virtual_device_create.
 */
void scc_virtual_device_set_x_display(void* dpy);

/**
 * Returns readable string description of virtual device, good for logging.
 * Returned string should _not_ be deallocated.
 */
const char* scc_virtual_device_to_string(VirtualDevice* dev);
/** Generates scheduled outputs and flushes all buffers buffers */
void scc_virtual_device_flush(VirtualDevice* dev);
/** Releases virtual key or button */
void scc_virtual_device_key_release(VirtualDevice* dev, Keycode key);
/** Presses down virtual key or button */
void scc_virtual_device_key_press(VirtualDevice* dev, Keycode key);
/** Sets value of gamepad axis */
void scc_virtual_device_set_axis(VirtualDevice* dev, Axis a, AxisValue value);
/** Moves mouse by offset */
void scc_virtual_device_mouse_move(VirtualDevice* dev, double dx, double dy);
/** Scrolls mouse wheel by offset */
void scc_virtual_device_mouse_scroll(VirtualDevice* dev, double dx, double dy);

