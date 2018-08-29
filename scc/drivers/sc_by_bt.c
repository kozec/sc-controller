#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <inttypes.h>
#include <stdbool.h>
#include <limits.h>

#define SC_BY_BT_MODULE_VERSION 3

enum BtInPacketType {
	BUTTON   = 0x0010,
	TRIGGERS = 0x0020,
	STICK    = 0x0080,
	LPAD     = 0x0100,
	RPAD     = 0x0200,
	GYRO     = 0x1800,
	PING     = 0x5000,
};

#define LONG_PACKET 0x80
#define PACKET_SIZE 20

enum SCButtons {
	// This may be moved later to something shared, only this c file needs it right now
	SCB_RPADTOUCH	= 0b10000000000000000000000000000,
	SCB_LPADTOUCH	= 0b01000000000000000000000000000,
	SCB_RPAD		= 0b00100000000000000000000000000,
	SCB_LPAD		= 0b00010000000000000000000000000, // # Same for stick but without LPadTouch
	SCB_STICKPRESS	= 0b00000000000000000000000000001, // # generated internally, not sent by controller
	SCB_RGRIP	 	= 0b00001000000000000000000000000,
	SCB_LGRIP	 	= 0b00000100000000000000000000000,
	SCB_START	 	= 0b00000010000000000000000000000,
	SCB_C		 	= 0b00000001000000000000000000000,
	SCB_BACK		= 0b00000000100000000000000000000,
	SCB_A			= 0b00000000000001000000000000000,
	SCB_X			= 0b00000000000000100000000000000,
	SCB_B			= 0b00000000000000010000000000000,
	SCB_Y			= 0b00000000000000001000000000000,
	SCB_LB			= 0b00000000000000000100000000000,
	SCB_RB			= 0b00000000000000000010000000000,
	SCB_LT			= 0b00000000000000000001000000000,
	SCB_RT			= 0b00000000000000000000100000000,
	SCB_CPADTOUCH	= 0b00000000000000000000000000100, // # Available on DS4 pad
	SCB_CPADPRESS	= 0b00000000000000000000000000010, // # Available on DS4 pad
};

struct SCByBtControllerInput {
	uint16_t type;
	uint32_t buttons;
	uint8_t ltrig;
	uint8_t rtrig;
	int32_t stick_x;
	int32_t stick_y;
	int32_t lpad_x;
	int32_t lpad_y;
	int32_t rpad_x;
	int32_t rpad_y;
	int32_t gpitch;
	int32_t groll;
	int32_t gyaw;
	int32_t q1;
	int32_t q2;
	int32_t q3;
	int32_t q4;
};

struct SCByBtC {
	int fileno;
	char buffer[256];
	uint8_t long_packet;
	struct SCByBtControllerInput state;
	struct SCByBtControllerInput old_state;
};

typedef struct SCByBtC* SCByBtCPtr;

#define BT_BUTTONS_BITS 23

static uint32_t BT_BUTTONS[] = {
	// Bit to SCButton
	SCB_RT,					// 00
	SCB_LT,					// 01
	SCB_RB,					// 02
	SCB_LB,					// 03
	SCB_Y,					// 04
	SCB_B,					// 05
	SCB_X,					// 06
	SCB_A,					// 07
	0, 						// 08 - dpad, ignored
	0, 						// 09 - dpad, ignored
	0, 						// 10 - dpad, ignored
	0, 						// 11 - dpad, ignored
	SCB_BACK,				// 12
	SCB_C,					// 13
	SCB_START,				// 14
	SCB_LGRIP,				// 15
	SCB_RGRIP,				// 16
	SCB_LPAD,				// 17
	SCB_RPAD,				// 18
	SCB_LPADTOUCH,			// 19
	SCB_RPADTOUCH,			// 20
	0,						// 21 - nothing
	SCB_STICKPRESS,			// 22
};

static inline void debug_packet(char* buffer, size_t size) {
	size_t i;
	for(i=0; i<size; i++)
		printf("%02x", buffer[i] & 0xff);
	printf("\n");
}

static char tmp_buffer[256];

/** Returns 1 if state has changed, 2 on read error */
int read_input(SCByBtCPtr ptr) {
	if (ptr->long_packet) {
		// Previous packet had long flag set and this is its 2nd part
		if (read(ptr->fileno, tmp_buffer, PACKET_SIZE) < PACKET_SIZE)
			return 2;
		memcpy(ptr->buffer + PACKET_SIZE, tmp_buffer + 1, PACKET_SIZE - 1);
		ptr->long_packet = 0;
		// debug_packet(ptr->buffer, PACKET_SIZE * 2);
	} else {
		if (read(ptr->fileno, ptr->buffer, PACKET_SIZE) < PACKET_SIZE)
			return 2;
		ptr->long_packet = *((uint8_t*)(ptr->buffer + 1)) == LONG_PACKET;
		if (ptr->long_packet) {
			// This is 1st part of long packet
			return 0;
		}
		// debug_packet(ptr->buffer, PACKET_SIZE);
	}
	
	struct SCByBtControllerInput* state = &(ptr->state);
	struct SCByBtControllerInput* old_state = &(ptr->old_state);
	
	int rv = 0;
	int bit;
	uint16_t type = *((uint16_t*)(ptr->buffer + 2));
	char* data = &ptr->buffer[4];
	if ((type & PING) == PING) {
		// PING packet does nothing
		return 0;
	}
	if ((type & BUTTON) == BUTTON) {
		uint32_t bt_buttons = *((uint32_t*)data);
		uint32_t sc_buttons = 0;
		for (bit=0; bit<BT_BUTTONS_BITS; bit++) {
			if ((bt_buttons & 1) != 0)
				sc_buttons |= BT_BUTTONS[bit];
			bt_buttons >>= 1;
		}
		
		if (rv == 0) { *old_state = *state; state->type = type; rv = 1; }
		state->buttons = sc_buttons;
		data += 3;
	}
	if ((type & TRIGGERS) == TRIGGERS) {
		if (rv == 0) { *old_state = *state; state->type = type; rv = 1; }
		state->ltrig = *(((uint8_t*)data) + 0);
		state->rtrig = *(((uint8_t*)data) + 1);
		data += 2;
	}	
	if ((type & STICK) == STICK) {
		if (rv == 0) { *old_state = *state; state->type = type; rv = 1; }
		state->stick_x = *(((int16_t*)data) + 0);
		state->stick_y = *(((int16_t*)data) + 1);
		data += 4;
	}
	if ((type & LPAD) == LPAD) {
		if (rv == 0) { *old_state = *state; state->type = type; rv = 1; }
		state->lpad_x = *(((int16_t*)data) + 0);
		state->lpad_y = *(((int16_t*)data) + 1);
		data += 4;
	}
	if ((type & RPAD) == RPAD) {
		if (rv == 0) { *old_state = *state; state->type = type; rv = 1; }
		state->rpad_x = *(((int16_t*)data) + 0);
		state->rpad_y = *(((int16_t*)data) + 1);
		data += 4;
	}
	if ((type & GYRO) == GYRO) {
		if (rv == 0) { *old_state = *state; state->type = type; rv = 1; }
		state->gpitch = *(((int16_t*)data) + 0);
		state->groll = *(((int16_t*)data) + 1);
		state->gyaw = *(((int16_t*)data) + 2);
		state->q1 = *(((int16_t*)data) + 3);
		state->q2 = *(((int16_t*)data) + 4);
		state->q3 = *(((int16_t*)data) + 5);
		state->q4 = *(((int16_t*)data) + 6);
		data += 14;
	}
	
	return rv;
}

const int sc_by_bt_module_version(void) {
	return SC_BY_BT_MODULE_VERSION;
}
