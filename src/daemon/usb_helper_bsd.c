/**
 * SC Controller - USB helper on BSD
 *
 * libusb doesn't really work as scc would need on *BSD, so this implementation uses uhid instead.
 * That means it can't work with non-hid devices, but nothing likt that is supported right now anyway.
 */
#define LOG_TAG "USB"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/intmap.h"
#include "scc/utils/assert.h"
#include "daemon.h"
#include <dev/usb/usb.h>		// has to be included before dev/usb/usbhid.h
#include <dev/usb/usbhid.h>
#include <sys/errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <errno.h>

static bool sccd_usb_dev_interupt_read_loop(USBDevHandle dev, uint8_t endpoint, int length, sccd_usb_input_read_cb cb, void* userdata);
static USBDevHandle sccd_usb_dev_open_uhid(const char* syspath);
static void sccd_usb_dev_hid_write(USBDevHandle hndl, uint16_t idx, uint8_t* data, uint16_t length);
static uint8_t* sccd_usb_dev_hid_request(USBDevHandle hndl, uint16_t idx, uint8_t* data, int32_t length);
static void sccd_usb_dev_close(USBDevHandle dev);


static USBHelper usb_helper = {
	.open_uhid					= sccd_usb_dev_open_uhid,
	.close						= sccd_usb_dev_close,
	.interupt_read_loop			= sccd_usb_dev_interupt_read_loop,
	.hid_write					= sccd_usb_dev_hid_write,
	.hid_request				= sccd_usb_dev_hid_request,
};

typedef struct InputInterruptData {
	void*						userdata;
	void*						buffer;
	uint8_t						endpoint;	// not used for anything but passed to callback
	int							length;
	sccd_usb_input_read_cb		cb;
} InputInterruptData;

static intmap_t input_interupts;


void sccd_usb_helper_init() {
	input_interupts = intmap_new();
	ASSERT(input_interupts != NULL);
}

void sccd_usb_helper_close() {
	
}

USBHelper* sccd_get_usb_helper() {
	return &usb_helper;
}

static void sccd_usb_dev_close(USBDevHandle handle) {
	close(handle);
}

static USBDevHandle sccd_usb_dev_open_uhid(const char* syspath) {
	int fd = open(syspath, O_RDWR);
	if (fd < 0)
		WARN("sccd_usb_dev_open_uhid: %s: %s", syspath, strerror(fd));
	
	return fd;
}

static void sccd_usb_dev_hid_write(USBDevHandle hndl, uint16_t idx, uint8_t* data, uint16_t length) {
	struct usb_ctl_report rp;
	int err;
	memset(&rp, 0, sizeof(rp));
	rp.ucr_report = UHID_FEATURE_REPORT;
	memcpy(rp.ucr_data, data, length);
	
	if ((err = ioctl(hndl, USB_SET_REPORT, &rp)) < 0)
		WARN("sccd_usb_dev_hid_write: USB_SET_REPORT: %s", strerror(err));
}

static uint8_t* sccd_usb_dev_hid_request(USBDevHandle hndl, uint16_t idx, uint8_t* data, int32_t _length) {
	uint16_t length;
	uint8_t* out_buffer = NULL;
	bool use_same_buffer = false;
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
	
	if ((err = ioctl(hndl, USB_SET_REPORT, &rp)) < 0) {
		LERROR("sccd_usb_dev_hid_request: USB_SET_REPORT: %s", strerror(err));
		return NULL;
	}
	
	if ((err = ioctl(hndl, USB_GET_REPORT, &rp)) < 0) {
		LERROR("sccd_usb_dev_hid_request: USB_GET_REPORT: %s", strerror(err));
		return NULL;
	}
	
	memcpy(out_buffer, rp.ucr_data, length);
	return out_buffer;
}

static void input_interrupt_cb(Daemon* d, int hndl, void* userdata) {
	struct usb_ctl_report rp;
	InputInterruptData* iid = (InputInterruptData*)userdata;
	int err = read(hndl, iid->buffer, iid->length);
	if (err < iid->length) {
		if (err < 0)
			WARN("Read failed from fd %i: %s", hndl, strerror(err));
		else
			WARN("Read failed from fd %i", hndl);
		// Signalize closing, remove interupt data, unregister from poller and deallocate memory
		iid->cb(d, hndl, iid->endpoint, NULL, iid->userdata);
		intmap_remove(input_interupts, hndl);
		sccd_poller_remove(hndl);
		free(iid);
		return;
	}
	
	iid->cb(d, hndl, iid->endpoint, iid->buffer, iid->userdata);
}

static bool sccd_usb_dev_interupt_read_loop(USBDevHandle hndl, uint8_t endpoint, int length, sccd_usb_input_read_cb cb, void* userdata) {
	InputInterruptData* iid = malloc(sizeof(InputInterruptData));
	if (iid == NULL)
		goto sccd_usb_dev_interupt_read_loop_fail;
	iid->buffer = malloc(length);
	if (iid->buffer == NULL)
		goto sccd_usb_dev_interupt_read_loop_fail;
	if (intmap_put(input_interupts, hndl, iid) != MAP_OK)
		goto sccd_usb_dev_interupt_read_loop_fail;
	
	iid->userdata = userdata;
	iid->endpoint = endpoint;
	iid->length = length;
	iid->cb = cb;
	if (!sccd_poller_add((int)hndl, &input_interrupt_cb, (void*)iid))
		goto sccd_usb_dev_interupt_read_loop_fail;
	return true;
	
sccd_usb_dev_interupt_read_loop_fail:
	LERROR("sccd_usb_dev_interupt_read_loop: out of memory");
	if (iid != NULL)
		free(iid->buffer);
	free(iid);
	intmap_remove(input_interupts, hndl);
	return false;
}
