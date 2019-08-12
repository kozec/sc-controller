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


#if 0
static GUID InterfaceClassGuid = {0x4d1e55b2, 0xf16f, 0x11cf, {0x88, 0xcb, 0x00, 0x11, 0x11, 0x00, 0x00, 0x30} };
// #define DEFINE_DEVPROPKEY(name, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8, pid) EXTERN_C const DEVPROPKEY DECLSPEC_SELECTANY name = { { l, w1, w2, { b1, b2,  b3,  b4,  b5,  b6,  b7,  b8 } }, pid }
// DEFINE_DEVPROPKEY(DEVPKEY_Device_Parent, 0x4340a6c5, 0x93fa, 0x4706, 0x97, 0x2c, 0x7b, 0x64, 0x80, 0x08, 0xa5, 0xa7, 8);

void sccd_hidapi_rescan() {
	// I would love to use hid_enumerate here, but it doesn't make difference
	// between multiple devices of same type (like two wired SCs, for example)
	SP_DEVINFO_DATA devinfo_data;
	SP_DEVICE_INTERFACE_DATA device_interface_data;
	SP_DEVICE_INTERFACE_DETAIL_DATA_A* device_interface_detail_data;
	HDEVINFO device_info_set = SetupDiGetClassDevsA(&InterfaceClassGuid, NULL,
									NULL, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE);
	device_interface_data.cbSize = sizeof(SP_DEVICE_INTERFACE_DATA);
	memset(&devinfo_data, 0x0, sizeof(devinfo_data));
	devinfo_data.cbSize = sizeof(SP_DEVINFO_DATA);
	
	for (int device_index=0;; device_index++) {
		int res;
		DWORD required_size = 0;
		res = SetupDiEnumDeviceInterfaces(device_info_set,
				NULL, &InterfaceClassGuid, device_index, &device_interface_data);
		if (!res)
			break;
		
		SetupDiGetDeviceInterfaceDetailA(device_info_set,
				&device_interface_data, NULL, 0, &required_size, NULL);
		device_interface_detail_data = malloc(required_size);
		if (device_interface_detail_data == NULL) {
			WARN("OOM in sccd_hidapi_rescan: failed to allocate device_interface_detail_data");
			break;
		}
		device_interface_detail_data->cbSize = sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA_A);
		res = SetupDiGetDeviceInterfaceDetailA(device_info_set,
				&device_interface_data, device_interface_detail_data,
				required_size, NULL, NULL);
		if (!res)
			goto sccd_hidapi_rescan_devinfo_failed;
		LOG("=== %s ===", device_interface_detail_data->DevicePath);
		for (int i=0; ; i++) {
			uint32_t address = 0;
			uint32_t busno = 0;
			BYTE data[256];
			DWORD real_size;
			DWORD real_count;
			res = SetupDiEnumDeviceInfo(device_info_set, i, &devinfo_data);
			if (!res)
				break;
			DEVPROPKEY arr[64];
			res = SetupDiGetDevicePropertyKeys(device_info_set, &devinfo_data,
						arr, 64, &real_count, 0);
			if (!res)
				continue;
			/*
			res = SetupDiGetDevicePropertyW(device_info_set, &devinfo_data,
						&DEVPKEY_Device_Parent, NULL, data, 255, &real_size, 0);
			if (!res)
				continue;
				*/
			for (int j=0; j<real_count; j++) {
				
			}
			LOG(">>> OK");
			/*
			res = SetupDiGetDeviceRegistryPropertyA(device_info_set,
						&devinfo_data, SPDRP_ADDRESS, NULL, (PBYTE)&address,
						sizeof(uint32_t), &real_size);
			if (!res || (real_size != sizeof(uint32_t)))
				continue;
			res = SetupDiGetDeviceRegistryPropertyA(device_info_set,
						&devinfo_data, SPDRP_BUSNUMBER, NULL, (PBYTE)&busno,
						sizeof(uint32_t), &real_size);
			if (!res || (real_size != sizeof(uint32_t)))
				continue;	
			res = SetupDiGetDeviceRegistryPropertyA(device_info_set,
						&devinfo_data, SPDRP_PHYSICAL_DEVICE_OBJECT_NAME, NULL,
						data, 256, &real_size);
			if (!res) continue;
			// data[real_size + 1] = 0;
			LOG(">>> %x:%x %s", address, busno, data);
			// break;
			*/
		}
sccd_hidapi_rescan_devinfo_failed:
		free(device_interface_detail_data);
	}
	/*
	char fake_syspath_buffer[1024];
	struct hid_device_info* lst = hid_enumerate(0, 0);
	struct hid_device_info* dev = lst;
	while (dev != NULL) {
		snprintf(fake_syspath_buffer, 1024, "/hidapi%s/--/%i", dev->path, dev->interface_number);
		// Following replacement is done only so it looks better in log
		path_replace(fake_syspath_buffer, '\\', '/');
#ifdef _WIN32
		SP_DEVICE_INTERFACE_DATA device_interface_data;
		device_interface_data.cbSize = sizeof(SP_DEVICE_INTERFACE_DATA);	
#else
#error "Implement me!"
#endif
		LOG("> %s %s", wctomb(NULL, dev->serial_number), fake_syspath_buffer);
		//sccd_device_monitor_new_device(get_daemon(), fake_syspath_buffer,
		//								HIDAPI, dev->vendor_id, dev->product_id);
		dev = dev->next;
	}
	hid_free_enumeration(lst);
	*/
}
#endif

void sccd_usb_rescan();
void sccd_hidapi_rescan();

void sccd_device_monitor_rescan() {
	sccd_usb_rescan();
#ifdef USE_HIDAPI
	sccd_hidapi_rescan();
#endif
}

