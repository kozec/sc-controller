/*
 * SC-Controller - Device Monitor - Linux
 *
 * Watches and enumerates physical devices connected to machine using eudev
 * and allows stuff to happen when new one is detected.
 */
#define LOG_TAG "DevMon"
#include "scc/utils/container_of.h"
#include "scc/utils/logging.h"
#include "scc/utils/hashmap.h"
#include "scc/utils/assert.h"
#include "scc/input_device.h"
#include "daemon.h"
#include <sys/stat.h>
#include <libudev.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <fcntl.h>
static struct udev* ctx;
static struct udev_monitor* monitor;

static bool get_vendor_product(const char* subsystem, const char* syspath, Vendor* vendor, Product* product);

struct LinuxInputDeviceData {
	InputDeviceData		idev;
	Vendor				vendor;
	Product				product;
	int					idx;
};

static int input_device_get_idx(const InputDeviceData* idev) {
	const struct LinuxInputDeviceData* ldev = container_of(idev, struct LinuxInputDeviceData, idev);
	return ldev->idx;
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
#ifdef __BSD__
	if (idev->subsystem == UHID)
		return sccd_input_bsd_open(syspath);
#endif
	return NULL;
}

static char* input_device_get_prop(const InputDeviceData* idev, const char* name) {
	// Special handling for vendor/product/name so it's all accessible using same prop names
	if (0 == strcmp(name, "vendor_id")) {
#ifdef USE_LIBUSB
		if (idev->subsystem == USB)
			return input_device_get_prop(idev, "idVendor");
#endif
		if (idev->subsystem == EVDEV)
			return input_device_get_prop(idev, "device/id/vendor");
	}
	if (0 == strcmp(name, "product_id")) {
#ifdef USE_LIBUSB
		if (idev->subsystem == USB)
			return input_device_get_prop(idev, "idProduct");
#endif
		if (idev->subsystem == EVDEV)
			return input_device_get_prop(idev, "device/id/product");
	}
	if (0 == strcmp(name, "version_id")) {
#ifdef USE_LIBUSB
		if (idev->subsystem == USB)
			// TODO: Check this
			return input_device_get_prop(idev, "idVersion");
#endif
		if (idev->subsystem == EVDEV)
			return input_device_get_prop(idev, "device/id/version");
	}
	if (0 == strcmp(name, "unique_id")) {
		char* uniq = idev->get_prop(idev, "device/uniq");
		if (uniq == NULL) {
			char* vendor = idev->get_prop(idev, "vendor_id");
			char* product = idev->get_prop(idev, "product_id");
			if ((vendor != NULL) && (product != NULL))
				uniq = strbuilder_fmt("%s:%s", vendor, product);
			free(vendor);
			free(product);
		}
		return uniq;
	}
	
	StrBuilder* sb = strbuilder_new();
	strbuilder_addf(sb, "%s/%s", idev->path, name);
	if (strbuilder_failed(sb))
		goto input_device_get_prop_fail;
	int fd = open(strbuilder_get_value(sb), O_RDONLY);
	if (fd < 0)
		goto input_device_get_prop_fail;
	strbuilder_clear(sb);
	strbuilder_add_fd(sb, fd);
	strbuilder_rstrip(sb, "\r\n\t ");
	close(fd);
	if (strbuilder_failed(sb))
		goto input_device_get_prop_fail;
	return strbuilder_consume(sb);
input_device_get_prop_fail:
	strbuilder_free(sb);
	return NULL;
}

static char* input_device_get_name(const InputDeviceData* idev) {
#ifdef USE_LIBUSB
	if (idev->subsystem == USB)
		return input_device_get_prop(idev, "product");
#endif
	return input_device_get_prop(idev, "device/name");
}

static void input_device_free_dummy(InputDeviceData* idev) {
}

static void input_device_free(InputDeviceData* idev) {
	struct LinuxInputDeviceData* ldev = container_of(idev, struct LinuxInputDeviceData, idev);
	free((char*)ldev->idev.path);
	free(ldev);
}

static InputDeviceData* input_device_copy(const InputDeviceData* idev) {
	const struct LinuxInputDeviceData* ldev = container_of(idev, struct LinuxInputDeviceData, idev);
	struct LinuxInputDeviceData* copy = malloc(sizeof(struct LinuxInputDeviceData));
	if (copy == NULL) return NULL;
	copy->idev.path = strbuilder_cpy(ldev->idev.path);
	if (copy->idev.path == NULL) {
		free(copy);
		return NULL;
	}
	copy->idev.free = input_device_free;
	return &copy->idev;
}


static void on_new_syspath(Daemon* d, const char* subsystem, const char* syspath) {
	static struct LinuxInputDeviceData ldata = {
		.idev = {
			.get_prop = input_device_get_prop,
			.get_name = input_device_get_name,
			.get_idx = input_device_get_idx,
			.free = input_device_free_dummy,
			.open = input_device_open,
			.copy = input_device_copy,
		}
	};
	
	ldata.idev.path = syspath;
	if (strcmp(subsystem, "input") == 0) {
		// TODO: Bluetooth here?
		*((Subsystem*)&ldata.idev.subsystem) = EVDEV;
		ldata.product = -1;
		ldata.vendor = -1;
	} else {
		if (!get_vendor_product(subsystem, syspath, &ldata.vendor, &ldata.product))
			return;
		*((Subsystem*)&ldata.idev.subsystem) = USB;
	}
	
	sccd_device_monitor_new_device(d, &ldata.idev);
}

bool sccd_device_monitor_test_filter(Daemon* d, const InputDeviceData* idev, const HotplugFilter* filter) {
	const struct LinuxInputDeviceData* ldev = container_of(idev, struct LinuxInputDeviceData, idev);
	char* name;
	switch (filter->type) {
	case SCCD_HOTPLUG_FILTER_VENDOR:
		return (ldev->vendor == filter->vendor);
	case SCCD_HOTPLUG_FILTER_PATH:
		if (strstr(filter->path, "/dev/input/event") == filter->path) {
			// Small special case, I want this to be equivalent of
			// /sys/devices/......./eventXY
			name = malloc(256);
			if (name == NULL) {
				WARN("sccd_device_monitor_test_filter: Out of memory");
				return false;
			}
			strcpy(name, "/dev/input");
			strncat(name, strrchr(idev->path, '/'), 240);
			if (0 == strcmp(name, filter->path)) {
				free(name);
				return true;
			}
			free(name);
		}
		return 0 == strcmp(idev->path, filter->path);
	case SCCD_HOTPLUG_FILTER_PRODUCT:
		return (ldev->product == filter->product);
	case SCCD_HOTPLUG_FILTER_NAME:
		name = input_device_get_prop(idev, "device/name");
		if ((name != NULL) && (0 == strcmp(name, filter->name))) {
			free(name);
			return true;
		}
		free(name);
		return false;
	case SCCD_HOTPLUG_FILTER_UNIQUE_ID: {
		char* unique_id = idev->get_prop(idev, "unique_id");
		if (0 == strcmp(unique_id, filter->id)) {
			free(unique_id);
			return true;
		}
		free(unique_id);
		return false;
	}
	case SCCD_HOTPLUG_FILTER_VIDPID: {
		char* product = idev->get_prop(idev, "product_id");
		char* vendor = idev->get_prop(idev, "vendor_id");
		char* buffer = strbuilder_fmt("%s:%s", vendor, product);
		free(product);
		free(vendor);
		if (0 == strcmp(buffer, filter->vidpid)) {
			free(buffer);
			return true;
		}
		free(buffer);
		return false;
	}
	default:
		return false;
	}
}

static void on_data_ready(Daemon* d, int fd, void* userdata) {
	any_t trash;
	struct udev_device* dev = udev_monitor_receive_device(monitor);
	const char* action = udev_device_get_action(dev);
	const char* subsystem = udev_device_get_subsystem(dev);
	const char* syspath = udev_device_get_syspath(dev);
	int initialized = udev_device_get_is_initialized(dev);
	if ((action == NULL) || (subsystem == NULL) || (syspath == NULL)) {
		// Failed to get device info
		udev_device_unref(dev);
		return;
	}
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
		sccd_device_monitor_device_removed(d, syspath);
	}
	udev_device_unref(dev);
	(void)trash;
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
	sccd_device_monitor_common_init();
	Daemon* d = get_daemon();
	ctx = udev_new();
	ASSERT(ctx != NULL);
	monitor = udev_monitor_new_from_netlink(ctx, "udev");
	ASSERT(monitor != NULL);
	ASSERT(d->poller_cb_add(udev_monitor_get_fd(monitor), &on_data_ready, NULL));
#ifdef USE_HIDAPI
	sccd_input_hidapi_rescan();
#endif
}

void sccd_device_monitor_start() {
	udev_monitor_set_receive_buffer_size(monitor, 1);
	udev_monitor_enable_receiving(monitor);
}

static void sccd_device_monitor_rescan_subsystem(Daemon* d, const char* subsystem) {
	struct udev_enumerate* e = udev_enumerate_new(ctx);
	int evdev = strcmp(subsystem, "input");
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
		if ((evdev == 0) && (strstr(syspath, "/event") == NULL)) {
			entry = udev_list_entry_get_next(entry);
			continue;
		}
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
	uint32_t subsytems_to_scan = sccd_device_monitor_get_enabled_subsystems(d);
	
	for (int sys=0; sys<sizeof(subsytems_to_scan); sys++) {
		if ((subsytems_to_scan & (1 << sys)) == 0)
			continue;
		switch (sys) {
			case USB:
				sccd_device_monitor_rescan_subsystem(d, "usb");
				break;
			case BT:
				sccd_device_monitor_rescan_subsystem(d, "bluetooth");
				break;
			case EVDEV:
				sccd_device_monitor_rescan_subsystem(d, "input");
				break;
		}
	}
}

void sccd_device_monitor_close() {
	sccd_device_monitor_close_common();
	udev_monitor_unref(monitor);
	udev_unref(ctx);
}

