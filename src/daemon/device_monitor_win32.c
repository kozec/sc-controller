/*
 * SC-Controller - Device Monitor - Windows
 *
 * Basically does nothing. Scanning is done by usb_helper
 */
#define LOG_TAG "DevMon"
#include "scc/utils/logging.h"
#include "scc/utils/hashmap.h"
#include "scc/utils/intmap.h"
#include "scc/utils/assert.h"
#include "scc/input_device.h"
#include "daemon.h"
#include <windows.h>
#include <unistd.h>
#include <stdio.h>
#if USE_HIDAPI
#include <winbase.h>
#include <setupapi.h>
#include <hidapi.h>

typedef struct HidapiDevice {
	char							fake_syspath[256];
	intmap_t						idx_to_path;
	enum HidapiDeviceType {
		HIDAPIDT_NEW,
		HIDAPIDT_KNOWN,
		HIDAPIDT_REMOVED
	}								type;
} HidapiDevice;

map_t path_to_hidapidevice = NULL;
#endif

static map_t callbacks;
static map_t known_devs;
static bool enabled_subsystems[] = { false, false };

static char _key[256];
inline static const char* make_key(Subsystem sys, Vendor vendor, Product product, int idx) {
#ifdef USE_HIDAPI
	if (sys == HIDAPI)
		sprintf(_key, "%i:%x:%x.%x", sys, vendor, product, idx);
	else
#endif
		sprintf(_key, "%i:%x:%x", sys, vendor, product);
	return _key;
}

/*
long int read_long_from_file(const char* filename, int base) {
	char buffer[256];
	FILE* fp = fopen(filename, "r");
	if (fp == NULL) return -1;
	int r = fread(buffer, 1, 255, fp);
	fclose(fp);
	if (r < 1) return -1;
	return strtol(buffer, NULL, base);
}
*/

void sccd_device_monitor_init() {
	callbacks = hashmap_new();
	known_devs = hashmap_new();
	ASSERT((callbacks != NULL) && (known_devs != NULL));
#ifdef USE_HIDAPI
	path_to_hidapidevice = hashmap_new();
	ASSERT(path_to_hidapidevice != NULL);
#endif
}

void sccd_device_monitor_close() {
	hashmap_free(callbacks);
	hashmap_free(known_devs);
}


bool sccd_device_monitor_test_filter(Daemon* d, const InputDeviceData* idev, const HotplugFilter* filter) {
	switch (filter->type) {
	case SCCD_HOTPLUG_FILTER_VENDOR:
		// return (ldev->vendor == filter->vendor);
	case SCCD_HOTPLUG_FILTER_PRODUCT:
		// return (ldev->product == filter->product);
	case SCCD_HOTPLUG_FILTER_NAME:
		// name = input_device_get_prop(idev, "device/name");
		// if ((name != NULL) && (strcmp(name, filter->name) == 0)) {
		// 	free(name);
		// 	return true;
		// }
		// free(name);
		return false;
	default:
		return false;
	}
}


static const char* input_device_get_name(const InputDeviceData* idev) {
	return NULL;
}

static int input_device_get_idx(const InputDeviceData* idev) {
	// TODO: This? Used on Windows?
	return -1;
}

static InputDevice* input_device_open(const InputDeviceData* idev) {
#ifdef USE_HIDAPI
	if (idev->subsystem == HIDAPI)
		return sccd_input_hidapi_open(idev->path);
#endif
#ifdef USE_LIBUSB
	if (idev->subsystem == USB)
		return sccd_input_libusb_open(idev->path);
#endif
	return NULL;
}

static char* input_device_get_prop(const InputDeviceData* idev, const char* name) {
	return NULL;
}

static void input_device_free(InputDeviceData* idev) {
	free((char*)idev->path);
	free(idev);
}

static InputDeviceData* input_device_copy(const InputDeviceData* idev) {
	return NULL;
}


void sccd_device_monitor_win32_fill_struct(InputDeviceData* idev) {
	idev->get_prop = input_device_get_prop;
	idev->get_name = input_device_get_name;
	idev->get_idx = input_device_get_idx;
	idev->free = input_device_free;
	idev->open = input_device_open;
	idev->copy = input_device_copy;
}

void sccd_device_monitor_rescan() {
#if !defined(USE_LIBUSB) && !defined(USE_HIDAPI)
#error "At least one of USE_LIBUSB, USE_HIDAPI has to be enabled"
#endif
#ifdef USE_LIBUSB
	sccd_input_libusb_rescan();
#endif
#ifdef USE_HIDAPI
	sccd_input_hidapi_rescan();
#endif
}

