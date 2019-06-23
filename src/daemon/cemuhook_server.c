/**
 * SC-Controller - Daemon - CemuHookUDP motion provider
 *
 * Accepts all connections from clients and sends data captured
 * by 'cemuhook' actions to them.
 */

#define LOG_TAG "CemuHook"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/list.h"
#ifdef _WIN32
	#error "Implement me!"
#else
	#include "scc/tools.h"
	#include <netinet/in.h>
	#include <sys/socket.h>
	#include <arpa/inet.h>
	#define SOCKETERROR  ": %s", strerror(errno)
#endif
#include "daemon.h"
#include <sys/types.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <zlib.h>

#define BUFFER_SIZE			1024
#define MAX_PROTO_VERSION	1001
#define CLIENT_TIMEOUT		(5 * 1000)
typedef struct CEHClient {
	struct sockaddr_in	address;
	monotime_t			last_seen;
	uint32_t			next_packet_no;
} CEHClient;
static LIST_TYPE(CEHClient) clients;
static uint32_t next_id = 1;
static int sock;

typedef enum {
	DSUC_VERSIONREQ =	0x100000,
	DSUS_VERSIONRSP =	0x100000,
	DSUC_LISTPORTS =	0x100001,
	DSUS_PORTINFO =		0x100001,
	DSUC_PADDATAREQ =	0x100002,
	DSUS_PADDATARSP =	0x100002,
} MessageType;

struct __attribute__((packed)) PortInfo {
	uint8_t			pad_id;
	uint8_t			state;
	uint8_t			model;
	uint8_t			connection_type;
	uint8_t			mac[6];
	uint8_t			battery;
	uint8_t			active;
};

struct __attribute__((packed)) Message {
	char						header[4];			// 0B
	uint16_t					protocol_version;	// 4B
	uint16_t					packet_size;		// 6B
	uint32_t					crc;				// 8B
	uint32_t					msg_id;				// 12B
	MessageType					message_type;		// 16B
	union {											// 20B
		struct {
			int32_t				count;
			uint8_t				ids[4];
		} list_ports;
		struct {
			uint8_t				flags;
			uint8_t				id;
			uint8_t				mac[6];
		} pad_data_req;
		struct {
			uint16_t			max_version;
			uint16_t			min_version;
		} version_info;
		struct PortInfo			port_info[4];		// size = 12B * 4B
		struct {
			struct PortInfo		pad_info;
			uint32_t			packet_number;
			uint8_t				buttons1;
			uint8_t				buttons2;
			uint8_t				button_ps;
			uint8_t				button_touch;
			uint8_t				sticks[4];			// LX, LY, RX, RY
			uint8_t				analog_buttons[12];
			struct {
				uint8_t			active;
				uint8_t			id;
				uint16_t		x;
				uint16_t		y;
			} touch_point[2];
			uint64_t			motion_timestamp;
			struct {
				float			x;
				float			y;
				float			z;
				float			pitch;
				float			yaw;
				float			roll;
			} accel;
		} pad_data;
	};
};

static void send_msg(struct sockaddr_in* target, struct Message* msg, MessageType type, uint16_t payload_size) {
	size_t size = 20 + payload_size;
	memcpy(msg->header, "DSUS", 4);
	msg->protocol_version = MAX_PROTO_VERSION;
	msg->packet_size = 4 + payload_size;
	msg->message_type = type;
	msg->msg_id = next_id ++;
	msg->crc = 0;
	
	uLong crc = crc32(0, (const Bytef*)msg, size);
	msg->crc = crc;
	
	ssize_t r = sendto(sock, (char*)msg, size, 0, (struct sockaddr*)target, sizeof(struct sockaddr_in));
	if (r < 0) LERROR("sendto failed: " SOCKETERROR);
}

static void fill_port_info(struct PortInfo* pi, uint16_t id, uint8_t active) {
	static uint8_t mac[6] = { 0x05, 0x0C, 0x0C, 0x00, 0x00, 0x01 };
	pi->pad_id = id;
	pi->state = (id == 0) ? 0x02 : 0x00;	// Connected : Disconnected
	pi->connection_type = 0x01;				// Usb
	pi->model = 0x02;						// DS4
	pi->battery = 0x04;						// High
	pi->active = active;
	memcpy(pi->mac, mac, 5);
	pi->mac[5] = 1 + id;
}

static void send_gyro_data(CEHClient* target, uint16_t id, float data[6], uint64_t timestamp) {
	struct Message out;
	memset(&out, 0, sizeof(struct Message));
	fill_port_info(&out.pad_data.pad_info, id, 1);
	memcpy(&out.pad_data.accel, data, sizeof(float) * 6);
	out.pad_data.motion_timestamp = timestamp * 1000;
	out.pad_data.packet_number = target->next_packet_no ++;
	send_msg(&target->address, &out, DSUS_PADDATARSP, 80);
	// DEBUG("Sent data to (0x%x)", target->address.sin_port);
}

static void on_data_recieved(Daemon* d, int fd, void* userdata) {
	char buffer[BUFFER_SIZE];
	struct Message* msg = (struct Message*)&buffer[0];
	struct Message out;
	struct sockaddr_in source;
	socklen_t len = sizeof(struct sockaddr_in);
	ssize_t n = recvfrom(fd, buffer, BUFFER_SIZE, 0, (struct sockaddr*)&source, &len);
	if (n < 0) {
		LERROR("recvfrom: " SOCKETERROR);
		return;
	}
	if ((buffer[0] != 'D') || (buffer[1]!='S') || (buffer[2] != 'U') || (buffer[3] != 'C')) {
		WARN("Recieved invalid message: Invalid header");
		return;
	}
	if (msg->protocol_version > MAX_PROTO_VERSION) {
		WARN("Recieved invalid message: Unsupported version");
		return;
	}
	
	switch (msg->message_type) {
	case DSUC_VERSIONREQ:
		out.version_info.min_version = 0;
		out.version_info.max_version = MAX_PROTO_VERSION;
		send_msg(&source, &out, DSUS_VERSIONRSP, 4);
		break;
	case DSUC_LISTPORTS:
		if ((msg->list_ports.count > 0) && (msg->list_ports.count <= 4)) {
			for (int i=0; i<msg->list_ports.count; i++)
				fill_port_info(&out.port_info[i], msg->list_ports.ids[i], 0);
			send_msg(&source, &out, DSUS_PORTINFO, 12 * msg->list_ports.count);
		}
		break;
	case DSUC_PADDATAREQ: {
		if (!((msg->pad_data_req.flags == 0)
			|| (((msg->pad_data_req.flags & 0x01) != 0) && (msg->pad_data_req.id == 0)))) {
				// Only querying by ID and querying for 1st controller is supported
				WARN("Refusing request: flags=%x id=%x mac=%x:%x:%x:%x:%x:%x",
						msg->pad_data_req.flags, msg->pad_data_req.id,
						msg->pad_data_req.mac[0],
						msg->pad_data_req.mac[1],
						msg->pad_data_req.mac[2],
						msg->pad_data_req.mac[3],
						msg->pad_data_req.mac[4],
						msg->pad_data_req.mac[5]
				);
				break;
		}
		CEHClient* c = NULL;
		FOREACH_IN(CEHClient*, i, clients) {
			if (i->address.sin_port == source.sin_port) {
				// Server listens only on localhost, so it should be safe to assume IP matches
				c = i;
				break;
			}
		}
		if (c == NULL) {
			c = malloc(sizeof(CEHClient));
			if ((c == NULL) || (!list_allocate(clients, 1))) {
				WARN("Out of memory");
				free(c);
				break;
			}
			memcpy(&c->address, &source, sizeof(struct sockaddr_in));
			c->next_packet_no = mono_time_ms() & 0xFFFFFFFF;
			DEBUG("New client (0x%x) added", c->address.sin_port);
			list_add(clients, c);
		}
		c->last_seen = mono_time_ms();
		break;
	}
	default:
		// WARN("Recieved invalid message: Unknown message type");
		return;
	}
}


bool sccd_cemuhook_feed(int index, float data[6]) {
	monotime_t t = mono_time_ms();
	ListIterator it = iter_get(clients);
	while (iter_has_next(it)) {
		CEHClient* c = iter_next(it);
		if ((t > c->last_seen + CLIENT_TIMEOUT) || (t < c->last_seen)) {
			DEBUG("Dropping client (0x%x)", c->address.sin_port);
			iter_remove(it);
		} else {
			send_gyro_data(c, 0, data, (uint64_t)t);
		}
	}
	return true;
}

bool sccd_cemuhook_socket_enable() {
	clients = list_new(CEHClient, 4);
	if (clients == NULL)
		// This may be enabled at random time, so I can't just crash here
		return false;
	
	struct sockaddr_in server_addr;
	memset(&server_addr, 0, sizeof(struct sockaddr_in));
	server_addr.sin_family = AF_INET;
	server_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
	server_addr.sin_port = htons(26760);
	
#ifdef _WIN32
	WSADATA wsaData;
	int err = WSAStartup(MAKEWORD(2, 2), &wsaData);
	if (err != 0) {
		LERROR("Failed to initialize Winsock2: error %i", err);
		return false;
	}
#endif
	sock = socket(AF_INET, SOCK_DGRAM, 0);
	if (sock < 0) {
		LERROR("Failed to open control socket" SOCKETERROR);
		return false;
	}
	
	/*
#ifndef _WIN32
	if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &(int){ 1 }, sizeof(int)) < 0) {
#else
	if (setsockopt(sock, SOL_SOCKET, SO_EXCLUSIVEADDRUSE, &(char){ 1 }, sizeof(char)) < 0) {
#endif
		// stupid, but not fatal
		WARN("setsockopt failed" SOCKETERROR);
	}
	*/
	if (bind(sock, (const struct sockaddr *)&server_addr, sizeof(struct sockaddr_in)) < 0) {
		LERROR("Bind failed" SOCKETERROR);
		return false;
	}
	
	if (!sccd_poller_add(sock, &on_data_recieved, NULL)) {
		LERROR("sccd_poller_add failed to add listening socket");
		return false;
	}
	
	LOG("Created CemuHookUDP Motion Provider");
	return true;
}


__attribute__((constructor)) void check_stuff() {
	ASSERT(sizeof(MessageType) == sizeof(uint32_t));
	ASSERT(sizeof(float) == 4);
}

