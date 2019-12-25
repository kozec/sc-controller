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
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#ifdef _WIN32
	#include "scc/utils/msys_socket.h"
	#define SOCKETERROR ": error %i", WSAGetLastError()
	#define connect msys_connect
	#define socket msys_socket
	#define close msys_close
	#define bind msys_bind
#else
	#define SOCKETERROR  ": %s", strerror(errno)
	#include <sys/socket.h>
	#include <sys/un.h>
#endif
#include "scc/client.h"
#include "scc/tools.h"
#include "client.h"
#include <unistd.h>
#include <string.h>
#include <errno.h>

static const char* RQ_TAGS = "123456789abcdefghijklmnopqrstuvw";
#define RQ_OCCUPIED ((char*)(void*)1)

/** Connects to scc-daemon. Returns NULL if connection cannot be initiated */
SCCClient* sccc_connect() {
	struct _SCCClient* c = malloc(sizeof(struct _SCCClient));
	ControllerList controllers = list_new(ControllerData, 16);
	ASSERT(strlen(RQ_TAGS) == SCCC_MAX_ACTIVE_REQUESTS);
	if ((c == NULL) || (controllers == NULL)) {
		LOG("Failed to allocate client: Out of memory");
		list_free(controllers);
		free(c);
		return NULL;
	}
	
	struct sockaddr_un addr;
	memset(&addr, 0, sizeof(addr));
	memset(c, 0, sizeof(struct _SCCClient));
	RC_INIT(&c->client, &sccc_dealloc);
	list_set_dealloc_cb(controllers, &free);
	c->next = c->buffer;
	c->controllers = controllers;
	c->fd = -1;
	*c->buffer = 0;
	addr.sun_family = AF_UNIX;
	strcpy(addr.sun_path, scc_get_daemon_socket());
	DDEBUG("Connecting to '%s'...", addr.sun_path);
	
	c->fd = socket(PF_UNIX, SOCK_STREAM, 0);
#ifdef _WIN32
	if ((c->fd < 0) && (WSAGetLastError() == WSANOTINITIALISED)) {
		WSADATA wsaData;
		int err = WSAStartup(MAKEWORD(2, 2), &wsaData);
		if (err != 0) {
			LERROR("Failed to initialize Winsock2: error %i", err);
			goto sccc_connect_fail;
		}
		c->fd = socket(PF_UNIX, SOCK_STREAM, 0);
	}
#endif
	
	if (c->fd < 0) {
		LERROR("Failed to open socket" SOCKETERROR);
		goto sccc_connect_fail;
	}
	
	if (connect(c->fd, (struct sockaddr*)&addr, sizeof(addr)) == -1) {
		LERROR("Connection failed" SOCKETERROR);
		goto sccc_connect_fail;
	}
	
	return &c->client;
	
sccc_connect_fail:
	RC_REL(&c->client);
	return NULL;
}

int sccc_get_fd(SCCClient* _c) {
	struct _SCCClient* c = container_of(_c, struct _SCCClient, client);
	return c->fd;
}

void sccc_dealloc(void* _c) {
	struct _SCCClient* c = container_of(_c, struct _SCCClient, client);
	if (c->fd >= 0)
		close(c->fd);
	list_free(c->controllers);
	free(c);
}

const char* sccc_recieve(SCCClient* _c) {
	struct _SCCClient* c = container_of(_c, struct _SCCClient, client);
	// Recieve as many bytes as possible
	size_t free_space = SCCC_BUFFER_SIZE - (size_t)(c->next - c->buffer);
	if (free_space < 1) {
		// Our messages are very short, so if so many bytes are recieved
		// without newline, it's safe to assume something went very, very wrong.
		// Bail out in such case.
		LERROR("Buffer overrun. Closing connection");
		goto sccc_recieve_fail;
	}
	ssize_t r = recv(c->fd, c->next, free_space, MSG_PEEK);
	if (r < 0) {
#ifdef _WIN32
		if (WSAGetLastError() == WSAEWOULDBLOCK) {
			// No data queued
			return NULL;
		}
		LERROR("Error %i; Closing connection", WSAGetLastError());
#else
		LERROR("%s; Closing connection", strerror(errno));
#endif
		goto sccc_recieve_fail;
	}
	*(c->next + r) = 0;
	char* pos = strchr(c->buffer, '\n');
	// If \n is found, we got at least one message
	if (pos != NULL) {
		// empty recv buffer up to newline
		recv(c->fd, c->next, (size_t)(pos - c->next + 1), 0);
		*pos = 0;
		c->next = c->buffer;
		int parsed = on_command(c, c->buffer);
		if (parsed == 1)
			// handled
			return NULL;
		else if (parsed < 0)
			// OOM in on_command
			goto sccc_recieve_fail;
		else
			// Unknown message
			return c->buffer;
	} else if (r == 0) {
		// Connection was closed and we don't have any message left in buffer
		c->buffer[0] = 0;
		return c->buffer;
	} else {
		// empty recv buffer completly
		recv(c->fd, c->next, r, 0);
		c->next += r;
		return NULL;
	}
	
sccc_recieve_fail:
	close(c->fd);
	c->buffer[0] = 0;
	if (_c->callbacks.on_disconnected != NULL)
		_c->callbacks.on_disconnected(_c);
	return c->buffer;
}

void store_response(struct _SCCClient* c, const char* tag, const char* response) {
	char* index = strchr(RQ_TAGS, tag[1]);
	if ((index == NULL) || ((size_t)(index - RQ_TAGS) >= SCCC_MAX_ACTIVE_REQUESTS)
			|| (c->responses[index - RQ_TAGS] != RQ_OCCUPIED)) {
		LERROR("Recieved response with invalid tag: '%s'", tag);
		close(c->fd);
		return;
	}
	c->responses[index - RQ_TAGS] = strbuilder_cpy(response);
	if (c->responses[index - RQ_TAGS] == NULL) {
		LERROR("OOM while storing response");
		close(c->fd);
		return;
	}
}

int32_t sccc_request(SCCClient* _c, const char* request) {
	struct _SCCClient* c = container_of(_c, struct _SCCClient, client);
	int32_t id = -1;
	for (int32_t i=0; (id == -1) && (i<SCCC_MAX_ACTIVE_REQUESTS); i++) {
		if (c->responses[c->next_request_id] == NULL)
			id = c->next_request_id;
		c->next_request_id ++;
		if (c->next_request_id >= SCCC_MAX_ACTIVE_REQUESTS)
			c->next_request_id = 0;
		if (id >= 0)
			break;
	}
	if (id < 0) {
		LERROR("Too many active requests, are you calling 'sccc_get_response' properly?");
		return -1;
	}
	
	char tag[3] = "#? ";
	tag[1] = RQ_TAGS[id];
	if ((send(c->fd, tag, 3, 0) < 0) || (send(c->fd, request, strlen(request), 0) < 0) || (send(c->fd, "\n", 1, 0) < 0)) {
		LERROR("%s; Closing connection", strerror(errno));
		close(c->fd);
		return -1;
	}
	
	c->responses[id] = RQ_OCCUPIED;
	return id;
}

char* sccc_get_response(SCCClient* _c, int32_t id) {
	struct _SCCClient* c = container_of(_c, struct _SCCClient, client);
	ASSERT(id < SCCC_MAX_ACTIVE_REQUESTS);
	if (id < 0)
		return NULL;
	while (1) {
		char* response = c->responses[id];
		if (response == RQ_OCCUPIED) {
			// Still waiting
			const char* buffer = sccc_recieve(&c->client);
			if ((buffer != NULL) && (buffer[0] == 0)) {
				LERROR("sccc_get_response: connection closed");
				return NULL;
			}
		} else if (response == NULL) {
			LERROR("sccc_get_response: response already retrieved or never asked for");
			return NULL;
		} else {
			// Got response
			c->responses[id] = NULL;
			return response;
		}
	}
}

void sccc_unref(SCCClient* c) {
	RC_REL(c);
}

