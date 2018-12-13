/**
 * SC Controller - USB helper on BSD
 *
 * libusb doesn't really work as scc would need on *BSD, so this implementation
 * uses uhid instead. Nonetheless, usb descriptor parsing functions here are
 * taken from libusb source code.
 *
 * That means it can't work with non-hid devices, but none are supported right
 * now anyway.
 */
#define LOG_TAG "USB"
#include "scc/utils/strbuilder.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "daemon.h"
#include <dev/usb/usb.h>
#include <dev/usb/usbhid.h>
#include <sys/errno.h>
#include <usbhid.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <errno.h>

static USBDevHandle sccd_usb_dev_open_by_syspath(const char* syspath);
static bool sccd_usb_dev_interupt_read_loop(USBDevHandle dev, uint8_t endpoint, int length, sccd_usb_input_read_cb cb, void* userdata);
static bool sccd_usb_dev_open_uhid(USBDevHandle handle, uint index);
static void sccd_usb_dev_hid_write(USBDevHandle hndl, uint16_t idx, uint8_t* data, uint16_t length);
static uint8_t* sccd_usb_dev_hid_request(USBDevHandle hndl, uint16_t idx, uint8_t* data, int32_t length);
static void sccd_usb_dev_close(USBDevHandle dev);

static USBHelper usb_helper = {
	.open						= sccd_usb_dev_open_by_syspath,
	.close						= sccd_usb_dev_close,
	.open_uhid					= sccd_usb_dev_open_uhid,
	.interupt_read_loop			= sccd_usb_dev_interupt_read_loop,
	.hid_write					= sccd_usb_dev_hid_write,
	.hid_request				= sccd_usb_dev_hid_request,
};

typedef struct InputInterruptData {
	sccd_usb_input_read_cb			cb;
	USBDevHandle					hndl;
	uint8_t							endpoint;
	uint8_t*						buffer;
	void*							userdata;
} InputInterruptData;

#define CDESCS_MAX					16
#define DT_CONFIG_SIZE				9

struct usbhelper_handle {
	int								fd;
	uint8_t							bus;
	uint8_t							dev;
	struct usb_device_info			di;
	struct usb_device_cdesc			cdescs[CDESCS_MAX];
	int								uhids[USB_MAX_DEVNAMES];
};


struct libusb_interface_descriptor {
	uint8_t  bLength;
	uint8_t  bDescriptorType;
	uint8_t  bInterfaceNumber;
	uint8_t  bAlternateSetting;
	uint8_t  bNumEndpoints;
	uint8_t  bInterfaceClass;
	uint8_t  bInterfaceSubClass;
	uint8_t  bInterfaceProtocol;
	uint8_t  iInterface;
	const void* endpoint;
	const unsigned char* extra;
	int extra_length;
};

struct libusb_interface {
	const struct libusb_interface_descriptor* altsetting;
	int num_altsetting;
};

struct libusb_config_descriptor {
	uint8_t  bLength;
	uint8_t  bDescriptorType;
	uint16_t wTotalLength;
	uint8_t  bNumInterfaces;
	uint8_t  bConfigurationValue;
	uint8_t  iConfiguration;
	uint8_t  bmAttributes;
	uint8_t  MaxPower;
	const struct libusb_interface* interface;
	const unsigned char* extra;
	int extra_length;
};

typedef LIST_TYPE(InputInterruptData) InterruptDataList;

/**
 * It's not possible to send packets while in input_interrupt_cb. To overcome
 * this problem, recieved packets are stored and processed only after all
 * libusb_handle_events_timeout_completed processing is done.
 */
static InterruptDataList scheduled_interupts;


void sccd_usb_helper_init() {
	scheduled_interupts = list_new(InputInterruptData, 32);
}

void sccd_usb_helper_close() {
	
}

USBHelper* sccd_get_usb_helper() {
	return &usb_helper;
}

static USBDevHandle sccd_usb_dev_open_by_syspath(const char* syspath) {
	char busnode[16];
	if (strstr(syspath, "/bsd/usb/") != syspath)
		return NULL;
	const char* s_bus = syspath + strlen("/bsd/usb/");
	const char* s_dev = strstr(s_bus, "/") + 1;
	long bus = strtol(s_bus, NULL, 16);
	long dev = strtol(s_dev, NULL, 16);
	
	snprintf(busnode, sizeof(busnode), "/dev/usb%li", bus);
	int fd = open(busnode, O_RDWR);
	if (fd < 1) {
		WARN("could not open %s", busnode);
		return NULL;
	}
	struct usbhelper_handle* handle = malloc(sizeof(struct usbhelper_handle));
	if (handle == NULL) {
		LERROR("OOM while opening usb device");
		goto sccd_usb_dev_open_by_syspath_fail;
	}
	handle->di.udi_addr = dev;
	for (size_t i = 0; i<USB_MAX_DEVNAMES; i++)
		handle->uhids[i] = -1;
	if (ioctl(fd, USB_DEVICEINFO, &handle->di) < 0) {
		WARN("could not open USB %i:%i: ioctl USB_DEVICEINFO failed", bus, dev);
		goto sccd_usb_dev_open_by_syspath_fail;
	}
	handle->fd = fd;
	handle->bus = bus;
	handle->dev = dev;
	return handle;
	
sccd_usb_dev_open_by_syspath_fail:
	free(handle);
	close(fd);
	return NULL;
}

static void sccd_usb_dev_close(USBDevHandle handle) {
	close(handle->fd);
	free(handle);
}

static bool get_fdesc(USBDevHandle handle, int idx, struct usb_device_fdesc* fdesc, void* data, size_t size) {
	fdesc->udf_bus = handle->bus;
	fdesc->udf_addr = handle->dev;
	fdesc->udf_config_index = idx;
	fdesc->udf_size = size;
	fdesc->udf_data = data;
	return ioctl(handle->fd, USB_DEVICE_GET_FDESC, fdesc) >= 0;
}

static bool sccd_usb_dev_open_uhid(USBDevHandle handle, uint idx) {
	char uhidnode[32];
	if ((idx < 0) || (idx >= USB_MAX_DEVNAMES)) {
		WARN("sccd_usb_dev_open_uhid: invalid index");
		return false;
	}
	if (handle->uhids[idx] != -1) {
		WARN("sccd_usb_dev_open_uhid: uhid device %i is already open", idx);
		return false;
	}
	if (strstr(handle->di.udi_devnames[idx], "uhidev") != handle->di.udi_devnames[idx]) {
		WARN("sccd_usb_dev_open_uhid: no device with index %i", idx);
		return false;
	}
	
	snprintf(uhidnode, 32, "/dev/uhid%s", handle->di.udi_devnames[idx] + 6);
	int fd = open(uhidnode, O_RDWR);
	if (fd < 0) {
		WARN("sccd_usb_dev_open_uhid: %s: %s", uhidnode, strerror(errno));
		return false;
	}
	
	DDEBUG("Assigned %s to idx %i", uhidnode, idx);
	handle->uhids[idx] = fd;
	return true;
}

static void sccd_usb_dev_hid_write(USBDevHandle hndl, uint16_t idx, uint8_t* data, uint16_t length) {
	
}

static uint8_t* sccd_usb_dev_hid_request(USBDevHandle hndl, uint16_t idx, uint8_t* data, int32_t _length) {
	uint16_t length;
	uint8_t* out_buffer = NULL;
	bool use_same_buffer = false;
	if ((idx < 0) || (idx >= USB_MAX_DEVNAMES) || (hndl->uhids[idx] < 0)) {
		WARN("sccd_usb_dev_hid_request: invalid index");
		return NULL;
	}
	if (_length < 0) {
		use_same_buffer = true;
		length = (uint16_t)(-_length);
		out_buffer = data;
	} else {
		length = (uint16_t)_length;
		out_buffer = malloc(length);
		if (out_buffer == NULL) {
			LERROR("sccd_usb_dev_hid_request: OOM Error");
			return NULL;
		}
	}
	
	struct usb_ctl_report rp;
	int err;
	memset(&rp, 0, sizeof(rp));
	rp.ucr_report = UHID_FEATURE_REPORT;
	memcpy(rp.ucr_data, data, length);
	
	if ((err = ioctl(hndl->uhids[idx], USB_SET_REPORT, &rp)) < 0) {
		LERROR("sccd_usb_dev_hid_request: USB_SET_REPORT: %s", strerror(err));
		return NULL;
	}
	
	if ((err = ioctl(hndl->uhids[idx], USB_GET_REPORT, &rp)) < 0) {
		LERROR("sccd_usb_dev_hid_request: USB_GET_REPORT: %s", strerror(err));
		return NULL;
	}
	
	memcpy(out_buffer, rp.ucr_data, length);
	return out_buffer;
}

static bool sccd_usb_dev_interupt_read_loop(USBDevHandle hndl, uint8_t endpoint, int length, sccd_usb_input_read_cb cb, void* userdata) {
	Daemon* d = get_daemon();
	
	return false;
}
