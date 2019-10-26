/**
 * SC Controller - USB helper on BSD
 *
 * libusb doesn't really work as scc would need on *BSD, so this implementation uses uhid instead.
 * That means it can't work with non-hid devices, but nothing like that is supported right now anyway.
 */
#define LOG_TAG "input_bsd"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/intmap.h"
#include "scc/utils/assert.h"
#include "scc/input_device.h"
#include "daemon.h"
#include <dev/usb/usb.h>		// has to be included before dev/usb/usbhid.h
#include <dev/usb/usbhid.h>
#include <sys/errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <errno.h>

typedef struct BSDInputDevice {
	InputDevice				dev;
	int						fd;
} BSDInputDevice;

typedef struct InputInterruptData {
	sccd_input_read_cb		cb;
	InputDevice*			dev;
	uint8_t*				buffer;
	size_t					length;
	void*					userdata;
} InputInterruptData;

static intmap_t input_interupts;

void sccd_input_bsd_init() {
	input_interupts = intmap_new();
	ASSERT(input_interupts != NULL);
}

void sccd_input_bsd_close() {
	// nothing...
}

static void sccd_input_bsd_dev_close(InputDevice* _dev) {
	BSDInputDevice* dev = container_of(_dev, BSDInputDevice, dev);
	close(dev->fd);
	free(dev);
}

static void sccd_input_bsd_hid_write(InputDevice* _dev, uint16_t idx, uint8_t* data, uint16_t length) {
	BSDInputDevice* dev = container_of(_dev, BSDInputDevice, dev);
	struct usb_ctl_report rp;
	int err;
	memset(&rp, 0, sizeof(rp));
	rp.ucr_report = UHID_FEATURE_REPORT;
	memcpy(rp.ucr_data, data, length);
	
	if ((err = ioctl(dev->fd, USB_SET_REPORT, &rp)) < 0)
		WARN("sccd_usb_dev_hid_write: USB_SET_REPORT: %s", strerror(err));
}

static uint8_t* sccd_input_bsd_hid_request(InputDevice* _dev, uint16_t idx, uint8_t* data, int32_t _length) {
	BSDInputDevice* dev = container_of(_dev, BSDInputDevice, dev);
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
	
	if ((err = ioctl(dev->fd, USB_SET_REPORT, &rp)) < 0) {
		LERROR("sccd_usb_dev_hid_request: USB_SET_REPORT: %s", strerror(err));
		return NULL;
	}
	
	if ((err = ioctl(dev->fd, USB_GET_REPORT, &rp)) < 0) {
		LERROR("sccd_usb_dev_hid_request: USB_GET_REPORT: %s", strerror(err));
		return NULL;
	}
	
	memcpy(out_buffer, rp.ucr_data, length);
	return out_buffer;
}

static void input_interrupt_cb(Daemon* d, int fd, void* userdata) {
	struct usb_ctl_report rp;
	InputInterruptData* iid = (InputInterruptData*)userdata;
	int err = read(fd, iid->buffer, iid->length);
	if (err < iid->length) {
		if (err < 0)
			WARN("Read failed from fd %i: %s", fd, strerror(err));
		else
			WARN("Read failed from fd %i", fd);
		// Signalize closing, remove interupt data, unregister from poller and deallocate memory
		iid->cb(d, iid->dev, 0, NULL, iid->userdata);
		intmap_remove(input_interupts, fd);
		sccd_poller_remove(fd);
		free(iid);
		return;
	}
	
	iid->cb(d, iid->dev, 0, iid->buffer, iid->userdata);
}

static int sccd_input_bsd_claim_interfaces_by(InputDevice* _dev, int cls, int subclass, int protocol) {
	WARN("sccd_input_bsd_claim_interfaces_by: not supported");
	return 0;
}

static bool sccd_input_bsd_interupt_read_loop(InputDevice* _dev, uint8_t endpoint, int length, sccd_input_read_cb cb, void* userdata) {
	BSDInputDevice* dev = container_of(_dev, BSDInputDevice, dev);
	InputInterruptData* iid = malloc(sizeof(InputInterruptData));
	if (iid == NULL)
		goto sccd_usb_dev_interupt_read_loop_fail;
	iid->buffer = malloc(length);
	if (iid->buffer == NULL)
		goto sccd_usb_dev_interupt_read_loop_fail;
	if (intmap_put(input_interupts, dev->fd, iid) != MAP_OK)
		goto sccd_usb_dev_interupt_read_loop_fail;
	
	iid->userdata = userdata;
	iid->length = length;
	iid->dev = _dev;
	iid->cb = cb;
	if (!sccd_poller_add(dev->fd, &input_interrupt_cb, (void*)iid))
		goto sccd_usb_dev_interupt_read_loop_fail;
	return true;
	
sccd_usb_dev_interupt_read_loop_fail:
	LERROR("sccd_usb_dev_interupt_read_loop: out of memory");
	if (iid != NULL)
		free(iid->buffer);
	free(iid);
	intmap_remove(input_interupts, dev->fd);
	return false;
}

InputDevice* sccd_input_bsd_open(const char* syspath) {
	BSDInputDevice* dev = (BSDInputDevice*)malloc(sizeof(BSDInputDevice));
	if (dev == NULL) {
		LERROR("sccd_input_bsd_open: out of memory");
		return NULL;
	}
	dev->fd = open(syspath, O_RDWR);
	if (dev->fd < 0) {
		LERROR("sccd_input_bsd_open: %s: %s", syspath, strerror(dev->fd));
		free(dev);
		return NULL;
	}
	
	*((Subsystem*)(&dev->dev.sys)) = UHID;
	dev->dev.close = sccd_input_bsd_dev_close;
	dev->dev.claim_interfaces_by = sccd_input_bsd_claim_interfaces_by;
	dev->dev.interupt_read_loop  = sccd_input_bsd_interupt_read_loop;
	dev->dev.hid_request = sccd_input_bsd_hid_request;
	dev->dev.hid_write = sccd_input_bsd_hid_write;
	
	return &dev->dev;
}

