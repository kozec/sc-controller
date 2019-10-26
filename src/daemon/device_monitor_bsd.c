/*
 * SC-Controller - Device Monitor - BSD
 *
 * BSD version of device monitor monitors only uhid devices.
 * It does so every X seconds and allows stuff to happen when new device is detected.
 */
#define LOG_TAG "DevMon"
#include "scc/utils/logging.h"
#include "scc/utils/hashmap.h"
#include "scc/utils/assert.h"
#include "daemon.h"
#include <dev/usb/usb.h>
#include <sys/errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <errno.h>
#include <stdio.h>

#define UHIDEV						"/dev/uhid"
#define UHID_MAX					32
#define NODE_NAME_MAX				32


static map_t callbacks;
static map_t known_devs;
static bool enabled_subsystems[] = { false, false };

static char _key[256];
inline static const char* make_key(Subsystem sys, Vendor vendor, Product product) {
	sprintf(_key, "%i:%x:%x", sys, vendor, product);
	return _key;
}

void sccd_device_monitor_init() {
	callbacks = hashmap_new();
	known_devs = hashmap_new();
	ASSERT((callbacks != NULL) && (known_devs != NULL));
}

void sccd_device_monitor_close() {
	hashmap_free(callbacks);
	hashmap_free(known_devs);
}

bool sccd_register_hotplug_cb(Subsystem sys, Vendor vendor, Product product, int idx, sccd_hotplug_cb cb) {
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

// TODO: Schedule this to be really done every X seconds
void sccd_device_monitor_rescan() {
	char node_name[NODE_NAME_MAX];
	Daemon* d = get_daemon();
	
	for (int i = 0; i < UHID_MAX; i++) {
		snprintf(node_name, NODE_NAME_MAX, "%s%d", UHIDEV, i);
		int fd = open(node_name, O_RDWR);
		if (fd < 1) {
			if (errno != ENOENT && errno != ENXIO)
				WARN("could not open %s: %s", node_name, strerror(errno));
			continue;
		}
		
		struct usb_device_info di;
		int err = ioctl(fd, USB_GET_DEVICEINFO, &di);
		close(fd);
		if (err < 0)
			continue;
		
		// LOG("Dev: /bsd/usb/%i/%i %i %s %x %x %s %s", di.udi_bus, di.udi_addr, di.udi_addr, node_name, di.udi_vendorNo, di.udi_productNo, di.udi_product, di.udi_vendor);
		sccd_hotplug_cb cb = NULL;
		const char* key = make_key(UHID, di.udi_vendorNo, di.udi_productNo);
		if (hashmap_get(callbacks, key, (any_t*)&cb) != MAP_MISSING) {
			// I have no value to store in known_devs hashmap yet.
			if (hashmap_put(known_devs, node_name, (void*)1) != MAP_OK)
				return;
			cb(d, node_name, UHID, di.udi_vendorNo, di.udi_productNo, 0);
		}
	}
}
