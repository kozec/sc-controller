/**
 * SC Controller - client
 *
 * Tools for remote controling scc-daemon. SCCClient is what was (is) called
 * DaemonManager in python version.
 *
 * SCCClient is reference-counted. sccc_connect creates instance with single
 * reference and connection is automatically closed when last reference to
 * SCCClient is released.
 */

#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/utils/rc.h"
#include "scc/controller.h"
#include <stdbool.h>

#define SCCC_BUFFER_SIZE 10240
#define SCCC_MAX_ACTIVE_REQUESTS 32
typedef struct SCCClient SCCClient;

struct SCCClient {
	RC_HEADER;
	
	// All these are callbacks and none of them needs to be set.
	// Old 'alive' signal is not needed, if sccc_connect returns client, daemon is alive
	
	void*	userdata;
	
	/** Called after list of controllers (as reported by daemon) is updated */
	void (*on_controllers_changed)	(SCCClient* c, int controller_count);
	/**
	 * Called after connection to daemon is terminated. RC_REL should
	 * be used as response to this to deallocate SCCClient data.
	 */
	void (*on_disconnected)			(SCCClient* c);
	/**
	 * Called when event from locked or observed input is recieved.
	 * There is always only button or only pst is set, other value is zeroed.
	 */
	void (*on_event)				(SCCClient* c, uint32_t handle, SCButton button, PadStickTrigger pst, int values[]);
	/** Called when daemon reports profile change */
	void (*on_profile_changed)		(SCCClient* c, const char* profile_name);
	/** Called after daemon reports its version - usually right after connection is initiated */
	void (*on_version_recieved)		(SCCClient* c, const char* version);
	/** Called when daemon reports change in configuration file */
	void (*on_reconfigured)			(SCCClient* c);
	/**
	 * Called when "Ready" message is recieved, giving good signal to initiate
	 * communication with daemon.
	 */
	void (*on_ready)				(SCCClient* c);
};

/**
 * Connects to scc-daemon. Blocks until connection is initiated or fails.
 *
 * Returns SCCClient* with single reference.
 * Returns NULL and logs error if connection cannot be initiated.
 */
SCCClient* sccc_connect();

/**
 * Attempts to retrieve single message from socket. This function will call
 * recv() and so it will block until at least part of message is recieved.
 * Then, if message is recieved fully, this method will return that message
 * in buffer that will be changed next time method is called.
 * Do NOT deallocate this buffer.
 *
 * Many messages are handled internally, calling apropriate callbacks
 * in the process. For those messages, as well as when message is not
 * fully recieved in one recv operation, this method returns NULL.
 * That's why returning NULL is not meant as error.
 *
 * If socket is closed or other error occurs, returns empty string.
 */
const char* sccc_recieve(SCCClient* c);

/**
 * Returns handle of controller with given id or 0 if there is no such controller connected.
 * As special case, if id parameter is NULL, returns handle of first controller,
 * or 0 if there no controller at all.
 */
uint32_t sccc_get_controller_handle(SCCClient* c, const char* id);

/**
 * Returns controller ID of specified controller or NULL if handle is invalid.
 * Returned value should _not_ be deallocated by caller and will be available
 * at least until next call to 'sccc_recieve'.
 */
const char* sccc_get_controller_id(SCCClient* c, int handle);

/**
 * Locks physical button, axis or pad. Events from locked sources are
 * sent to this client and processed using 'event' callback until
 * unlock_all() is called.
 *
 * Calls sccc_request() and so it's subject to same blocking issue.
 *
 * Suceeds only if all sources are available. Returns true on success.
 */
#define sccc_lock(c, handle, ...) _sccc_lock(c, handle, __VA_ARGS__, NULL)
bool _sccc_lock(SCCClient* c, int handle, const char* src1, ...);


/**
 * Makes simple request that expects one of "Ok." or "Fail: something" as response.
 * There may be up to 32 requests sent at any given time (althought even two at
 * once should be unnecessary)
 *
 * Returns ID that should be used to retrieve response or -1 if request
 * cannot be sent. 0 is valid id im this case.
 * Note that sending request _without_ retrieving response will lead to
 * filling request buffer and eventually end up with requests failing.
 */
int32_t sccc_request(SCCClient* c, const char* request);

/**
 * Retrieves response assotiated with given request ID.
 * This will most likely involve calling sccc_recieve() and other callbacks
 * from whitin this call and will block until response is retrieved, connection
 * to daemon terminated or timeout reached.
 *
 * Returns string that has to be deallocated by caller on success.
 * Returns NULL on failure.
 */
char* sccc_get_response(SCCClient* c, int32_t id);

/** Returns file descriptor assotiated with client */
int sccc_get_fd(SCCClient* c);


/**
 * Creates Slave Mapper. Slave Mapper can take inputs from actual controller
 * connected to daemon (through input locking) and interpret them as necessary.
 *
 * Returns NULL on failure.
 */
Mapper* sccc_create_slave_mapper(SCCClient* c);

// TODO: Deallocator for this

/** Returns true if message startws with "OK." */
#define sccc_is_ok(x) ((x != NULL) && ((x)[0] == 'O') && ((x)[1] == 'K') && ((x)[2] == '.'))


// Following method(s) are available only if <glib.h> is included before this file
#ifdef __G_LIB_H__

/**
 * Converts SCCClient to GSource and adds source to main loop.
 * Use g_source_set_callback to recieve events.
 */
GSource* scc_gio_client_to_gsource(SCCClient* c);

#endif


#ifdef __cplusplus
}
#endif
