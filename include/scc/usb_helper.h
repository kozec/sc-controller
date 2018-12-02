/**
 * SC Controller - USB Helper
 *
 * Wrapper for some libusb functions. Most of gamepad drivers will need exectly
 * two things, and those are here.
 */

#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/controller.h"
#include <stdbool.h>
#include <stdint.h>

struct Daemon;
typedef struct libusb_device_handle* USBDevHandle;

typedef void (*sccd_usb_input_read_cb)(struct Daemon* d, USBDevHandle hndl, uint8_t endpoint, const uint8_t* data, void* userdata);

typedef struct USBHelper {
	/**
	 * Opens USB device represented by given syspath.
	 *
	 * Returns opaque pointer to something only libusb knows about,
	 * or NULL on failure.
	 */
	USBDevHandle	(*open)(const char* syspath);
	/** Closes given USBDevHandle */
	void			(*close)(USBDevHandle hndl);
	/**
	 * Claims all interfaces matching specified parameters.
	 * Returns number of claimed interfaces, which will be zero in case of error.
	 */
	int				(*claim_interfaces_by)(USBDevHandle hndl, int cls, int subclass, int protocol);
	/**
	 * Setups kind-of read loop with callback that will be called repeadedly
	 * every time USB device sends new packet.
	 *
	 * This will be done until it device is closed, disconnected or it's canceled
	 * by other error with same effect, in which case callback will be called one
	 * last time with NULL data. Cleanup is automatic.
	 * 
	 * Returns true on success or false on OOM error.
	 */
	bool			(*interupt_read_loop)(USBDevHandle hndl, uint8_t endpoint, int length, sccd_usb_input_read_cb cb, void* userdata);
	/**
	 * Makes synchronous HID write on given USB device.
	 */
	void			(*hid_write)(USBDevHandle hndl, uint16_t idx, uint8_t* data, uint16_t length);
	/**
	 * Makes synchronous HID request on given USB device.
	 * 
	 * There are two ways how to call this method:
	 *  - if 'length' is positive (or zero, but don't do that), method returns
	 *    data responsed by device in freshly allocated buffer that caller has
	 *    to deallocate.
	 *  - if 'length' negative, buffer in which request was stored is reused as
	 *    buffer for response. Doing this prevents possible OOM error.
	 *
	 * In both cases, length of response is same as length of request. Returns
	 * pointer to buffer with response or NULL if request fails.
	 */
	uint8_t*		(*hid_request)(USBDevHandle hndl, uint16_t idx, uint8_t* data, int32_t length);
} USBHelper;


#ifdef __cplusplus
}
#endif
