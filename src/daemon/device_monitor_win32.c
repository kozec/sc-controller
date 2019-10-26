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

void sccd_device_monitor_new_device(Daemon* d, const char* syspath, Subsystem sys, Vendor vendor, Product product, int idx) {
	sccd_hotplug_cb cb = NULL;
	const char* key = make_key(sys, vendor, product, idx);
	if (hashmap_get(callbacks, key, (any_t*)&cb) != MAP_MISSING) {
		// I have no value to store in known_devs hashmap yet.
		if (hashmap_put(known_devs, syspath, (void*)1) != MAP_OK)
			return;
		cb(d, syspath, sys, vendor, product, idx);
		return;
	}
	key = make_key(sys, vendor, product, -1);
	if (hashmap_get(callbacks, key, (any_t*)&cb) != MAP_MISSING) {
		// I have no value to store in known_devs hashmap yet.
		if (hashmap_put(known_devs, syspath, (void*)1) != MAP_OK)
			return;
		cb(d, syspath, sys, vendor, product, idx);
	}
}

long int read_long_from_file(const char* filename, int base) {
	char buffer[256];
	FILE* fp = fopen(filename, "r");
	if (fp == NULL) return -1;
	int r = fread(buffer, 1, 255, fp);
	fclose(fp);
	if (r < 1) return -1;
	return strtol(buffer, NULL, base);
}

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

bool sccd_register_hotplug_cb(Subsystem sys, Vendor vendor, Product product, int idx, sccd_hotplug_cb cb) {
	any_t trash;
#ifndef USE_HIDAPI
	if (sys == HIDAPI) {
		WARN("Driver is trying to register callback for %x:%x on hidapi, but hidapi support was disabled at compile time",
					vendor, product);
		return false;
	}
#endif
	const char* key = make_key(sys, vendor, product, idx);
	if (hashmap_get(callbacks, key, &trash) != MAP_MISSING) {
		WARN("Callback for %x:%x is already registered", vendor, product);
		return false;
	}
	if (hashmap_put(callbacks, key, cb) != MAP_OK)
		return false;
	
	enabled_subsystems[sys] = true;
	return true;
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

