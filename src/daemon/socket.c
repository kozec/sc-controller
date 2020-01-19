/**
 * SC-Controller - Daemon - Socket
 *
 * Code here handles scc-daemon use of unix or windows socket. On Windows,
 * implementation compatible with mingw's 'fake unix socket' is used.
 *
 * Only interesting thing is that any issue with allocation, buffer overflow,
 * or other unexpected stuff is handled simply by dropping client.
 */

#define LOG_TAG "Daemon"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#ifdef _WIN32
	#include "scc/utils/msys_socket.h"
	#include "scc/tools.h"
	#define SOCKETERROR ": error %i", WSAGetLastError()
	#define socket msys_socket
	#define accept msys_accept
	#define close msys_close
	#define bind msys_bind
#else
	#include "scc/tools.h"
	#include <sys/socket.h>
	#include <sys/stat.h>
	#include <sys/un.h>
	#define SOCKETERROR  ": %s", strerror(errno)
#endif
#include "daemon.h"
#include <sys/types.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>

static LIST_TYPE(Client) clients;
static int sock;


void sccd_drop_client_asap(Client* client) {
	client->should_be_dropped = true;
}

static void drop(Client* client) {
	sccd_unlock_actions(client);		// Just to be sure nothing remains locked
	close(client->fd);
	sccd_poller_remove(client->fd);
	list_remove(clients, client);
	if (client == sccd_get_special_client(SCT_OSD)) {
		sccd_set_special_client(SCT_OSD, NULL);
		INFO("scc-osd-daemon lost");
	}
	if (client == sccd_get_special_client(SCT_AUTOSWITCH)) {
		sccd_set_special_client(SCT_AUTOSWITCH, NULL);
		INFO("scc-autoswitch-daemon lost");
	}
	sccd_logger_client_remove(client);

	if (client->tag != NULL)
		free(client->tag);
	free(client);
}

static void on_client_socket_data(Daemon* d, int fd, void* _client) {
	Client* client = (Client*)_client;
	size_t free_space = CLIENT_BUFFER_SIZE - (client->next - client->buffer);
	if (client->should_be_dropped)
		return drop(client);
	if (free_space < 1) {
		LERROR("Buffer overflow; dropping client");
		return drop(client);
	}
	ssize_t r = recv(fd, client->next, free_space, 0);
	if (r < 0) {
#ifndef _WIN32
		LERROR("%s; dropping client", strerror(errno));
#else
		LERROR("Error %i; dropping client", WSAGetLastError());
#endif
		return drop(client);
	} else if (r == 0) {
		DDEBUG("Client disconnected");
		return drop(client);
	}
	*(client->next + r) = 0;
	client->next += r;
	
	char* newline = strchr(client->buffer, '\n');
	while (newline != NULL) {
		*newline = 0;
		size_t len = newline - client->buffer;
		sccd_on_client_command(client, client->buffer, len);
		if (client->should_be_dropped) {
			drop(client);
		} else {
			memmove(client->buffer, newline + 1, CLIENT_BUFFER_SIZE + 1 - len);
			client->next -= len + 1;
		}
		newline = strchr(client->buffer, '\n');
	}
}

/** Returns true if any error was fatal */
static bool sccd_send_error_list(Client* client) {
	bool any_fatal_error = false;
	ListIterator it = iter_get(sccd_get_errors());
	FOREACH(ErrorData*, e, it) {
		sccd_socket_consume(client, strbuilder_fmt("Error: %s\n", e->message));
		any_fatal_error = any_fatal_error | e->fatal;
	}
	iter_free(it);

	return any_fatal_error;
}

void sccd_send_controller_list(Client* client) {
	ListIterator it = iter_get(sccd_get_controller_list());
	int count = 0;
	FOREACH(Controller*, c, it) {
		count ++;
		sccd_socket_consume(client, strbuilder_fmt("Controller: %s %s %i\n",
			c->get_id(c),
			c->get_type(c),
			(int)c->flags
		));
	}
	iter_free(it);
	sccd_socket_consume(client, strbuilder_fmt("Controller Count: %i\n", count));
}

void sccd_send_profile_list(Client* client) {
	ControllerList lst = sccd_get_controller_list();
	FOREACH_IN(Controller*, c, lst) {
		const char* filename = get_profile_for_controller(c);
		if (filename != NULL)
			sccd_socket_consume(client, strbuilder_fmt(
				"Controller profile: %s %s\n", c->get_id(c), filename));
	}
	sccd_socket_consume(client, strbuilder_fmt("Current profile: %s\n", sccd_get_current_profile()));
}

void sccd_socket_send(Client* client, const char* str) {
	if (client->should_be_dropped) return;
	if (str == NULL) {
		LERROR("OOM while sending; dropping client");
		sccd_drop_client_asap(client);
	} else if (send(client->fd, str, strlen(str), 0) < 1) {
		LERROR("send failed" SOCKETERROR);
		sccd_drop_client_asap(client);
	}
}

void sccd_socket_consume(Client* client, char* str) {
	sccd_socket_send(client, str);
	free(str);
}

void sccd_socket_send_to_all(const char* str) {
	ListIterator it = iter_get(clients);
	FOREACH(Client*, client, it)
		sccd_socket_send(client, str);
	iter_free(it);
}

void sccd_clients_for_all(void (*cb)(Client* c)) {
	ListIterator it = iter_get(clients);
	FOREACH(Client*, client, it)
		cb(client);
	iter_free(it);
}

static void on_new_connection(Daemon* d, int fd, void* userdata) {
	// Accept connection
	int client_fd = accept(fd, NULL, NULL);
	if (client_fd < 0) {
		LERROR("accept failed" SOCKETERROR);
		return;
	}
	
	// Allocate
	Client* client = malloc(sizeof(Client));
	if (client == NULL)
		goto on_new_connection_fail;
	// Setup
	memset(client, 0, sizeof(Client));
	client->fd = client_fd;
	client->next = client->buffer;
	client->mapper = sccd_mapper_to_mapper(sccd_get_default_mapper());
	if (!list_add(clients, client))
		goto on_new_connection_fail;
	if (!sccd_poller_add(client_fd, on_client_socket_data, client))
		goto on_new_connection_fail;
	// Welcome
	sccd_socket_send(client, "SCCDaemon\n");
	sccd_socket_consume(client, strbuilder_fmt("Version: %s\n", DAEMON_VERSION));
	sccd_socket_consume(client, strbuilder_fmt("PID: %i\n", getpid()));
	sccd_send_controller_list(client);
	sccd_send_profile_list(client);
	if (!sccd_send_error_list(client))
		sccd_socket_send(client, "Ready.\n");
	// ... really warm welcome
	if (client->should_be_dropped) {
		drop(client);
		return;
	}
	DDEBUG("Accepted new connection");
	return;
on_new_connection_fail:
	WARN("Failed to allocate new client, dropping connection");
	close(client_fd);
	// poller is last thing to add and so if code ends here, callback doesn't
	// have to be removed
	if (client != NULL) {
		list_remove(clients, client);
		free(client);
	}
}


bool sccd_socket_init() {
	clients = list_new(Client, 16);
	ASSERT(clients != NULL);
	
	const char* path = scc_get_daemon_socket();
	struct sockaddr_un server_addr;
	memset(&server_addr, 0, sizeof(server_addr));
	server_addr.sun_family = AF_UNIX;
	strncpy(server_addr.sun_path, path, sizeof(server_addr.sun_path) - 1);
	
	// Check if socket file already exists; If yes, delete it.
	if (access(server_addr.sun_path, F_OK) != -1)
		unlink(server_addr.sun_path);
	
#ifdef _WIN32
	WSADATA wsaData;
	int err = WSAStartup(MAKEWORD(2, 2), &wsaData);
	if (err != 0) {
		LERROR("Failed to initialize Winsock2: error %i", err);
		return false;
	}
#endif
	sock = socket(PF_UNIX, SOCK_STREAM, 0);
	if (sock < 0) {
		LERROR("Failed to open control socket" SOCKETERROR);
		return false;
	}

#ifndef _WIN32
	if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &(int){ 1 }, sizeof(int)) < 0) {
#else
	if (setsockopt(sock, SOL_SOCKET, SO_EXCLUSIVEADDRUSE, &(char){ 1 }, sizeof(char)) < 0) {
#endif
		// stupid, but not fatal
		WARN("setsockopt failed" SOCKETERROR);
	}
	if (!sccd_poller_add(sock, &on_new_connection, NULL)) {
		LERROR("sccd_poller_add failed to add listening socket");
		return false;
	}
	
	if (bind(sock, (const struct sockaddr *)&server_addr, sizeof(struct sockaddr_un)) < 0) {
		LERROR("Bind failed" SOCKETERROR);
		return false;
	}
	if (chmod(server_addr.sun_path, 0600) < 0) {
		WARN("chmod failed: %s", strerror(errno));
	}
	if (listen(sock, 5) < 0) {
		LERROR("Listen failed" SOCKETERROR);
		return false;
	}
	LOG("Created control socket %s", server_addr.sun_path);
	return true;
}
