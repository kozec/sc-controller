/**
 * Should anyone ever feel need to implement additional 'driver' into SC-Controller,
 * this should be only header he needs to import.
 */

#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/utils/dll_export.h"
#include "scc/controller.h"
#include <stdbool.h>
#include <stdint.h>
struct Daemon;

typedef unsigned short Vendor;
typedef unsigned short Product;
typedef uintptr_t TaskID;
typedef enum {
	USB			= 0,
#ifdef __linux__
	BT			= 1,
	EVDEV		= 2,
#endif
#ifdef __BSD__
	UHID		= 3,
#else
	HIDAPI		= 4,
#endif
#ifdef _WIN32
	DINPUT		= 5,
#endif
} Subsystem;

typedef struct Daemon Daemon;
typedef struct Driver Driver;
typedef struct InputDevice InputDevice;
typedef struct InputDeviceData InputDeviceData;
typedef struct HotplugFilter HotplugFilter;
typedef struct InputTestMethods InputTestMethods;

typedef void (*sccd_mainloop_cb)(Daemon* d);
typedef void (*sccd_poller_cb)(Daemon* d, int fd, void* userdata);
typedef bool (*sccd_hotplug_cb)(Daemon* d, const InputDeviceData* idata);
typedef void (*sccd_scheduler_cb)(void* userdata);


/** This is 'daemon from POV of driver', not everything that daemon does */
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
	 * Schedules function to be called after given delay.
	 *
	 * Callback will be called from main loop and unlike with mapper, it's
	 * guaranteed that this callback will be eventually called,
	 * assuming entire daemon doesn't crash before.
	 *
	 * 'delay' is in milliseconds. It can be zero, in which case callback will be called ASAP.
	 * Returns id that can be used to cancel scheduled call later
	 * or 0 if allocation fails.
	 */
	TaskID			(*schedule)(uint32_t timeout, sccd_scheduler_cb cb, void* userdata);
	/**
	 * Cancels callback scheduled by 'schedule' method.
	 * If id is not valid, does nothing.
	 */
	void			(*cancel)(TaskID task_id);
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
	 * InputDeviceData object passed to callback will be valid only durring
	 * that callback. Use it's copy() method if you need to keep it longer.
	 *
	 * This is basically global shortcut to udev monitor.
	 *
	 * 'filters' is NULL terminated vararg list used to filter matching devices.
	 * Callback is called only if device matches all the filters.
	 * Callback should return true to signalize device was handled sucesfully.
	 * If it does so, callback will not be called for same device again
	 * unless it is disconnected and reconnected back.
	 *
	 * Returns true on success or false on OOM error. False is also returned if
	 * there already is another callback for same vendor and product ID registered.
	 */
	bool			(*hotplug_cb_add)(Subsystem sys, sccd_hotplug_cb callback, const HotplugFilter* filters, ...);
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
	 * Returns controller with given ID or NULL if such controler is not found.
	 * Note that returned value may be deallocated by daemon at any time and so
	 * it shouldn't be kept by caller.
	 */
	Controller*		(*get_controller_by_id)(const char* id);
	/**
	 * Returns X11 display connection (casted to void*)
	 * On platforms where X11 is not used, or if connection to XServer failed
	 * before, returns NULL.
	 */
	void*			(*get_x_display)();
	/**
	 * Returns configuration directory, that is ~/.config/scc under normal conditions.
	 * Returned value is cached internally and should NOT be free'd by caller.
	 */
	const char*		(*get_config_path)();
	/**
	 * Returns true if hidapi support was enabled at compile time
	 */
	bool			(*get_hidapi_enabled)();
};


struct Driver {
	/**
	 * Called when daemon is exiting to give driver chance to deallocate things.
	 * May be NULL.
	 */
	void				(*unload)(Driver* drv, Daemon* d);
	/**
	 * Called after daemon is completly initialized (unless set to NULL).
	 * It's good idea to register hotplug callbacks from here.
	 *
	 * Returns false to indicate any failure. Library may be unloaded in such case.
	 * This method is not called from scc-input-tester.
	 * May be NULL.
	 */
	bool				(*start)(Driver* drv, Daemon* d);
	/**
	 * Methods used by `scc-input-tester`. See 'input_test.h' to more details.
	 * May (and most likely will be) NULL.
	 */
	InputTestMethods*	input_test;
};


typedef struct HotplugFilter {
	enum {
		SCCD_HOTPLUG_FILTER_VENDOR			= 1,
		SCCD_HOTPLUG_FILTER_PRODUCT			= 2,
#ifdef __linux__
		/** vendor:product ids as string (format that lsusb uses) */
		SCCD_HOTPLUG_FILTER_VIDPID			= 3,
#endif
		/** device path. Emulated on Windows. Useful mostly for input tester */
		SCCD_HOTPLUG_FILTER_PATH			= 4,
		/** evdev or dinput name. Not always available */
		SCCD_HOTPLUG_FILTER_NAME			= 5,
		/** interface number. Not always available */
		SCCD_HOTPLUG_FILTER_IDX				= 6,
		/**
		 * guidInstance on Windows, 'device/uniq' on Linux, or similar.
		 * May fallback to "vendor:product" format.
		 */
		SCCD_HOTPLUG_FILTER_UNIQUE_ID		= 7,
	}					type;
	union {
		Vendor			vendor;
		Product			product;
		const char*		name;
		const char*		path;
		const char*		vidpid;
		const char*		id;
		int				idx;
	};
} HotplugFilter;


/**
 * This function has to be exported by driver; It will be called automatically
 * when daemon is starting.
 *
 * Returns NULL to indicate any failure.
 */
DLL_EXPORT Driver* scc_driver_init(Daemon* daemon);
typedef Driver*(*scc_driver_init_fn)(Daemon* daemon);


#ifdef __cplusplus
}
#endif

