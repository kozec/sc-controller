/*
 * SC Controller - Daemon - internal definitions
 */
#pragma once

#include "scc/utils/strbuilder.h"
#include "scc/utils/list.h"
#include "scc/input_test.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include <sys/time.h>
#include <stdbool.h>
#include "version.h"
#ifdef _WIN32
#include "scc/input_device.h"
#endif

#define MIN_SLEEP_TIME 10 /** ms */
#define CLIENT_BUFFER_SIZE 10240
#define SCCD_OOM ((void*)-1) /* used as possible return value in some cases */

typedef struct SCCDMapper SCCDMapper;

typedef struct Client {
	int				fd;
	Mapper*			mapper;		// Mapper (controller) assigned by client
	char*			tag;		// last tag sent by client or NULL
	bool			should_be_dropped;
	char			buffer[CLIENT_BUFFER_SIZE + 1];
	char*			next;		// as in 'place in buffer I'll write next time'
} Client;

typedef struct ErrorData {
	uint16_t		id;
	char*			message;
	bool			fatal;
} ErrorData;

enum SpecialClientType {
	SCT_OSD,
	SCT_AUTOSWITCH
};

typedef LIST_TYPE(ErrorData) ErrorList;
typedef LIST_TYPE(Controller) ControllerList;

typedef void (*sccd_scheduler_cb_internal)(void* parent, void* userdata);

int sccd_start();
void sccd_set_proctitle(const char* name);
void sccd_set_default_profile(const char* profile);
void sccd_exit();

intptr_t sccd_error_add(const char* message, bool fatal);
void sccd_error_remove(intptr_t id);
ErrorList sccd_get_errors();
/** Returns true on success */
bool sccd_set_profile(Mapper* m, const char* filename);
/**
 * Returns filename of 'main' profile, one that's loaded on 1st controller
 * or just held in memory waiting for controller to be connected.
 */
const char* sccd_get_current_profile();

void sccd_logger_init(bool log_to_stdout);
/** Returns entire log as one giant string */
const char* sccd_logger_get_log();
/**
 * Adds client to list of clients that are getting log messages.
 * Returns false if memory cannot be allocated.
 */
bool sccd_logger_client_add(Client* c);
void sccd_logger_client_remove(Client* c);

void sccd_poller_init();
bool sccd_poller_add(int fd, sccd_poller_cb cb, void* userdata);
void sccd_poller_remove(int fd);
void sccd_poller_close();

void sccd_scheduler_init();
void sccd_scheduler_close();
/**
 * Schedules function to be called in 'timeout' ms.
 * May return 0 if allocation fails.
 */
TaskID sccd_scheduler_schedule(uint32_t timeout, sccd_scheduler_cb_internal cb, void* parent, void* userdata);
/** Cancels task with given ID. Does nothing if ID is not valid */
void sccd_scheduler_cancel(TaskID id);
/** Returns NULL if there is no such task scheduled */
void* sccd_scheduler_get_user_data(TaskID id);
/**
 * Sets to 't' time that daemon can safelly sleep without delaying
 * any pending tasks. Sets 't' to MIN_SLEEP_TIME if there is no task pending
 */
void sccd_scheduler_get_sleep_time(struct timeval* t);

/** Returns false on failure */
bool sccd_socket_init();
/**
 * Sends string to client. There is no newline appended, so to
 * conform to protocol, caller should be adding one.
 *
 * If str is NULL, assumes allocation failure, logs error and marks client
 * for dropping.
 * If client already is marked for dropping, doesn't send anything.
 */
void sccd_socket_send(Client* client, const char* str);
/** As sccd_socket_send, but also deallocates string */
void sccd_socket_consume(Client* client, char* str);
/** Sends message to all connected clients */
void sccd_socket_send_to_all(const char* str);
void sccd_clients_for_all(void (*cb)(Client* c));
void sccd_on_client_command(Client* client, char* buffer, size_t len);
void sccd_send_controller_list(Client* client);
void sccd_send_profile_list(Client* client);
/**
 * Schedules client to be dropped. This is better than dropping it immediatelly,
 * as code can still send messages to such client (but they will be
 * redirected to /dev/null) without having to consider possibility that related
 * memory is already deallocated.
 */
void sccd_drop_client_asap(Client* client);

/** Starts CemuHookUDP motion provider server */
bool sccd_cemuhook_socket_enable();
/** Stores and/or sends rotation data to clients */
bool sccd_cemuhook_feed(int index, float data[6]);

/** Initializes connection to X11 display. On Windows, does nothing */
void sccd_x11_init();
void sccd_x11_close();
/**
 * Returns open connection to X11 display.
 * Returns NULL on Windows, Android, or on *nix if connection to display failed
 */
void* sccd_x11_get_display();

void sccd_device_monitor_init();
void sccd_device_monitor_common_init();
void sccd_device_monitor_start();
void sccd_device_monitor_rescan();
void sccd_device_monitor_close();
void sccd_device_monitor_close_common();
bool sccd_register_hotplug_cb(Subsystem sys, sccd_hotplug_cb cb, const HotplugFilter* filters, ...);

#ifdef __BSD__
InputDevice* sccd_input_bsd_open(const char* syspath);
void sccd_input_bsd_init();
void sccd_input_bsd_close();
#else
InputDevice* sccd_input_libusb_open(const char* syspath);
void sccd_input_libusb_init();
void sccd_input_libusb_close();
#endif
#ifdef USE_HIDAPI
InputDevice* sccd_input_hidapi_open(const char* syspath);
void sccd_input_hidapi_rescan();
void sccd_input_hidapi_close();
void sccd_input_hidapi_init();
#endif
#ifdef USE_DINPUT
InputDevice* sccd_input_dinput_open(const InputDeviceData* idev);
void sccd_input_dinput_rescan();
void sccd_input_dinput_close();
void sccd_input_dinput_init();
#endif
void sccd_device_monitor_new_device(Daemon* d, const InputDeviceData* idata);
void sccd_device_monitor_device_removed(Daemon* d, const char* path);
/** Returns true if filter matches device */
bool sccd_device_monitor_test_filter(Daemon* d, const InputDeviceData* data, const HotplugFilter* filter);
/**
 * Returns bit mask of enabled subsystems; Subsystem is enabled
 * (and bit is set to 1) if there is any callback registered for it*/
uint32_t sccd_device_monitor_get_enabled_subsystems(Daemon* d);
#ifdef _WIN32
struct Win32InputDeviceData {
	InputDeviceData		idev;
	Vendor				vendor;
	Product				product;
	uint8_t				bus;
	uint8_t				dev;
	int					idx;
	void*				d8dev;
};
void sccd_device_monitor_win32_fill_struct(struct Win32InputDeviceData* wdev);
void sccd_input_libusb_rescan();
#endif

Client* sccd_get_special_client(enum SpecialClientType t);
/** If another client is already registered, it's dropped */
void sccd_set_special_client(enum SpecialClientType t, Client* client);

enum DirverInitMode {
	/** Used by daemon */
	DIMODE_ALL =					1,
	/**
	 * Used by scc-input-tester to initialize only dirvers with
	 * 'list_devices' method.
	 */
	DIMODE_LIST_DEVICES_ONLY =		2
};

/** Loads and initializes all available drivers */
void sccd_drivers_init(Daemon* daemon, enum DirverInitMode mode);
/** Asks input drivers to list available devices. Used by input_tester */
void sccd_drivers_list_devices(Daemon* daemon, const controller_available_cb cb);
/** Returns driver with given name or NULL if there is no such loaded */
Driver* sccd_drivers_get_by_name(const char* driver_name);

ControllerList sccd_get_controller_list();
Controller* sccd_get_controller_by_id(const char* id);

/**
 * Returns NULL on success or source that was not available for locking
 * Additionally, may return SCCD_OOM in case of OOM error.
 */
const char* sccd_lock_actions(Client* c, StringList sources);
/** Unlocks all locked actions */
void sccd_unlock_actions(Client* c);
/**
 * When there are some actions locked on particular mapper, profile assigned
 * to that mapper is wrapped in LockProfile. To prevent removing this wrapper
 * by accident, 'sccd_is_locked_profile' can be used to detect it and
 * this method changes wrapped profile without touching wrapping LockProfile
 */
void sccd_change_locked_profile(Profile* p, Profile* child);
/** Returns true if passed profile is instance of LockProfile */
bool sccd_is_locked_profile(Profile* p);

/** Returns NULL on failure */
SCCDMapper* sccd_mapper_create();
Mapper* sccd_mapper_to_mapper(SCCDMapper* m);
/** Returns NULL if mapper is not SCCDMapper */
SCCDMapper* sccd_mapper_to_sccd_mapper(Mapper* m);
SCCDMapper* sccd_get_default_mapper();
void sccd_mapper_deallocate(SCCDMapper* m);
void sccd_mapper_flush(SCCDMapper* m);
/** Returns false if allocation fails */
bool sccd_mapper_set_profile_filename(SCCDMapper* m, const char* filename);
/** Returns NULL if no filename was set */
const char* sccd_mapper_get_profile_filename(SCCDMapper* m);

/**
 * Returns NULL if mapper for controller cannot be determined; Returns None
 * if mapper has no profile assigned.
 */
const char* get_profile_for_controller(Controller* c);

/**
 * Used to read and decode Vendor a Product id from /sys/.../idVendor and idProduct
 * Also used by usb_helper to read devnum and busnum numbers.
 *
 * Returns -1 on failure.
 */
long int read_long_from_file(const char* filename, int base);

/** For internal use only */
Daemon* get_daemon();
