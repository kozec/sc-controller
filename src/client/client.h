#pragma once
#include "scc/utils/tokenizer.h"
#include "scc/utils/list.h"
#include "scc/controller.h"
#include "scc/client.h"
#include <stdint.h>

typedef struct ControllerData {
	uint32_t			handle;
	char*				id;
	char*				type;
	ControllerFlags		flags;
	char*				config_file;
	bool				alive;
} ControllerData;

typedef LIST_TYPE(ControllerData) ControllerList;

struct _SCCClient {
	SCCClient			client;
	int					fd;
	ControllerList		controllers;
	char*				responses[SCCC_MAX_ACTIVE_REQUESTS];
	uint8_t				next_request_id;
	char				buffer[SCCC_BUFFER_SIZE];
	char*				next;
};

void sccc_dealloc(void* c);

/** Returns 1 if message was parsed and handled, -1 on OOM error */
int on_command(struct _SCCClient* c, char* msg);

/** Returns ControllerData or allocates new. Returns NULL on OOM error */
ControllerData* get_data_by_id(struct _SCCClient* c, const char* id);

/** Returns ControllerData or NULL if handle is not valid */
ControllerData* get_data_by_handle(struct _SCCClient* c, int handle);

void controller_data_free(ControllerData* cd);

void store_response(struct _SCCClient* c, const char* tag, const char* response);

void on_controller_event(struct _SCCClient* c, const char* controller, Tokens* tokens);

/** Sends "Controller: XY" request to daemon. Returns False if anything (OOM, invalid handle) fails */
bool request_controller(struct _SCCClient* c, int handle);

/** Removes and deallocates ControllerData* for every non 'alive' controller */
void remove_nonalive(ControllerList lst);

/** Marks controller not 'alive' */
void mark_non_alive_foreach_cb(void* item);

