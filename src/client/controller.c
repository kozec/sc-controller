/**
 * SC-Controller - Client - Socket
 * 
 * Code here handles clients connecting to scc-daemon using unix socket.
 */

#define LOG_TAG "SCCC"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/list.h"
#include "scc/client.h"
#include "scc/tools.h"
#include "client.h"

#ifdef _WIN32
	#include <winsock.h>
#else
	#include <sys/socket.h>
	#include <sys/un.h>
#endif
#include <unistd.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>


ControllerData* get_data_by_id(struct _SCCClient* c, const char* id) {
	ListIterator it = iter_get(c->controllers);
	if (it == NULL) return NULL;
	uint32_t next_free_handle = 1;
	FOREACH(ControllerData*, cd, it) {
		if (strcmp(cd->id, id) == 0) {
			// Got one
			iter_free(it);
			return cd;
		}
		if (cd->handle >= next_free_handle)
			next_free_handle = cd->handle + 1;
	}
	// Nothing found
	iter_free(it);
	if (!list_allocate(c->controllers, 1)) return NULL;
	ControllerData* cd = malloc(sizeof(ControllerData));
	char* id_copy = strbuilder_cpy(id);
	if ((cd == NULL) || (id_copy == NULL)) {
		free(cd);
		free(id_copy);
		return NULL;
	}
	memset(cd, 0, sizeof(ControllerData));
	list_add(c->controllers, cd);
	cd->handle = next_free_handle;
	cd->id = id_copy;
	return cd;
}

ControllerData* get_data_by_handle(struct _SCCClient* c, int handle) {
	// Not using Iterator here to avoid need to allocate it
	FOREACH_IN(ControllerData*, cd, c->controllers)
		if (cd->handle == handle)
			return cd;
	return NULL;
}

void on_controller_event(struct _SCCClient* c, const char* controller, Tokens* tokens) {
	uint32_t handle = sccc_get_controller_handle(&c->client, controller);
	if (handle != 0) {
		const char* what = iter_next(tokens);
		SCButton b = scc_string_to_button(what);
		PadStickTrigger pst = 0;
		if (b != 0) {
			const char* value = iter_next(tokens);
			int values[] = { (value[0] == '1') ? 1 : 0 };
			c->client.callbacks.on_event(&c->client, handle, b, 0, values);
		}
		if (b == 0)
			pst = scc_string_to_pst(what);
		if (pst != 0) {
			const char* x = iter_next(tokens);
			const char* y = iter_next(tokens);
			int values[] = {
				strtol(x, NULL, 10),
				strtol(y, NULL, 10),
			};
			c->client.callbacks.on_event(&c->client, handle, 0, pst, values);
		}
	}
	tokens_free(tokens);
}

bool request_controller(struct _SCCClient* c, int handle) {
	ControllerData* cd = get_data_by_handle(c, handle);
	if ((cd == NULL) || (cd->id == NULL)) return false;
	char* buffer = strbuilder_fmt("Controller: %s", cd->id);
	if (buffer == NULL) return false;
	int32_t id = sccc_request(&c->client, buffer);
	free(buffer);
	buffer = sccc_get_response(&c->client, id);
	if (sccc_is_ok(buffer)) {
		free(buffer);
		return true;
	} else {
		free(buffer);
		return false;
	}
}

bool _sccc_lock(SCCClient* _c, int handle, const char* src1, ...) {
	va_list args;
	struct _SCCClient* c = container_of(_c, struct _SCCClient, client);
	if (!request_controller(c, handle)) return false;
	if (src1 == NULL)
		// Sucesfully locked nothing
		return true;
	
	StrBuilder* sb = strbuilder_new();
	if (sb == NULL) return false;	// OOM
	strbuilder_add(sb, "Lock:");
	va_start(args, src1);
	const char* arg = src1;
	while (arg != NULL) {
		strbuilder_add(sb, " ");
		strbuilder_add(sb, arg);
		arg = va_arg(args, const char*);
	}
	va_end(args);
	if (strbuilder_failed(sb)) {
		strbuilder_free(sb);
		return false;
	}
	
	char* buffer = strbuilder_consume(sb);
	if (buffer == NULL) return false;
	int32_t id = sccc_request(&c->client, buffer);
	free(buffer);
	if (id < 0) return false;
	buffer = sccc_get_response(&c->client, id);
	bool rv = sccc_is_ok(buffer);
	free(buffer);
	return rv;
}

uint32_t sccc_get_controller_handle(SCCClient* _c, const char* id) {
	struct _SCCClient* c = container_of(_c, struct _SCCClient, client);
	// Not using Iterator here to avoid need to allocate it
	if (id == NULL) {
		if (list_len(c->controllers) > 0)
			return c->controllers->items[0]->handle;
	} else {
		FOREACH_IN(ControllerData*, cd, c->controllers) {
			if (strcmp(cd->id, id) == 0) {
				// Got one
				return cd->handle;
			}
		}
	}
	return 0;
}

bool sccc_unlock_all(SCCClient* _c) {
	struct _SCCClient* c = container_of(_c, struct _SCCClient, client);
	int32_t id = sccc_request(&c->client, "Unlock.");
	char* buffer = sccc_get_response(&c->client, id);
	if (sccc_is_ok(buffer)) {
		free(buffer);
		return true;
	}
	free(buffer);
	return false;
}

const char* sccc_get_controller_id(SCCClient* _c, int handle) {
	struct _SCCClient* c = container_of(_c, struct _SCCClient, client);
	ControllerData* cd = get_data_by_handle(c, handle);
	return cd->id;
}

void controller_data_free(ControllerData* cd) {
	if (cd->id != NULL) free(cd->id);
	if (cd->type != NULL) free(cd->type);
	if (cd->config_file != NULL) free(cd->config_file);
	free(cd);
}

static bool nonalive_controllers_filter_fn(void* item, void* userdata) {
	ControllerData* cd = (ControllerData*)item;
	if (cd->alive)
		return true;
	
	controller_data_free(cd);
	return false;
}

/** Removes and deallocates ControllerData* for every non 'alive' controller */
void remove_nonalive(ControllerList lst) {
	list_filter(lst, &nonalive_controllers_filter_fn, NULL);
}

void mark_non_alive_foreach_cb(void* item) {
	ControllerData* cd = (ControllerData*)item;
	cd->alive = false;
}
