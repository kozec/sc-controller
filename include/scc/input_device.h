/**
 * SC Controller - Input Device
 *
 * This is just big abstraction over libusb, hidapi, uhid or whatever comes later.
 * Use daemon->hotplug_cb_add to add callback which will recieve InputDeviceData
 * and then call open method to get instance of InputDevice.
 */

#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/controller.h"
#include "scc/driver.h"
#include <stdbool.h>
#include <stdint.h>

typedef struct InputDeviceData InputDeviceData;
typedef struct InputDevice InputDevice;
typedef void (*sccd_input_read_cb)(Daemon* d, InputDevice* dev, uint8_t endpoint, const uint8_t* data, void* userdata);


/* Holds data about not-yet opened device */
typedef struct InputDeviceData {
	/** Describes type and/or backing library of this input device */
	const Subsystem		subsystem;
	/** Syspath or other unique identifier suitable for printing out while debugging */
	const char*			path;
	
	/**
	 * Returns user-friendly name suitable for displaying in UI.
	 * May return NULL.
	 *
	 * Returned string has to be free'd by caller.
	 */
	char*				(*get_name)(const InputDeviceData* idev);
	/**
	 * Returns device index or -1 if index is not used or available */
	int					(*get_idx)(const InputDeviceData* idev);
	/**
	 * Returns other property of device.
	 * Property names are implementation specific.
	 * Returned string has to be free'd by caller.
	 *
	 * Returns NULL if property is not known or memory cannot be allocated.
	 */
	char*				(*get_prop)(const InputDeviceData* idev, const char* name);
	
	/**
	 * Opens assotiated device.
	 * Note that this will not work with EVDEV devices.
	 * For those, use path to open device using udev library directly.
	 *
	 * Returns InputDevice object or NULL on error.
	 */
	InputDevice*		(*open)(const InputDeviceData* idev);
	/**
	 * Creates copy of InputDeviceData.
	 *
	 * InputDeviceData is usually recieved as argument to callback registered
	 * by daemon->hotplug_cb_add method and such object will be valid only
	 * durring that callback. Copy method can be used if driver needs to keep
	 * that passed data.
	 *
	 * Returns copy or NULL if memory cannot be allocated or operation
	 * is not supported.
	 */
	InputDeviceData*	(*copy)(const InputDeviceData* idev);
	/**
	 * Dellocates copy created by copy() method.
	 * It's illegal to call this method on value recieved as argument
	 * to hotplug callback.
	 */
	void				(*free)(InputDeviceData* idev);
} InputDeviceData;


/** Represents handle to already opened device */
typedef struct InputDevice {
	/** Describes type and/or backing library of this input device */
	const Subsystem		sys;
	/**
	 * Claims all interfaces matching specified parameters.
	 * Returns number of claimed interfaces, which will be zero in case of error.
	 *
	 * Available only on libusb devices.
	 */
	int					(*claim_interfaces_by)(InputDevice* dev, int cls, int subclass, int protocol);
	/**
	 * Dellocates device and closes all handles.
	 * InputDevice given as parameter is deallocated by this call and should not
	 * be used anymore.
	 */
	void				(*close)(InputDevice* dev);
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
	bool				(*interupt_read_loop)(InputDevice* dev, uint8_t endpoint, int length, sccd_input_read_cb cb, void* userdata);
	/**
	 * Makes synchronous HID write on given USB device.
	 * 'idx' has meaning only with libusb devices and is ignored for everything else.
	 */
	void				(*hid_write)(InputDevice* dev, uint16_t idx, uint8_t* data, uint16_t length);
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
	uint8_t*			(*hid_request)(InputDevice* dev, uint16_t idx, uint8_t* data, int32_t length);
} InputDevice;


#ifdef __cplusplus
}
#endif

