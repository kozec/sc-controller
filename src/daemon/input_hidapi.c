/**
 * SC Controller - Input Device - wrapper for hidapi
 *
 * Check input_device.h to see interface this uses.
 */
#if USE_HIDAPI
#define LOG_TAG "input_hidapi"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/input_device.h"
#include "scc/tools.h"
#include "./hidapi.h"
#include "daemon.h"
#include <stdlib.h>

#define BUFFER_MAX 256
#define DEV_TYPECHECK(dev, method_name, err_return) do {						\
	if (dev->sys != HIDAPI) {													\
		LERROR("" #method_name " called on device of subsystem %i", dev->sys);	\
		return err_return;														\
	} 																			\
} while(0)

static void sccd_input_hidapi_mainloop(Daemon* d);

typedef struct HidapiInputDevice {
	InputDevice			dev;
	hid_device*			hid;
	int					idx;
	struct InputInterruptData {
		sccd_input_read_cb		cb;
		uint8_t*				buffer;
		size_t					length;
		void*					userdata;
	} 					idata;
} HidapiInputDevice;

typedef LIST_TYPE(HidapiInputDevice) InputDeviceList;

/**
 * Unlike with libusb, there is no problem with sending packets at any time,
 * but there is no real interrupt callback.
 *
 * To workaroud this, devices with interrupt callback set are pooled repeadedly
 * to recieve any input packets.
 */
static InputDeviceList devices_with_iterupts;
// TODO: ^^ Maybe actual poll() can be used on BSD/Linux?
// This is needed mostly for Windows, so it probably doesn't matter :(

void sccd_input_hidapi_init() {
	Daemon* d = get_daemon();
	devices_with_iterupts = list_new(HidapiInputDevice, 32);
	ASSERT(d->mainloop_cb_add(&sccd_input_hidapi_mainloop));
	ASSERT(devices_with_iterupts != NULL);
	if (hid_init() != 0) {
		FATAL("Failed to initialize hidapi");
	}
}

void sccd_input_hidapi_close() {
	hid_exit();
}

static void sccd_input_hidapi_dev_close(InputDevice* _dev) {
	DEV_TYPECHECK(_dev, sccd_input_hidapi_dev_close, (void)0);
	HidapiInputDevice* dev = container_of(_dev, HidapiInputDevice, dev);
	hid_close(dev->hid);
	if (dev->idata.buffer != NULL) {
		free(dev->idata.buffer);
		list_remove(devices_with_iterupts, dev);
	}
	free(dev);
}

static int sccd_input_hidapi_claim_interfaces_by(InputDevice* _dev, int cls, int subclass, int protocol) {
	DEV_TYPECHECK(_dev, sccd_input_hidapi_dev_close, 0);
#ifdef _WIN32
	// Claiming interfaces doesn't work / is not needed with HIDAPI on Windows
	return 1;
#endif
	WARN("sccd_input_libusb_claim_interfaces_by called on HIDAPI");
	return 0;
}

static void sccd_input_hidapi_hid_write(InputDevice* _dev, uint16_t idx, uint8_t* data, uint16_t length) {
	DEV_TYPECHECK(_dev, sccd_input_hidapi_dev_close, (void)0);
	HidapiInputDevice* dev = container_of(_dev, HidapiInputDevice, dev);
	hid_write(dev->hid, data, length);
}

static uint8_t* sccd_input_hidapi_hid_request(InputDevice* _dev, uint16_t idx, uint8_t* data, int32_t _length) {
	DEV_TYPECHECK(_dev, sccd_input_hidapi_dev_close, NULL);
	HidapiInputDevice* dev = container_of(_dev, HidapiInputDevice, dev);
	
	uint8_t* out_buffer = NULL;
	bool use_same_buffer = false;
	uint16_t length;
	int err;
	if (_length < 0) {
		use_same_buffer = true;
		length = (uint16_t)(-_length);
		out_buffer = data;
	} else {
		length = (uint16_t)_length;
		out_buffer = malloc(length);
		if (out_buffer == NULL) {
			LERROR("sccd_input_hid_request: OOM Error");
			return NULL;
		}
	}
	
	unsigned char buffer[BUFFER_MAX + 1];
	if (length > BUFFER_MAX) {
		LERROR("sccd_input_hid_request: called with length larger"
				"than supported. Changing BUFFER_MAX will fix this issue");
		return NULL;
	}
	buffer[0] = 0;
	memcpy(&buffer[1], data, length);
	if (dev->idx != idx) {
		LERROR("sccd_input_hid_request: trying to send request to "
				"different idx than device was originally opened for (%i != %i)",
				dev->idx, idx);
		return NULL;
	}
	err = hid_send_feature_report(dev->hid, buffer, length + 1);
	if (err < 0) {
		wcstombs((char*)buffer, hid_error(dev->hid), BUFFER_MAX);
		LERROR("sccd_input_hid_request: hid_send_feature_report failed: %s", buffer);
		goto sccd_input_hid_request_fail;
	}
	err = hid_get_feature_report(dev->hid, buffer, length + 1);
	if (err < 0) {
		wcstombs((char*)buffer, hid_error(dev->hid), BUFFER_MAX);
		LERROR("sccd_input_hid_request: hid_get_feautre_report failed: %s", buffer);
		goto sccd_input_hid_request_fail;
	}
	memcpy(out_buffer, &buffer[1], length);
	return out_buffer;
	
sccd_input_hid_request_fail:
	if (!use_same_buffer)
		free(out_buffer);
	return NULL;
}

static bool sccd_input_hidapi_interupt_read_loop(InputDevice* _dev, uint8_t endpoint, int length, sccd_input_read_cb cb, void* userdata) {
	DEV_TYPECHECK(_dev, sccd_input_hidapi_dev_close, false);
	HidapiInputDevice* dev = container_of(_dev, HidapiInputDevice, dev);
	
	if (dev->idata.buffer != NULL) {
		LERROR("Only one input_read_cb can be attached to hidapi device");
		return false;
	}
	
	dev->idata.cb = cb;
	dev->idata.length = length;
	dev->idata.userdata = userdata;
	dev->idata.buffer = malloc(length);
	if ((dev->idata.buffer == NULL) || (!list_allocate(devices_with_iterupts, 1))) {
		free(dev->idata.buffer);
		return false;
	}
	list_add(devices_with_iterupts, dev);
	return true;
}

static void sccd_input_hidapi_mainloop(Daemon* d) {
	int r;
	FOREACH_IN(HidapiInputDevice*, dev, devices_with_iterupts) {
		// TODO: Handle device disconnecting
		while ((r = hid_read_timeout(dev->hid, dev->idata.buffer, dev->idata.length, 0)) > 0) {
			dev->idata.cb(d,
					&dev->dev,
					dev->idx,
					dev->idata.buffer,
					dev->idata.userdata
			);
		}
	}
}


InputDevice* sccd_input_hidapi_open(const char* syspath) {
#ifdef _WIN32
	char device_path[1024];
	// Get original DevicePath from fake syspath generated by device monitor
	strncpy(device_path, syspath + 8, 1023);
	scc_path_break_slashes(device_path);
#else
	const char* device_path = syspath;
#endif
	
	HidapiInputDevice* dev = malloc(sizeof(HidapiInputDevice));
	if (dev == NULL) {
		LERROR("Failed to open device %s: out of memory", device_path);
		return NULL;
	}
	hid_device* hid = hid_open_path(device_path);
	if (hid == NULL) {
		LERROR("Failed to open device %s: hid_open_path failed", device_path);
		free(dev);
		return NULL;
	}
	
	dev->hid = hid;
	*((Subsystem*)(&dev->dev.sys)) = HIDAPI;
	dev->dev.close = sccd_input_hidapi_dev_close;
	dev->dev.claim_interfaces_by = sccd_input_hidapi_claim_interfaces_by;
	dev->dev.interupt_read_loop  = sccd_input_hidapi_interupt_read_loop;
	dev->dev.hid_request = sccd_input_hidapi_hid_request;
	dev->dev.hid_write = sccd_input_hidapi_hid_write;
	dev->idata.buffer = NULL;
	dev->idx = -1;
	// TODO: Idx in BSD / Linux?
	
#ifdef _WIN32
	char* interface_component = strstr(device_path, "&mi_");
	if (interface_component) {
		char* hex_str = interface_component + 4;
		char* endptr = NULL;
		dev->idx = strtol(hex_str, &endptr, 16);
		if (endptr == hex_str) {
			// Parsing failed
			dev->idx = -1;
		}
	}
#endif
	return &dev->dev;
}


void sccd_input_hidapi_rescan() {
	char fake_syspath_buffer[1024];
#ifdef _WIN32
	struct Win32InputDeviceData wdev = {
		.idev = { .subsystem = HIDAPI, .path = fake_syspath_buffer }
	};
	sccd_device_monitor_win32_fill_struct(&wdev);
#endif
	struct hid_device_info* lst = hid_enumerate(0, 0);
	struct hid_device_info* dev = lst;
	while (dev != NULL) {
		snprintf(fake_syspath_buffer, 1024, "/hidapi/%s", dev->path);
#ifdef _WIN32
		// Following replacement is done only so it looks better in log
		scc_path_fix_slashes(fake_syspath_buffer);
		wdev.product = dev->product_id;
		wdev.vendor = dev->vendor_id;
		wdev.idx = dev->interface_number;
		sccd_device_monitor_new_device(get_daemon(), &wdev.idev);
#endif
		dev = dev->next;
	}
	hid_free_enumeration(lst);
}


#endif

