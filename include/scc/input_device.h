/**
 * SC Controller - Input Device
 *
 * This is just big abstraction over libusb, hidapi, uhid or whatever comes later.
 * Use daemon->open_input_device to get instance of InputDevice*.
 */

#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/controller.h"
#include "scc/driver.h"
#include <stdbool.h>
#include <stdint.h>

typedef void (*sccd_input_read_cb)(Daemon* d, InputDevice* dev, uint8_t endpoint, const uint8_t* data, void* userdata);


struct InputDevice {
	/** Describes type and/or backing library of this input device */
	const Subsystem	sys;
	/**
	 * Claims all interfaces matching specified parameters.
	 * Returns number of claimed interfaces, which will be zero in case of error.
	 *
	 * Available only on libusb devices.
	 */
	int				(*claim_interfaces_by)(InputDevice* dev, int cls, int subclass, int protocol);
	/**
	 * Dellocates device and closes all handles.
	 * InputDevice given as parameter is deallocated by this call and should not
	 * be used anymore.
	 */
	void			(*close)(InputDevice* dev);
	/**
	 * Setups kind-of read loop with callback that will be called repeadedly
	 * every time USB device sends new packet.
	 *
	 * This will be done until it device is closed, disconnected or it's canceled
	 * by other error with same effect, in which case callback will be called one
	 * last time with NULL data. Cleanup is automatic.
	 *
	 * 'endpoint' has meaning only with libusb devices and is ignored for everything else.
	 *
	 * Returns true on success or false on OOM error.
	 */
	bool			(*interupt_read_loop)(InputDevice* dev, uint8_t endpoint, int length, sccd_input_read_cb cb, void* userdata);
	/**
	 * Makes synchronous HID write on given USB device.
	 * 'idx' has meaning only with libusb devices and is ignored for everything else.
	 */
	void			(*hid_write)(InputDevice* dev, uint16_t idx, uint8_t* data, uint16_t length);
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
	 * In both cases, length of response is assumed to be same as length of request.
	 * Returns pointer to buffer with response or NULL if request fails.
	 *
	 * 'idx' has meaning only with libusb devices and is ignored for everything else.
	 */
	uint8_t*		(*hid_request)(InputDevice* dev, uint16_t idx, uint8_t* data, int32_t length);
} USBHelper;


#ifdef __cplusplus
}
#endif

