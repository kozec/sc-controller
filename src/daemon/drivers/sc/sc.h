#pragma once
#include "scc/driver.h"

typedef struct SCController SCController;
typedef struct SCInput SCInput;
typedef struct SCByBtControllerInput SCByBtControllerInput;

typedef enum {
	SC_WIRED = 1,
	SC_WIRELESS = 2,
	SC_BT = 3,
	SC_DECK = 4,
} SCControllerType;

typedef enum {
	SS_NOT_CONFIGURED = 0,
	SS_READY = 1,
	SS_FAILED = 2
} SCControllerState;

#define MAX_SERIAL_LEN	24
/** MAX_DESC_LEN has to fit "<SCByCable SERIAL>" */
#define MAX_DESC_LEN (15 + MAX_SERIAL_LEN)
/** MAX_DESC_LEN has to fit "scSERIAL" */
#define MAX_ID_LEN (3 + MAX_SERIAL_LEN)


struct SCInput {
	uint8_t			_a1[2];
	uint8_t			ptype;
	uint32_t		seq;
	uint16_t		buttons0;
	uint8_t			buttons1;
	uint8_t			ltrig;
	uint8_t			rtrig;
	uint8_t			_a2[3];
	int16_t			lpad_x;
	int16_t			lpad_y;
	int16_t			rpad_x;
	int16_t			rpad_y;
	uint8_t			_a3[4];
	int16_t			accel_x;
	int16_t			accel_y;
	int16_t			accel_z;
	int16_t			gpitch;
	int16_t			groll;
	int16_t			gyaw;
	int16_t			q1;
	int16_t			q2;
	int16_t			q3;
	int16_t			q4;
	// uint8_t		_a4[16];
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

enum SCButtons {
	// This may be moved later to something shared
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

struct SCController {
	Controller			controller;
	Daemon*				daemon;
	Mapper*				mapper;
	SCControllerType	type;
	SCControllerState	state;
	InputDevice*		dev;
	bool 				long_packet;
	char				serial[MAX_SERIAL_LEN];
	char				desc[MAX_DESC_LEN];
	char				id[MAX_ID_LEN];
	int16_t				idx;
	bool				gyro_enabled;
	uint64_t			auto_id;
	bool				auto_id_used;
	uint16_t			idle_timeout;	// in seconds
	uint8_t				led_level;		// 1 to 100
	HapticData			hdata[2];
	ControllerInput		input;
};

typedef enum {
	PT_INPUT = 0x01,
	PT_HOTPLUG = 0x03,
	PT_IDLE = 0x04,
	PT_OFF = 0x9f,
	PT_AUDIO = 0xb6,
	PT_CLEAR_MAPPINGS = 0x81,
	PT_CONFIGURE = 0x87,
	PT_LED = 0x87,
	PT_CALIBRATE_JOYSTICK = 0xbf,
	PT_CALIBRATE_TRACKPAD = 0xa7,
	PT_SET_AUDIO_INDICES = 0xc1,
	PT_LIZARD_BUTTONS = 0x85,
	PT_LIZARD_MOUSE = 0x8e,
	PT_FEEDBACK = 0x8f,
	PT_RESET = 0x95,
	PT_GET_SERIAL = 0xAE,
	PT_BT_PREFIX = 0xC0
} SCPacketType;

typedef enum {
	PL_LED = 0x03,
	PL_OFF = 0x04,
	PL_FEEDBACK = 0x07,
	PL_CONFIGURE = 0x15,
	PL_CONFIGURE_BT = 0x0f,
	PL_GET_SERIAL = 0x15,
} SCPacketLength;

typedef enum {
	CT_LED = 0x2d,
	CT_CONFIGURE = 0x32,
	CONFIGURE_BT = 0x18,
} SCConfigType;

/** Returns NULL on failure */
SCController* create_usb_controller(Daemon* daemon, InputDevice* dev, SCControllerType type, uint16_t idx);
/** Common for wired and wireless controller */
void handle_input(SCController* sc, SCInput* i);
/** Returns false on failure */
bool read_serial(SCController* sc);
/** Returns false on failure */
bool clear_mappings(SCController* sc);
/** This is effectively reverse of clear_mappings. Returns false on failure */
bool lizard_mode(SCController* sc);
/** Returns false on failure */
bool configure(SCController* sc);
/**
 * Called to inform daemon & mapper about controller being disconnected.
 * Does not deallocate 'sc'.
 */
void disconnected(SCController* sc);

