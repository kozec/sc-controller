/**
 * Tools for msys-compatible 'unix' socket.
 * 
 * msys-compatible means that you can connect to it
 * using nc from msys/openbsd-netcat package.
 */

#pragma once

#ifndef _WIN32
#error "You've included msys_socket.h from something that's not Windows. Why?"
#else
#define FD_SETSIZE 512
#include "scc/utils/dll_export.h"
#include <winsock2.h>
#include <windows.h>
#include <ws2tcpip.h>

struct sockaddr_un {
	struct sockaddr_in		in;
	short					sun_family;
	char					sun_path[PATH_MAX];
};


/**
 * Creates msys-compatible 'unix' socket. domain has to be PF_UNIX.
 * Don't forget to call WSAStartup before this.
 */
DLL_EXPORT int msys_socket(int domain, int type, int protocol);

/** Connects to 'unix' socket. address_len has to be sizeof(struct sockaddr_un) */
DLL_EXPORT int msys_connect(int socket, const struct sockaddr* address, socklen_t address_len);

/** Binds socket. address_len has to be sizeof(struct sockaddr_un) */
DLL_EXPORT int msys_bind(int socket, const struct sockaddr *address, socklen_t address_len);

/** Closes socket. You have ot call this for every socket created by msys_socket to free memory  */
DLL_EXPORT int msys_close(int socket);

/** Accepts connection on socket created by msys_socket */
DLL_EXPORT int msys_accept(int sock, struct sockaddr* address, socklen_t* address_len);

/** You can just use listen instead of this */
#define msys_listen(socket, buffer) listen(socket, buffer)


#endif
