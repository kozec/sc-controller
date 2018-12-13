/*
 * SC Controller - Daemon - internal definitions
 */
#pragma once

#define DAEMON_VERSION "0.4.5"
#include "scc/utils/strbuilder.h"
#include "scc/utils/list.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include <sys/time.h>
#include <stdbool.h>

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
typedef uintptr_t TaskID;

intptr_t sccd_error_add(const char* message, bool fatal);
void sccd_error_remove(intptr_t id);
ErrorList sccd_get_errors();
/** Returns true on success */
bool sccd_set_profile(Mapper* m, const char* filename);

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
void sccd_on_client_command(Client* client, char* buffer, size_t len);
void sccd_send_controller_list(Client* client);
/**
 * Schedules client to be dropped. This is better than dropping it immediatelly,
 * as code can still send messages to such client (but they will be
 * redirected to /dev/null) without having to consider possibility that related
 * memory is already deallocated.
 */
void sccd_drop_client_asap(Client* client);

/** Initializes connection to X11 display. On Windows, does nothing */
void sccd_x11_init();
void sccd_x11_close();
/**
 * Returns open connection to X11 display.
 * Returns NULL on Windows, Android, or on *nix if connection to display failed
 */
void* sccd_x11_get_display();

void sccd_usb_helper_init();
void sccd_usb_helper_close();
USBHelper* sccd_get_usb_helper();

void sccd_device_monitor_init();
void sccd_device_monitor_start();
void sccd_device_monitor_rescan();
void sccd_device_monitor_close();
bool sccd_register_hotplug_cb(Subsystem sys, Vendor vendor, Product product, sccd_hotplug_cb cb);

Client* sccd_get_special_client(enum SpecialClientType t);
/** If another client is already registered, it's dropped */
void sccd_set_special_client(enum SpecialClientType t, Client* client);

void sccd_drivers_init();

ControllerList sccd_get_controller_list();

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
SCCDMapper* sccd_get_default_mapper();
void sccd_mapper_deallocate(SCCDMapper* m);
void sccd_mapper_flush(SCCDMapper* m);

/** 
 * Used to read and decode Vendor a Product id from /sys/.../idVendor and idProduct
 * Also used by usb_helper to read devnum and busnum numbers.
 * 
 * Returns -1 on failure.
 */
long int read_long_from_file(const char* filename, int base);

/** For internal use only */
Daemon* get_daemon();
