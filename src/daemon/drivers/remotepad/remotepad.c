/**
 * SC Controller - remotepad driver
 *
 * This is implementation or protocol used by Retroarch's Remote RetroPad core.
 *
 * Based on https://github.com/libretro/RetroArch/blob/master/cores/libretro-net-retropad.
 */

#define LOG_TAG "remotepad"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/hashmap.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#ifdef _WIN32
	#include <winsock2.h>
	#include <windows.h>
	#include <iphlpapi.h>
	#include <ws2tcpip.h>
	#define SOCKETERROR ": error %i", WSAGetLastError()
#else
	#include <sys/socket.h>
	#include <netinet/in.h>
	#include <arpa/inet.h>
	#define SOCKETERROR  ": %s", strerror(errno)
#endif
#include "remotepad.h"
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdbool.h>


static Driver driver = {
	.unload = NULL
};

static int sock;
static const int port = 55400;
static map_t controllers;

static void on_data_ready(Daemon* d, int fd, void* userdata) {
	struct remote_joypad_message msg;
	struct sockaddr_in source;
	socklen_t sendsize = sizeof(source);
	if (recvfrom(fd, (char*)&msg, sizeof(msg), 0, (struct sockaddr*)&source, &sendsize) < sizeof(msg)) {
		WARN("Invalid data recieved");
		return;
	}
	
	const char* address = inet_ntoa(source.sin_addr);
	RemotePad* pad = NULL;
	if (hashmap_get(controllers, address, (any_t)&pad) != MAP_OK) {
		// New pad connected, create it and recieve data
		pad = remotepad_new(d, address);
		if ((pad == NULL) || (hashmap_put(controllers, address, pad) != MAP_OK)) {
			LERROR("OOM, failed to add new controller");
			return;
		}
		if (!d->controller_add(&pad->controller)) {
			LERROR("Failed to add new controller");
			hashmap_remove(controllers, address);
			remotepad_free(pad);
			return;
		}
	}
	
	remotepad_input(pad, &msg);
}

void remove_pad_by_address(const char* address) {
	hashmap_remove(controllers, address);
}


Driver* scc_driver_init(Daemon* d) {
	controllers = hashmap_new();
	if (controllers == NULL) {
		LERROR("OOM");
		return NULL;
	}
	
	sock = socket(AF_INET, SOCK_DGRAM, 0);
	if (sock < 0) {
		LERROR("Failed to open control socket" SOCKETERROR);
		return NULL;
	}
	struct sockaddr_in server_addr;
	memset(&server_addr, 0, sizeof(struct sockaddr_in));
	server_addr.sin_family = AF_INET;
	server_addr.sin_port = htons(port);
	server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
	
#ifndef _WIN32
	if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &(int){ 1 }, sizeof(int)) < 0) {
#else
	if (setsockopt(sock, SOL_SOCKET, SO_EXCLUSIVEADDRUSE, &(char){ 1 }, sizeof(char)) < 0) {
#endif
	// stupid, but not fatal
	WARN("setsockopt failed" SOCKETERROR);
	}
	
	if (bind(sock, (const struct sockaddr *)&server_addr, sizeof(struct sockaddr_in)) < 0) {
		LERROR("Bind failed" SOCKETERROR);
		close(sock);
		return NULL;
	}
	
	if (!d->poller_cb_add(sock, &on_data_ready, NULL)) {
		LERROR("Failed to register with poller");
		close(sock);
		return NULL;
	}
	
	LOG("Listening on 0.0.0.0:%i", ntohs(server_addr.sin_port));
	
	return &driver;
}
