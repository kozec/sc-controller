/**
 * SC Controller - Vigem-backed gamepad
 */
#define LOG_TAG "UInput"
#include "scc/utils/logging.h"
#include "common.h"

#include <stdlib.h>
#include <stdbool.h>

static PVIGEM_CLIENT vigem = NULL;

static const char* vigem_error_to_string(VIGEM_ERROR err) {
	switch (err) {
		case VIGEM_ERROR_NONE: return "VIGEM_ERROR_NONE";
		case VIGEM_ERROR_BUS_NOT_FOUND: return "VIGEM_ERROR_BUS_NOT_FOUND";
		case VIGEM_ERROR_NO_FREE_SLOT: return "VIGEM_ERROR_NO_FREE_SLOT";
		case VIGEM_ERROR_INVALID_TARGET: return "VIGEM_ERROR_INVALID_TARGET";
		case VIGEM_ERROR_REMOVAL_FAILED: return "VIGEM_ERROR_REMOVAL_FAILED";
		case VIGEM_ERROR_ALREADY_CONNECTED: return "VIGEM_ERROR_ALREADY_CONNECTED";
		case VIGEM_ERROR_TARGET_UNINITIALIZED: return "VIGEM_ERROR_TARGET_UNINITIALIZED";
		case VIGEM_ERROR_TARGET_NOT_PLUGGED_IN: return "VIGEM_ERROR_TARGET_NOT_PLUGGED_IN";
		case VIGEM_ERROR_BUS_VERSION_MISMATCH: return "VIGEM_ERROR_BUS_VERSION_MISMATCH";
		case VIGEM_ERROR_BUS_ACCESS_FAILED: return "VIGEM_ERROR_BUS_ACCESS_FAILED";
		case VIGEM_ERROR_CALLBACK_ALREADY_REGISTERED: return "VIGEM_ERROR_CALLBACK_ALREADY_REGISTERED";
		case VIGEM_ERROR_CALLBACK_NOT_FOUND: return "VIGEM_ERROR_CALLBACK_NOT_FOUND";
		case VIGEM_ERROR_BUS_ALREADY_CONNECTED: return "VIGEM_ERROR_BUS_ALREADY_CONNECTED";
		case VIGEM_ERROR_BUS_INVALID_HANDLE: return "VIGEM_ERROR_BUS_INVALID_HANDLE";
		case VIGEM_ERROR_XUSB_USERINDEX_OUT_OF_RANGE: return "VIGEM_ERROR_XUSB_USERINDEX_OUT_OF_RANGE";
		default:
			return "(unknown error)";
	}
}

VirtualDevice* setup_gamepad(const VirtualDeviceSettings* settings) {
	VIGEM_ERROR err;
	const char* name;
	struct Internal* vdev = malloc(sizeof(struct Internal));
	if (vdev == NULL) {
		LERROR("OOM while allocating virtual device");
		return NULL;
	}
	
	if (vigem == NULL) {
		if ((vigem = vigem_alloc()) == NULL) {
			LERROR("Failed to allocate ViGEm client object");
			free(vdev);
			return NULL;
		}
		err = vigem_connect(vigem);
		if (err != VIGEM_ERROR_NONE) {
			LERROR("Failed to initialize ViGEm client library.");
			LERROR("Check if you have ViGEMBus installed and visit");
			LERROR("https://github.com/kozec/sc-controller/wiki/Running-SC-Controller-on-Windows for more info");
			LERROR("Error was: %s", vigem_error_to_string(err));
			vigem_free(vigem);
			vigem = NULL;
			free(vdev);
			return NULL;
		}
	}
	
	VirtualGamepadType gamepad_type = (settings == NULL) ? VGT_AUTO : settings->gamepad_type;
	OSVERSIONINFO osvi;
	memset(&osvi, 0, sizeof(OSVERSIONINFO));
	osvi.dwOSVersionInfoSize = sizeof(OSVERSIONINFO);
	GetVersionExA(&osvi);
	if ((osvi.dwMajorVersion > 6) || ((osvi.dwMajorVersion == 6) && (osvi.dwMinorVersion >=2))) {
		// Windows 8 or later
		if (gamepad_type == VGT_AUTO)
			gamepad_type = VGT_X360;
	} else {
		// Windows 7
		if (gamepad_type == VGT_AUTO)
			gamepad_type = VGT_DS4;
		if (gamepad_type == VGT_X360) {
			WARN("!!!!!!!!!!");
			WARN("It appears that you've manually configured x360 controller emulation on Windows 7");
			WARN("This will most likely crash your entire system.");
			WARN("Have fun.");
			WARN("!!!!!!!!!!");
		}
	}
	
	if (gamepad_type == VGT_X360) {
		// Xbox controller
		name = "x360 Controller";
		vdev->is_ds4 = false;
		XUSB_REPORT_INIT(&vdev->xusb_report);
		vdev->target = vigem_target_x360_alloc();
		if (vdev->target == NULL) {
			LERROR("vigem_target_x360_alloc failed");
			free(vdev);
			return NULL;
		}
	} else {
		// DS4 controller
		name = "DS4 Gamepad";
		vdev->is_ds4 = true;
		DS4_REPORT_INIT(&vdev->ds4_report);
		vdev->target = vigem_target_ds4_alloc();
		if (vdev->target == NULL) {
			LERROR("vigem_target_ds4_alloc failed");
			free(vdev);
			return NULL;
		}
	}
	
	err = vigem_target_add(vigem, vdev->target);
	if (err != VIGEM_ERROR_NONE) {
		vigem_target_free(vdev->target);
		LERROR("vigem_target_add failed: %s", vigem_error_to_string(err));
		free(vdev);
		return NULL;
	}
	
	snprintf((char*)vdev->name, NAME_SIZE, "<ViGEm %s 0x%p>", name, vdev);
	vdev->type = VTP_GAMEPAD;
	return (VirtualDevice*)vdev;
}


static void scc_virtual_ds4_update(struct Internal* idev) {
	VIGEM_ERROR err = vigem_target_ds4_update(vigem, idev->target, idev->ds4_report);
	if (err != VIGEM_ERROR_NONE)
		WARN("vigem_target_ds4_update failed: %s", vigem_error_to_string(err));
}

static void scc_virtual_ds4_update_dpad(struct Internal* idev) {
	uint16_t value = 0;
	if ((idev->dpad_x == 0) && (idev->dpad_y < 0))
		value = DS4_BUTTON_DPAD_NORTH;
	else if ((idev->dpad_x > 0) && (idev->dpad_y < 0))
		value = DS4_BUTTON_DPAD_NORTHEAST;
	else if ((idev->dpad_x > 0) && (idev->dpad_y == 0))
		value = DS4_BUTTON_DPAD_EAST;
	else if ((idev->dpad_x > 0) && (idev->dpad_y > 0))
		value = DS4_BUTTON_DPAD_SOUTHEAST;
	else if ((idev->dpad_x == 0) && (idev->dpad_y > 0))
		value = DS4_BUTTON_DPAD_SOUTH;
	else if ((idev->dpad_x < 0) && (idev->dpad_y > 0))
		value = DS4_BUTTON_DPAD_SOUTHWEST;
	else if ((idev->dpad_x < 0) && (idev->dpad_y == 0))
		value = DS4_BUTTON_DPAD_WEST;
	else if ((idev->dpad_x < 0) && (idev->dpad_y < 0))
		value = DS4_BUTTON_DPAD_NORTHWEST;
	else
		value = DS4_BUTTON_DPAD_NONE;
	
	idev->ds4_report.wButtons = (idev->ds4_report.wButtons & ~0x0F) | value;
	return scc_virtual_ds4_update(idev);
}

static void scc_virtual_ds4_set_axis(struct Internal* idev, Axis a, AxisValue value) {
	switch (a) {
	case ABS_X:
		idev->ds4_report.bThumbLX = (uint8_t)(0x80 + (value >> 8));
		return scc_virtual_ds4_update(idev);
	case ABS_Y:
		idev->ds4_report.bThumbLY = (uint8_t)(0x80 + (value >> 8));
		return scc_virtual_ds4_update(idev);
	case ABS_Z:
		idev->ds4_report.bTriggerL = (uint8_t)value;
		return scc_virtual_ds4_update(idev);
	case ABS_RX:
		idev->ds4_report.bThumbRX = (uint8_t)(0x80 + (value >> 8));
		return scc_virtual_ds4_update(idev);
	case ABS_RY:
		idev->ds4_report.bThumbRY = (uint8_t)(0x80 + (value >> 8));
		return scc_virtual_ds4_update(idev);
	case ABS_RZ:
		idev->ds4_report.bTriggerR = (uint8_t)value;
		return scc_virtual_ds4_update(idev);
	case ABS_HAT0X:
		idev->dpad_x = value;
		return scc_virtual_ds4_update_dpad(idev);
	case ABS_HAT0Y:
		idev->dpad_y = value;
		return scc_virtual_ds4_update_dpad(idev);
	}
}

static uint16_t convert_ds4_button(Keycode button) {
	switch (button) {
	case BTN_GAMEPAD:	// A
		return DS4_BUTTON_CROSS;
	case BTN_EAST:		// B
		return DS4_BUTTON_CIRCLE;
	case BTN_NORTH:		// X
		return DS4_BUTTON_SQUARE;
	case BTN_WEST:		// Y
		return DS4_BUTTON_TRIANGLE;
	case BTN_START:
		return DS4_BUTTON_SHARE;
	case BTN_SELECT:
		return DS4_BUTTON_OPTIONS;
	case BTN_TL:		// LEFT BUMPER
		return DS4_BUTTON_SHOULDER_LEFT;
	case BTN_TR:		// RIGHT BUMPER
		return DS4_BUTTON_SHOULDER_RIGHT;
	case BTN_THUMBL:	// LEFT STICK PRESSED
		return DS4_BUTTON_THUMB_LEFT;
	case BTN_THUMBR:	// RIGHT STICK PRESSED
		return DS4_BUTTON_THUMB_RIGHT;
	case BTN_MODE:		// HOME
		return DS4_SPECIAL_BUTTON_PS;
	default:
		return 0;
	}
}

void scc_virtual_ds4_set_button(struct Internal* idev, Keycode key, bool pressed) {
	uint16_t button = convert_ds4_button(key);
	if (button < DS4_BUTTON_SQUARE) {
		idev->ds4_report.bSpecial = 
			pressed
			? (idev->ds4_report.bSpecial | (uint8_t)button)
			: (idev->ds4_report.bSpecial & ~(uint8_t)button);
	} else if (button != 0) {
		idev->ds4_report.wButtons = 
			pressed
			? (idev->ds4_report.wButtons | button)
			: (idev->ds4_report.wButtons & ~button);
	}
	return scc_virtual_ds4_update(idev);
}


static void scc_virtual_xusb_update(struct Internal* idev) {
	VIGEM_ERROR err = vigem_target_x360_update(vigem, idev->target, idev->xusb_report);
	if (err != VIGEM_ERROR_NONE)
		WARN("vigem_target_x360_update failed: %s", vigem_error_to_string(err));
}

static void scc_virtual_xusb_update_dpad(struct Internal* idev) {
	uint16_t value = 0;
	if (idev->dpad_x < 0)
		value |= XUSB_GAMEPAD_DPAD_LEFT;
	else if (idev->dpad_x > 0)
		value |= XUSB_GAMEPAD_DPAD_RIGHT;
	if (idev->dpad_y < 0)
		value |= XUSB_GAMEPAD_DPAD_UP;
	else if (idev->dpad_y > 0)
		value |= XUSB_GAMEPAD_DPAD_DOWN;
	
	idev->xusb_report.wButtons = (idev->xusb_report.wButtons & ~0x0F) | value;
	return scc_virtual_xusb_update(idev);
}

static void scc_virtual_xusb_set_axis(struct Internal* idev, Axis a, AxisValue value) {
	switch (a) {
	case ABS_X:
		idev->xusb_report.sThumbLX = value;
		return scc_virtual_xusb_update(idev);
	case ABS_Y:
		idev->xusb_report.sThumbLY = -((int32_t)value+1);
		return scc_virtual_xusb_update(idev);
	case ABS_Z:
		idev->xusb_report.bLeftTrigger = (uint8_t)value;
		return scc_virtual_xusb_update(idev);
	case ABS_RX:
		idev->xusb_report.sThumbRX = value;
		return scc_virtual_xusb_update(idev);
	case ABS_RY:
		idev->xusb_report.sThumbRY = -((int32_t)value+1);
		return scc_virtual_xusb_update(idev);
	case ABS_RZ:
		idev->xusb_report.bRightTrigger = (uint8_t)value;
		return scc_virtual_xusb_update(idev);
	case ABS_HAT0X:
		idev->dpad_x = value;
		return scc_virtual_xusb_update_dpad(idev);
	case ABS_HAT0Y:
		idev->dpad_y = value;
		return scc_virtual_xusb_update_dpad(idev);
	}
}

static uint16_t convert_xusb_button(Keycode button) {
	switch (button) {
	case BTN_GAMEPAD:	// A
		return XUSB_GAMEPAD_A;
	case BTN_EAST:		// B
		return XUSB_GAMEPAD_B;
	case BTN_NORTH:		// X
		return XUSB_GAMEPAD_X;
	case BTN_WEST:		// Y
		return XUSB_GAMEPAD_Y;
	case BTN_START:
		return XUSB_GAMEPAD_START;
	case BTN_SELECT:
		return XUSB_GAMEPAD_BACK;
	case BTN_TL:		// LEFT BUMPER
		return XUSB_GAMEPAD_LEFT_SHOULDER;
	case BTN_TR:		// RIGHT BUMPER
		return XUSB_GAMEPAD_RIGHT_SHOULDER;
	case BTN_THUMBL:	// LEFT STICK PRESSED
		return XUSB_GAMEPAD_LEFT_THUMB;
	case BTN_THUMBR:	// RIGHT STICK PRESSED
		return XUSB_GAMEPAD_RIGHT_THUMB;
	case BTN_MODE:		// HOME
		return XUSB_GAMEPAD_GUIDE;
	default:
		return 0;
	}
}

void scc_virtual_xusb_set_button(struct Internal* idev, Keycode key, bool pressed) {
	uint16_t button = convert_xusb_button(key);
	if (button != 0) {
		idev->xusb_report.wButtons = 
			pressed
			? (idev->xusb_report.wButtons | button)
			: (idev->xusb_report.wButtons & ~button);
	}
	return scc_virtual_xusb_update(idev);
}


void scc_virtual_device_set_axis(VirtualDevice* dev, Axis a, AxisValue value) {
	struct Internal* idev = (struct Internal*)dev;
	if (idev->type == VTP_DUMMY) return;
	
	if ((idev->type == VTP_GAMEPAD) && (idev->is_ds4))
		scc_virtual_ds4_set_axis(idev, a, value);
	else if (idev->type == VTP_GAMEPAD)
		scc_virtual_xusb_set_axis(idev, a, value);
}

