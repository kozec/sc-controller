/**
 * SC Controller - USB helper
 *
 * Common code for USB-based drivers. Basically just wraps some libusb functions
 * so I don't have to write same code all over the place.
 *
 * It also contains only libusb context, because having more of those is not
 * really good idea.
 */
#define LOG_TAG "USB"
#include "scc/utils/strbuilder.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "daemon.h"
#include <libusb-1.0/libusb.h>	// libusb.h has to be included before daemon.h
#include <stdlib.h>

static libusb_context* ctx;

static void sccd_usb_helper_mainloop(Daemon* d);
static USBDevHandle sccd_usb_dev_open_by_syspath(const char* syspath);
static bool sccd_usb_dev_interupt_read_loop(USBDevHandle dev, uint8_t endpoint, int length, sccd_usb_input_read_cb cb, void* userdata);
static int sccd_usb_dev_claim_interfaces_by(USBDevHandle dev, int cls, int subclass, int protocol);
static void sccd_usb_dev_hid_write(USBDevHandle hndl, uint16_t idx, uint8_t* data, uint16_t length);
static uint8_t* sccd_usb_dev_hid_request(USBDevHandle hndl, uint16_t idx, uint8_t* data, int32_t length);
static void sccd_usb_dev_close(USBDevHandle dev);

static USBHelper usb_helper = {
	.open						= sccd_usb_dev_open_by_syspath,
	.close						= sccd_usb_dev_close,
	.claim_interfaces_by		= sccd_usb_dev_claim_interfaces_by,
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


typedef LIST_TYPE(InputInterruptData) InterruptDataList;

/**
 * It's not possible to send packets while in input_interrupt_cb. To overcome
 * this problem, recieved packets are stored and processed only after all
 * libusb_handle_events_timeout_completed processing is done.
 */
static InterruptDataList scheduled_interupts;

void sccd_usb_helper_init() {
	Daemon* d = get_daemon();
	int err;
	scheduled_interupts = list_new(InputInterruptData, 32);
	// Because I need to use this on Windows, only real way to
	// get polling done is by calling libusb_handle_events
	// from mainloop
	ASSERT(d->mainloop_cb_add(&sccd_usb_helper_mainloop));
	
	if ((err = libusb_init(&ctx)) != 0) {
		FATAL("Failed to initialize libusb: %s", libusb_strerror(err));
		return;
	}
}

void sccd_usb_helper_close() {
	libusb_exit(ctx);
}

USBHelper* sccd_get_usb_helper() {
	return &usb_helper;
}

static void sccd_usb_helper_mainloop(Daemon *d) {
#ifdef _WIN32
	static struct timeval timeout;
	sccd_scheduler_get_sleep_time(&timeout);	
	libusb_handle_events_timeout_completed(ctx, &timeout, NULL);
#else
	static struct timeval zero = { 0, 0 };
	libusb_handle_events_timeout_completed(ctx, &zero, NULL);
#endif
	if (list_len(scheduled_interupts) > 0) {
		Daemon* d = get_daemon();
		for (size_t i=0; i<list_len(scheduled_interupts); i++) {
			InputInterruptData* idata = scheduled_interupts->items[i];
			idata->cb(d, idata->hndl, idata->endpoint, idata->buffer, idata->userdata);
			free(idata->buffer);
			free(idata);
		}
		list_clear(scheduled_interupts);
	}
}

// Used by win32.c
static libusb_context* sccd_usb_get_context() {
	return ctx;
}

/** 
 * For given syspath, reads and sets busnum and devnum.
 * Returns true on success
 */
static bool get_usb_address(const char* syspath, uint8_t* bus, uint8_t* dev) {
	int i;
	#define BUFFER_SIZE 4096
	char fullpath[BUFFER_SIZE];
#ifdef _WIN32
	if (strstr(syspath, "/win32/usb/") == syspath) {
		// Special case, this fake path is generated when enumerating
		// devices on Windows.
		// strtol is used to parse VendorId and ProductId from string.
		const char* s_bus = syspath + strlen("/win32/usb/");
		const char* s_dev = strstr(s_bus, "/") + 1;
		long l_bus = strtol(s_bus, NULL, 16);
		long l_dev = strtol(s_dev, NULL, 16);
		*bus = (uint8_t)l_bus;
		*dev = (uint8_t)l_dev;
		return true;
	}
#endif
	if (snprintf(fullpath, BUFFER_SIZE, "%s/busnum", syspath) >= BUFFER_SIZE)
		// Syspath is sooo long it shouldn't be even possible
		return false;
	if ((i = read_long_from_file(fullpath, 10)) < 0)
		// Failed to read
		return false;
	*bus = (uint8_t)i;
	
	// This has same length as busnum one, so success is guaranteed.
	snprintf(fullpath, BUFFER_SIZE, "%s/devnum", syspath);
	if ((i = read_long_from_file(fullpath, 10)) < 0)
		// Failed to read
		return false;
	*dev = (uint8_t)i;
	return true;
}

static USBDevHandle sccd_usb_dev_open_by_syspath(const char* syspath) {
	USBDevHandle hndl = NULL;
	libusb_device** list = NULL;
	uint8_t syspath_bus;
	uint8_t syspath_dev;
	if (!get_usb_address(syspath, &syspath_bus, &syspath_dev)) {
		LERROR("Failed to determine device address for '%s'", syspath);
		goto sccd_usb_helper_open_by_syspath_end;
	}
	
	ssize_t count = libusb_get_device_list(ctx, &list);
	for (ssize_t i=0; i<count; i++) {
		uint8_t bus = libusb_get_bus_number(list[i]);
		uint8_t dev = libusb_get_device_address(list[i]);
		if ((bus == syspath_bus) && (dev == syspath_dev)) {
			int err;
			if ((err = libusb_open(list[i], (struct libusb_device_handle**)&hndl)) != 0) {
				LERROR("Failed to open device %u on bus %u: %s",
							syspath_dev, syspath_bus, libusb_strerror(err));
				hndl = NULL;
				goto sccd_usb_helper_open_by_syspath_end;
			}
			libusb_set_auto_detach_kernel_driver(hndl, 1);
			goto sccd_usb_helper_open_by_syspath_end;
		}
	}
	LERROR("Device %u on bus %u not found", syspath_dev, syspath_bus);
sccd_usb_helper_open_by_syspath_end:
	if (list != NULL)
		libusb_free_device_list(list, 1);
	return hndl;
}

static void sccd_usb_dev_close(USBDevHandle hndl) {
	libusb_close(hndl);
}

static int sccd_usb_dev_claim_interfaces_by(USBDevHandle hndl, int cls, int subclass, int protocol) {
	struct libusb_config_descriptor* desc;
	struct libusb_device* dev = libusb_get_device(hndl);
	int count = 0;
	for (uint8_t i=0; ; i++) {
		int err = libusb_get_config_descriptor(dev, i, &desc);
		if (err == LIBUSB_ERROR_NOT_FOUND) break;
		if (err != 0) {
			LERROR("libusb_get_config_descriptor: %s", libusb_strerror(err));
			return 0;
		}
		for (uint8_t n=0; n<desc->bNumInterfaces; n++) {
			const struct libusb_interface* ifc = &desc->interface[n];
			for (uint8_t m=0; m<ifc->num_altsetting; m++) {
				const struct libusb_interface_descriptor* alt = &ifc->altsetting[m];
				if ((alt->bInterfaceClass == cls) && (alt->bInterfaceSubClass == subclass) && (alt->bInterfaceProtocol == protocol)) {
					// Got one!
					int err = libusb_claim_interface(hndl, alt->bInterfaceNumber);
					if (err != 0) {
						LERROR("libusb_claim_interface: %s", libusb_strerror(err));
						// Not fatal. Maybe.
					} else {
#ifndef _WIN32
						libusb_detach_kernel_driver(hndl, alt->bInterfaceNumber);
#endif
						count++;
					}
				}
			}
		}
		libusb_free_config_descriptor(desc);
	}
	return count;
}

static void sccd_usb_dev_hid_write(USBDevHandle hndl, uint16_t idx, uint8_t* data, uint16_t length) {
	uint8_t request_type = (0x21 & ~LIBUSB_ENDPOINT_DIR_MASK) | LIBUSB_ENDPOINT_OUT;
	uint8_t request = 0x09;
	uint16_t value = 0x0300;
	
	int err = libusb_control_transfer(hndl, request_type, request, value,
										idx, (unsigned char *)data, length, 0);
	if (err < 0)
		LERROR("sccd_usb_dev_hid_write: out: %s", libusb_strerror(err));
}

static uint8_t* sccd_usb_dev_hid_request(USBDevHandle hndl, uint16_t idx, uint8_t* data, int32_t _length) {
	uint8_t* out_buffer = NULL;
	bool use_same_buffer = false;
	uint16_t length;
	uint8_t request_type = (0x21 & ~LIBUSB_ENDPOINT_DIR_MASK) | LIBUSB_ENDPOINT_OUT;
	uint8_t request = 0x09;
	uint16_t value = 0x0300;
	if (_length < 0) {
		use_same_buffer = true;
		length = (uint16_t)(-_length);
		out_buffer = data;
	} else {
		length = (uint16_t)_length;
		out_buffer = malloc(length);
		if (out_buffer == NULL) {
			LERROR("sccd_usb_dev_hid_request: OOM Error");
			goto sccd_usb_dev_hid_request_fail;
		}
	}
	
	int err = libusb_control_transfer(hndl, request_type, request, value, idx,
				(unsigned char *)data, length, 500);	// 500 is timeout of 0.5s
	if (err < 0) {
		LERROR("sccd_usb_dev_hid_request: out: %s", libusb_strerror(err));
		goto sccd_usb_dev_hid_request_fail;
	}
	
	request_type = (0xa1 & ~LIBUSB_ENDPOINT_DIR_MASK) | LIBUSB_ENDPOINT_IN;
	request = 0x01;
	err = libusb_control_transfer(hndl, request_type, request, value, idx,
				(unsigned char *)out_buffer, length, 500);
	if (err < 0) {
		LERROR("sccd_usb_dev_hid_request: in: %s", libusb_strerror(err));
		goto sccd_usb_dev_hid_request_fail;
	}
	return out_buffer;
sccd_usb_dev_hid_request_fail:
	if (!use_same_buffer)
		free(out_buffer);
	return NULL;
}

/** Helper function used when input_interrupt_cb runs out of memory */
static bool remove_si_by_device(void* _item, void* hndl) {
	InputInterruptData* item = (InputInterruptData*)_item;
	if (item->hndl == hndl) {
		free(item);
		return false;
	}
	return true;
}

static void input_interrupt_cb(struct libusb_transfer* t) {
	InputInterruptData* idata = (InputInterruptData*)t->user_data;
	InputInterruptData* scheduled = NULL;
	char* buffer_copy = NULL;
	if (!list_allocate(scheduled_interupts, 2))
		goto input_interrupt_cb_oom;
	scheduled = malloc(sizeof(InputInterruptData));
	buffer_copy = malloc(t->actual_length);
	if ((scheduled == NULL) || (buffer_copy == NULL))
		goto input_interrupt_cb_oom;
	
	memcpy(scheduled, idata, sizeof(InputInterruptData));
	scheduled->buffer = memcpy(buffer_copy, t->buffer, t->actual_length);
	scheduled->endpoint = t->endpoint & ~LIBUSB_ENDPOINT_DIR_MASK;
	list_add(scheduled_interupts, scheduled);
	// idata->cb(get_daemon(), idata->hndl, idata->buffer, idata->userdata);
	
	int err = libusb_submit_transfer(t);
	if (err != 0) {
		LERROR("input_interrupt_cb: %s", libusb_strerror(err));
		buffer_copy = NULL;
		scheduled = malloc(sizeof(InputInterruptData));
		if (scheduled == NULL)
			goto input_interrupt_cb_oom;
		memcpy(scheduled, idata, sizeof(InputInterruptData));
		scheduled->buffer = NULL;
		
		list_add(scheduled_interupts, scheduled);
		// idata->cb(get_daemon(), idata->hndl, NULL, idata->userdata);
		goto input_interrupt_cb_error;
	}
	
	return;
	
input_interrupt_cb_oom:
	// This is worst case of possible OOM error so far.
	// When this happens, connection with USB device is closed forcefully
	// and user will need to disconnect and reconnect it from machine
	// to recover.
	free(scheduled); free(buffer_copy);
	LERROR("input_interrupt_cb: out of memory");
	
	// I have to discard all already scheduled interrupts for same device
	list_filter(scheduled_interupts, &remove_si_by_device, idata->hndl);
	idata->cb(get_daemon(), idata->hndl, t->endpoint, NULL, idata->userdata);
	
input_interrupt_cb_error:
	free(idata->buffer);
	free(idata);
	libusb_free_transfer(t);
}

static bool sccd_usb_dev_interupt_read_loop(USBDevHandle hndl, uint8_t endpoint, int length, sccd_usb_input_read_cb cb, void* userdata) {
	uint8_t* buffer = malloc(length);
	InputInterruptData* idata = malloc(sizeof(InputInterruptData));
	struct libusb_transfer* t = libusb_alloc_transfer(0);
	if ((buffer == NULL) || (t == NULL))
		goto sccd_usb_dev_interupt_read_loop_fail;
	
	idata->cb = cb;
	idata->hndl = hndl;
	idata->buffer = buffer;
	idata->userdata = userdata;
	
	libusb_fill_interrupt_transfer(
		t, hndl,
		(endpoint & ~LIBUSB_ENDPOINT_DIR_MASK) | LIBUSB_ENDPOINT_IN,
		buffer,
		length,
		(libusb_transfer_cb_fn)&input_interrupt_cb,
		idata,
		0
	);
	int err = libusb_submit_transfer(t);
	if (err != 0) {
		LERROR("sccd_usb_dev_interupt_read_loop: %s", libusb_strerror(err));
		goto sccd_usb_dev_interupt_read_loop_fail;
	}
	return true;
sccd_usb_dev_interupt_read_loop_fail:
	if (idata != NULL) free(idata);
	if (buffer != NULL) free(buffer);
	if (t != NULL) libusb_free_transfer(t);
	return false;
}

#ifdef _WIN32
void sccd_device_monitor_new_device(Daemon* d, const char* syspath, Subsystem sys, Vendor vendor, Product product);

void sccd_usb_rescan() {
	char fake_syspath_buffer[1024];
	struct libusb_device_descriptor desc;
	libusb_device** list = NULL;
	ssize_t count = libusb_get_device_list(ctx, &list);
	
	for (ssize_t i=0; i<count; i++) {
		if (0 != libusb_get_device_descriptor(list[i], &desc))
			continue;
		uint8_t bus = libusb_get_bus_number(list[i]);
		uint8_t dev = libusb_get_device_address(list[i]);
		snprintf(fake_syspath_buffer, 1024, "/win32/usb/%x/%x", bus, dev);
		sccd_device_monitor_new_device(get_daemon(), fake_syspath_buffer, USB, desc.idVendor, desc.idProduct);
	}
	
	libusb_free_device_list(list, 1);
}

#endif