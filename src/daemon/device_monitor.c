/*
 * SC-Controller - Device Monitor
 *
 * Watches and enumerates physical devices connected to machine using eudev
 * and allows stuff to happen when new one is detected.
 */
#define LOG_TAG "DevMon"
#include "scc/utils/logging.h"
#include "scc/utils/hashmap.h"
#include "scc/utils/assert.h"
#include "daemon.h"
#include <stdio.h>
#include <unistd.h>
#ifndef _WIN32
#include <libudev.h>
static struct udev* ctx;
static struct udev_monitor* monitor;

static bool get_vendor_product(const char* subsystem, const char* syspath, Vendor* vendor, Product* product);
static void on_new_syspath(Daemon* d, const char* subsystem, const char* syspath);
#endif

static map_t callbacks;
static map_t known_devs;
static bool enabled_subsystems[] = { false, false };

static char _key[256];
inline static const char* make_key(Subsystem sys, Vendor vendor, Product product) {
	sprintf(_key, "%i:%x:%x", sys, vendor, product);
	return _key;
}

void sccd_device_monitor_new_device(Daemon* d, const char* syspath, Subsystem sys, Vendor vendor, Product product) {
	sccd_hotplug_cb cb = NULL;
	const char* key = make_key(sys, vendor, product);
	if (hashmap_get(callbacks, key, (any_t*)&cb) != MAP_MISSING) {
		// I have no value to store in known_devs hashmap yet.
		if (hashmap_put(known_devs, syspath, (void*)1) != MAP_OK)
			return;
		cb(d, syspath, sys, vendor, product);
	}
}

#ifndef _WIN32
static void on_new_syspath(Daemon* d, const char* subsystem, const char* syspath) {
	any_t trash;
	if (hashmap_get(known_devs, syspath, &trash) != MAP_MISSING)
		return;		// Device is already known
	
	Subsystem sys = USB;
	Vendor vendor = 0;
	Product product = 0;
	if (strcmp(subsystem  , "input") == 0) {
		sys = INPUT;
		// TODO: Handle input
		// TODO: bluetooth here
		return;
	} else {
		if (!get_vendor_product(subsystem, syspath, &vendor, &product))
			return;
	}
	
	sccd_device_monitor_new_device(d, syspath, sys, vendor, product);
}

static void on_data_ready(Daemon* d, int fd, void* userdata) {
	any_t trash;
	struct udev_device* dev = udev_monitor_receive_device(monitor);
	const char* action = udev_device_get_action(dev);
	const char* subsystem = udev_device_get_subsystem(dev);
	const char* syspath = udev_device_get_syspath(dev);
	int initialized = udev_device_get_is_initialized(dev);
	if (initialized) {
		if (strcmp(action, "bind") == 0) {
			// USB devices are bound
			on_new_syspath(d, subsystem, syspath);
		}
		if (strcmp(action, "add") == 0) {
			if ((strcmp(subsystem, "input") == 0) || (strcmp(subsystem, "bluetooth") == 0)) {
				// bluetooth and input devices are added
				on_new_syspath(d, subsystem, syspath);
			}
		}
	}
	if ((strcmp(action, "remove") == 0) || (strcmp(action, "unbind") == 0)) {
		if (hashmap_get(known_devs, syspath, &trash) != MAP_MISSING) {
			DEBUG("Device '%s' removed", syspath);
			hashmap_remove(known_devs, syspath);
		}
	}
	udev_device_unref(dev);
}

/** 
 * For given syspath, reads and returns Vendor and Product ids.
 * Returns true on success
 */
static bool get_vendor_product(const char* subsystem, const char* syspath, Vendor* vendor, Product* product) {
	#define FULLPATH_MAX 4096
	char fullpath[FULLPATH_MAX];
	snprintf(fullpath, FULLPATH_MAX, "%s/idVendor", syspath);
	if (access(fullpath, F_OK) != -1 ) {
		// syspath/idVendor exists
		long int id;
		id = read_long_from_file(fullpath, 16);
		if (id < 0) return false;
		*vendor = (Vendor)id;
		// when idVendor exists, idProduct should exist as well
		snprintf(fullpath, FULLPATH_MAX, "%s/idProduct", syspath);
		id = read_long_from_file(fullpath, 16);
		if (id < 0) return false;
		*product = (Product)id;
		return true;
	}
	// TODO: Is this needed?
	// if subsystem is None:
	// 	subsystem = DeviceMonitor.get_subsystem(syspath)
	// TODO: This will be needed
	// 	if subsystem == "bluetooth":
	// 		# Search for folder that matches regular expression...
	// 		names = [ name for name in os.listdir(syspath)
	// 			if os.path.isdir(syspath) and RE_BT_NUMBERS.match(name) ]
	// 		if len(names) > 0:
	// 			vendor, product = [ int(x, 16) for x in RE_BT_NUMBERS.match(names[0]).groups() ]
	// 			return vendor, product
	// 		# Above method works for anything _but_ SteamController
	// 		# For that one, following desperate mess is needed
	// 		node = self._dev_for_hci(syspath)
	// 		if node:
	// 			name = node.split("/")[-1]
	// 			if RE_BT_NUMBERS.match(name):
	// 				vendor, product = [ int(x, 16) for x in RE_BT_NUMBERS.match(name).groups() ]
	// 				return vendor, product
	return false;
}
#endif

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
#ifdef _WIN32
}
#else
	Daemon* d = get_daemon();
	ctx = udev_new();
	ASSERT(ctx != NULL);
	monitor = udev_monitor_new_from_netlink(ctx, "udev");
	ASSERT(monitor != NULL);
	ASSERT(d->poller_cb_add(udev_monitor_get_fd(monitor), &on_data_ready, NULL));
}

void sccd_device_monitor_start() {
	udev_monitor_set_receive_buffer_size(monitor, 1);
	udev_monitor_enable_receiving(monitor);
}

static void sccd_device_monitor_rescan_subsystem(Daemon* d, const char* subsystem) {
	struct udev_enumerate* e = udev_enumerate_new(ctx);
	if (e == NULL) {
		WARN("udev_enumerate_new failed for subsystem %s", subsystem);
		return;
	}
	int r = udev_enumerate_add_match_subsystem(e, subsystem);
	if (r < 0) {
		WARN("udev_enumerate_add_match_subsystem failed for subsystem %s", subsystem);
		goto sccd_device_monitor_rescan_subsystem_fail;
		return;
	}
	
	if (udev_enumerate_scan_devices(e) < 0) {
		WARN("udev_enumerate_scan_devices failed for subsystem %s", subsystem);
		goto sccd_device_monitor_rescan_subsystem_fail;
		return;
	}
	
	struct udev_list_entry* entry = udev_enumerate_get_list_entry(e);
	while (entry != NULL) {
		const char* syspath = udev_list_entry_get_name(entry);
		on_new_syspath(d, subsystem, syspath);
		entry = udev_list_entry_get_next(entry);
	}
	
sccd_device_monitor_rescan_subsystem_fail:
	udev_enumerate_unref(e);
}

/** Scans and calls callbacks for already connected devices */
void sccd_device_monitor_rescan() {
	Daemon* d = get_daemon();
	// self._get_hci_addresses()
	// subsytems_to_scan has to have enough space to fit everything from Subsystem enum
	bool subsytems_to_scan[] = { false, false, false };
		
	HashMapIterator iter = iter_get(callbacks);
	FOREACH(const char*, key, iter) {
		int sys;
		int vendor;
		int product;
		sscanf(key, "%i:%x:%x", &sys, &vendor, &product);
		subsytems_to_scan[sys] = true;
	}
	iter_free(iter);
	
	for (int sys=0; sys<sizeof(subsytems_to_scan); sys++) {
		if (!subsytems_to_scan[sys]) continue;	// skip rests
		switch (sys) {
			case USB:
				sccd_device_monitor_rescan_subsystem(d, "usb");
				break;
			case BT:
				sccd_device_monitor_rescan_subsystem(d, "bluetooth");
				break;
			case INPUT:
				sccd_device_monitor_rescan_subsystem(d, "input");
				break;
		}
	}
}
#endif

void sccd_device_monitor_close() {
	hashmap_free(callbacks);
	hashmap_free(known_devs);
#ifndef _WIN32
	udev_monitor_unref(monitor);
	udev_unref(ctx);
#endif
}

bool sccd_register_hotplug_cb(Subsystem sys, Vendor vendor, Product product, sccd_hotplug_cb cb) {
	any_t trash;
	const char* key = make_key(sys, vendor, product);
	if (hashmap_get(callbacks, key, &trash) != MAP_MISSING) {
		WARN("Callback for %x:%x is already registered", vendor, product);
		return false;
	}
	if (hashmap_put(callbacks, key, cb) != MAP_OK)
		return false;
	
	enabled_subsystems[sys] = true;
	return true;
}

#ifdef _WIN32

void sccd_usb_rescan();

void sccd_device_monitor_rescan() {
	sccd_usb_rescan();
}
#endif
