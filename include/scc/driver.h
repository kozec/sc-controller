/**
 * Should anyone ever feel need to implement additional 'driver' into SC-Controller,
 * this should be only header he needs to import.
 */

#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/controller.h"
#include <stdbool.h>
#include <stdint.h>
#ifndef DLL_EXPORT
#if defined _WIN32 || defined __CYGWIN__
#	define DLL_EXPORT __declspec(dllexport)
#else
#	if __GNUC__ >= 4
#		define DLL_EXPORT __attribute__((visibility("default")))
#	else
#		define DLL_EXPORT
#	endif
#endif
#endif

struct Daemon;

typedef unsigned short Vendor;
typedef unsigned short Product;
typedef enum {
	USB			= 0,
#ifndef _WIN32
	BT			= 1,
	INPUT		= 2,
#endif
} Subsystem;

#ifdef LIBUSB_H
typedef struct libusb_device_handle* USBDevHandle;
#else
typedef void* USBDevHandle;
#endif

typedef struct Daemon Daemon;
typedef struct Driver Driver;

typedef void (*sccd_mainloop_cb)(Daemon* d);
typedef void (*sccd_poller_cb)(Daemon* d, int fd, void* userdata);
typedef void (*sccd_hotplug_cb)(Daemon* d, const char* syspath, Subsystem sys, Vendor vendor, Product product);
typedef void (*sccd_usb_input_read_cb)(Daemon* d, USBDevHandle hndl, uint8_t endpoint, const uint8_t* data, void* userdata);

/** This is 'daemon from POV of driver', not everything that driver does */
struct Daemon {
	/**
	 * Registers new physical controller with daemon.
	 * Returns true on success. If false is returned (which should happen only
	 * when running out of memory), driver should deallocate everything related
	 * to Controller and forget about the device.
	 */
	bool			(*controller_add)(Controller* c);
	/**
	 * Informs daemon that controller has been removed (physically disconnected)
	 * and should not be used anymore.
	 * 
	 * Note that Controller object should NOT be deallocated until daemon calls
	 * it's deallocate method and its possible that daemon will make other
	 * requests even between controller_remove and deallocate calls.
	 * Driver has to handle this situation, preferably without crashing.
	 * On other hand, it's entirelly possible that deallocate will be called
	 * _from_ controller_remove method.
	 */
	void			(*controller_remove)(Controller* c);
	/**
	 * Adds callback that will be called periodically from Daemon's mainloop.
	 * There is no guarantee on how often callback will be called.
	 * Returns true on success or false on OOM error.
	 */
	bool			(*mainloop_cb_add)(sccd_mainloop_cb cb);
	/** Removes callback added by mainloop_cb_add. */
	void			(*mainloop_cb_remove)(sccd_mainloop_cb cb);
	/**
	 * Adds file descriptor that will be monitored for having data available to
	 * read and callback that will be called from Daemon's mainloop when that
	 * happens.
	 *
	 * Note that on Windows, select() from Winsock2 is used and polling works
	 * only with sockets.
	 *
	 * Returns true on success or false on OOM error.
	 */
	bool			(*poller_cb_add)(int fd, sccd_poller_cb cb, void* userdata);
	/**
	 * Adds callback that will be called when new device is detected.
	 * This is basically global shortcut to udev monitor.
	 *
	 * Returns true on success or false on OOM error. False is also returned if
	 * there already is another callback for same vendor and product ID registered.
	 */
	bool			(*hotplug_cb_add)(Subsystem sys, Vendor vendor, Product product, sccd_hotplug_cb cb);
	/**
	 * Registers error with daemon.
	 * Error (in this case) is simply string that will logged and sent to
	 * anything that requests list of errors.
	 *
	 * 'fatal' error is one that prevents emulation from working, for example
	 * uinput not being available. On other hand, not having access to physical
	 * controller device is not fatal, as other controller may be available.
	 * 
	 * Returns ID that can be used to remove error when it's resolved.
	 *
	 * Error may be silently ignored if there is no memory to store it.
	 * In such case, method returns -1. error_remove can handle -1 being passed
	 * as ID, so you can just ignore this possibility.
	 */
	intptr_t		(*error_add)(const char* message, bool fatal);
	/**
	 * Removes error added by error_add.
	 * Does nothing if ID is not valid.
	 */
	void			(*error_remove)(intptr_t id);
	/**
	 * Returns X11 display connection (casted to void*)
	 * On platforms where X11 is not used, or if connection to XServer failed
	 * before, returns NULL.
	 */
	void*			(*get_x_display)();
	/**
	 * Opens USB device represented by given syspath.
	 *
	 * Returns opaque pointer to something only libusb knows about,
	 * or NULL on failure.
	 * Doesn't work on Android (always returns NULL)
	 */
	USBDevHandle	(*usb_open)(const char* syspath);
	/** Closes given USBDevHandle */
	void			(*usb_close)(USBDevHandle hndl);
	/**
	 * Claims all interfaces matching specified parameters.
	 * Returns number of claimed interfaces, which will be zero in case of error.
	 */
	int				(*usb_claim_interfaces_by)(USBDevHandle hndl, int cls, int subclass, int protocol);
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
	bool			(*usb_interupt_read_loop)(USBDevHandle hndl, uint8_t endpoint, int length, sccd_usb_input_read_cb cb, void* userdata);
	/**
	 * Makes synchronous HID write on given USB device.
	 */
	void			(*usb_hid_write)(USBDevHandle hndl, uint16_t idx, uint8_t* data, uint16_t length);
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
	uint8_t*		(*usb_hid_request)(USBDevHandle hndl, uint16_t idx, uint8_t* data, int32_t length);
};

struct Driver {
	/**
	 * Called when daemon is exiting to give driver chance to deallocate things.
	 * May be NULL.
	 */
	void				(*unload)(struct Driver* drv, struct Daemon* d);
};

/** 
 * This function should be exported by driver; It will be called automatically
 * when daemon is starting.
 * It should return NULL to indicate on any failure.
 */
DLL_EXPORT Driver* scc_driver_init(Daemon* daemon);
typedef Driver*(*scc_driver_init_fn)(Daemon* daemon);

#ifdef __cplusplus
}
#endif
