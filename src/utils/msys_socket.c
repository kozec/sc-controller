#ifdef _WIN32
#define LOG_TAG "msys_socket"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/intmap.h"
#include "scc/utils/msys_socket.h"
#include <iphlpapi.h>
#include <combaseapi.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

// https://stackoverflow.com/questions/23086038/what-mechanism-is-used-by-msys-cygwin-to-emulate-unix-domain-sockets

intmap_t secrets = NULL;

static bool sec_initialized = false;
static SECURITY_ATTRIBUTES sec_all;
static SECURITY_DESCRIPTOR sd;

LPSECURITY_ATTRIBUTES get_inheritance() {
	if (!sec_initialized) {
		InitializeSecurityDescriptor (&sd, SECURITY_DESCRIPTOR_REVISION);
		SetSecurityDescriptorDacl (&sd, TRUE, 0, FALSE);
		
		sec_all.nLength = sizeof(SECURITY_ATTRIBUTES);
		sec_all.bInheritHandle = TRUE;
		sec_all.lpSecurityDescriptor = &sd;
		sec_initialized = true;
	}
	return &sec_all;
}


int msys_socket(int domain, int type, int protocol) {
	if (domain != PF_UNIX) {
		LERROR("msys_socket: Attempted to create non-PF_UNIX socket");
		WSASetLastError(WSAEPFNOSUPPORT);
		return -1;
	}
	return socket(PF_INET, type, protocol);
}

int msys_bind(int sock, const struct sockaddr* _address, socklen_t address_len) {
	GUID* gid;
	char buffer[256];
	int* gid_data;
	int sinsize = sizeof(struct sockaddr_in);
	struct sockaddr_un* address = (struct sockaddr_un*)_address;
	
	if (address_len != sizeof(struct sockaddr_un)) {
		LERROR("msys_bind: invalid address_len");
		WSASetLastError(WSA_INVALID_PARAMETER);
		return -1;
	}
	
	if (secrets == NULL)
		secrets = intmap_new();
	gid = malloc(sizeof(GUID));
	if ((secrets == NULL) || (gid == NULL) || (intmap_put(secrets, sock, gid) != MAP_OK)) {
		free(gid);
		LERROR("msys_bind: Out of memory");
		WSASetLastError(WSA_NOT_ENOUGH_MEMORY);
		return -1;
	}
	
	CoCreateGuid(gid);
	gid_data = (int*)gid;
	memset(&address->in, 0, sizeof(struct sockaddr_in));
	address->in.sin_family = AF_INET;
	address->in.sin_port = 0;
	address->in.sin_addr.s_addr = inet_addr("127.0.0.1");
	
	if (bind(sock, (const struct sockaddr *)&address->in, sinsize) < 0)
		goto msys_bind_fail;
	if (getsockname(sock, (struct sockaddr *)&address->in, &sinsize) < 0) {
		LERROR("msys_bind: getsockname failed");
		goto msys_bind_fail;
	}
	snprintf(buffer, 255, "!<socket >%i s %08x-%08x-%08x-%08x",
		ntohs(address->in.sin_port), gid_data[0], gid_data[1], gid_data[2], gid_data[3]);
	
	FILE* fp = fopen(address->sun_path, "w");
	if (fp == NULL) {
		WSASetLastError(WSAEACCES);
		goto msys_bind_fail;
	}
	fwrite(buffer, strlen(buffer), 1, fp);
	fclose(fp);
	chmod(address->sun_path, 0600);
	SetFileAttributes(address->sun_path, FILE_ATTRIBUTE_SYSTEM);
	return 0;
	
msys_bind_fail:
	// Jump here if failure is detected after 'gid' is allocated and put into map
	intmap_remove(secrets, sock);
	free(gid);
	return -1;
}

int msys_connect(int sock, const struct sockaddr* _address, socklen_t address_len) {
	char buffer[1024];
	uint32_t* buf_data = (uint32_t*)&buffer;
	struct sockaddr_un* address = (struct sockaddr_un*)_address;
	
	if (address_len != sizeof(struct sockaddr_un)) {
		LERROR("msys_connect: invalid address_len");
		WSASetLastError(WSA_INVALID_PARAMETER);
		return -1;
	}
	
	FILE* fp = fopen(address->sun_path, "r");
	if (fp == NULL) {
		LERROR("msys_connect: file not found");
		WSASetLastError(WSAEFAULT);
		return -1;
	}
	fread(buffer, 1023, 1, fp);
	fclose(fp);
	
	// Expects "!<socket >PORT s SECRET-UUID"
	// e.g. "!<socket >60003 s 013bd668-466879e9-18beeb93-b5579234"
	if (buffer[9] != '>')
		goto msys_connect_not_unix_socket;
	buffer[9] = 0;
	if (0 != strcmp("!<socket ", buffer))
		goto msys_connect_not_unix_socket;
	// 'Header' is OK, parse port and UUID data
	int port, u0, u1, u2, u3;
	sscanf(&buffer[10], "%i s %08x-%08x-%08x-%08x", &port,
				&u0, &u1, &u2, &u3);
	
	memset(&address->in, 0, sizeof(struct sockaddr_in));
	address->in.sin_family = AF_INET;
	address->in.sin_port = htons(port);
	address->in.sin_addr.s_addr = inet_addr("127.0.0.1");
	
	if (connect(sock, (struct sockaddr*)&address->in, sizeof(struct sockaddr_in)) < 0)
		return -1;
	
	buf_data[0] = u0; buf_data[1] = u1;
	buf_data[2] = u2; buf_data[3] = u3;
	send(sock, buffer, 16, 0);
	if (recv(sock, buffer, 16, MSG_WAITALL) < 16)
		goto msys_connect_failed;
	buf_data[0] = getpid();
	buf_data[1] = buf_data[2] = 0;
	send(sock, buffer, 12, 0);
	if (recv(sock, buffer, 12, MSG_WAITALL) < 12)
		goto msys_connect_failed;
	
	return sock;
	
msys_connect_not_unix_socket:
	LERROR("msys_connect: '%s' is not unix socket", address->sun_path);
	WSASetLastError(WSAEFAULT);
	return -1;
msys_connect_failed:
	LERROR("msys_connect: handshake failed");
	WSASetLastError(WSAEFAULT);
	return -1;
}

int msys_accept(int sock, struct sockaddr* address, socklen_t* address_len) {
	char buffer[17];
	struct sockaddr_in sin;
	GUID* gid;
	int* gid_data;
	int* buf_data = (int*)&buffer;
	int sin_len = sizeof(struct sockaddr_in);
	
	if ((secrets == NULL) || (intmap_get(secrets, sock, (any_t*)&gid) != MAP_OK)) {
		LERROR("msys_accept: socket not created with msys_socket");
		return -1;
	}
	
	gid_data = (int*)gid;
	int c = accept(sock, address, address_len);
	if (getsockname(c, (struct sockaddr*)&sin, &sin_len) < 0) {
		LERROR("msys_accept: getsockname failed");
		return -1;
	}
	
	// Remote side has exactly 500ms to send handshake
	DWORD timeout = 500;
	DWORD old_timeout;
	int trash = sizeof(DWORD);
	
	if (getsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&old_timeout, &trash) < 0) {
		LERROR("getsockopt SO_RCVTIMEO failed");
		goto msys_accept_fail;
	}
	if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(DWORD)) < 0) {
		LERROR("setsockopt SO_RCVTIMEO failed");
		goto msys_accept_fail;
	}
	recv(c, buffer, 16, MSG_WAITALL);
	
	if ((gid_data[0] != buf_data[0]) || (gid_data[1] != buf_data[1])
			|| (gid_data[2] != buf_data[2]) || (gid_data[3] != buf_data[3])) {
		// Invalid secret
		WSASetLastError(WSA_OPERATION_ABORTED);
		goto msys_accept_fail;
	}
	
	send(c, buffer, 16, 0);
	if (recv(c, buffer, 12, MSG_WAITALL) < 12) {
		WSASetLastError(WSA_OPERATION_ABORTED);
		goto msys_accept_fail;
	}
	send(c, buffer, 12, 0);
	
	if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const char*)&old_timeout, sizeof(DWORD)) < 0) {
		WSASetLastError(WSA_OPERATION_ABORTED);
		goto msys_accept_fail;
	}
	
	return c;
	
msys_accept_fail:
	LERROR("msys_accept: handshake failed");
	closesocket(c);
	return -1;
}

int msys_close(int sock) {
	GUID* gid;
	
	if ((secrets != NULL) && (intmap_get(secrets, sock, (any_t*)&gid) == MAP_OK)) {
		// Closing socket that msys_bind was called on. This may not be always
		// the case, for example for socket created with msys_accept.
		// It's also OK to call this funciton on any random socket.
		intmap_remove(secrets, sock);
		free(gid);
	}
	
	return closesocket(sock);
}

#endif // _WIN32

