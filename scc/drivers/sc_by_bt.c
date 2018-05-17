#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <inttypes.h>
#include <stdbool.h>
#include <limits.h>

#define SC_BY_BT_MODULE_VERSION 1

enum BtInPacketType {
	BUTTON = 0x14,
	TRIGGERS = 0x24,
	AXIS = 0x84,
};

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
	uint32_t buttons;
	uint8_t ltrig;
	uint8_t rtrig;
	int16_t stick_x;
	int16_t stick_y;
	int16_t lpad_x;
	int16_t lpad_y;
	int16_t rpad_x;
	int16_t rpad_y;
	int32_t gpitch;
	int32_t groll;
	int32_t gyaw;
	int32_t q1;
	int32_t q2;
	int32_t q3;
	int32_t q4;
};

typedef struct SCByBtControllerInput* InputPtr;

#define BT_BUTTONS_BITS 23

static uint32_t BT_BUTTONS[] = {
	// Bit to SCButton
	SCB_RT,					// 00
	SCB_LT,					// 01
	SCB_LB,					// 02
	SCB_RB,					// 03
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


static char buffer[256];

/** Returns 1 if state has changed, 2 on read error. */
int read_input(int fileno, size_t packet_size, InputPtr state, InputPtr old_state) {
	if (read(fileno, &buffer, packet_size) < packet_size)
		return 2;
	
	uint8_t type = *((uint8_t*)(buffer + 2));
	switch (type) {
		case BUTTON: {
			uint32_t bt_buttons = *((uint32_t*)(buffer + 4));
			uint32_t sc_buttons = 0;
			for (int bit=0; bit<BT_BUTTONS_BITS; bit++) {
				if ((bt_buttons & 1) != 0)
					sc_buttons |= BT_BUTTONS[bit];
				bt_buttons >>= 1;
			}
			
			*old_state = *state;
			state->buttons = sc_buttons;
			return 1;
		}
		case AXIS:
			*old_state = *state;
			state->stick_x = *((int16_t*)(buffer + 4));
			state->stick_y = *((int16_t*)(buffer + 6));
			return 1;
		case TRIGGERS:
			*old_state = *state;
			state->ltrig = *((uint8_t*)(buffer + 4));
			state->rtrig = *((uint8_t*)(buffer + 5));
			// printf("IN: %i %i\n", (int)state->ltrig, (int)state->rtrig);
			return 1;
	}
	// printf("IN: %i\n", type);
	// *old_state = *state;
	
	
	return 0;
}

const int sc_by_bt_module_version(void) {
	return SC_BY_BT_MODULE_VERSION;
}
