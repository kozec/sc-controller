/**
 * SC Controller - remotepad driver
 *
 * This is implementation or protocol used by Retroarch's Remote RetroPad core.
 *
 * Based on https://github.com/libretro/RetroArch/blob/master/cores/libretro-net-retropad.
 */

#include "scc/driver.h"
#include "scc/mapper.h"

/** MAX_DESC_LEN has to fit "<RemotePad at 255.255.255.255>" */
#define MAX_DESC_LEN	32
#define MAX_ID_LEN		24

struct remote_joypad_message {
	int port;
	int device;
	int index;
	int id;
	uint16_t state;
};

typedef struct RemotePad {
	Controller				controller;
	Mapper*					mapper;
	Daemon*					daemon;
	const char*				address;
	char					id[MAX_ID_LEN];
	char					desc[MAX_DESC_LEN];
	ControllerInput			input;
	bool					removed;
} RemotePad;


void remotepad_input(RemotePad* pad, struct remote_joypad_message* msg);
RemotePad* remotepad_new(Daemon* daemon, const char* address);
void remove_pad_by_address(const char* address);
void remotepad_free(RemotePad* pad);

////// Following are declarations from libretro //////

// Buttons for the RetroPad (JOYPAD).
// The placement of these is equivalent to placements on the Super Nintendo controller.
// L2/R2/L3/R3 buttons correspond to the PS1 DualShock.
#define RETRO_DEVICE_ID_JOYPAD_B			0
#define RETRO_DEVICE_ID_JOYPAD_Y			1
#define RETRO_DEVICE_ID_JOYPAD_SELECT		2
#define RETRO_DEVICE_ID_JOYPAD_START		3
#define RETRO_DEVICE_ID_JOYPAD_UP			4
#define RETRO_DEVICE_ID_JOYPAD_DOWN			5
#define RETRO_DEVICE_ID_JOYPAD_LEFT			6
#define RETRO_DEVICE_ID_JOYPAD_RIGHT		7
#define RETRO_DEVICE_ID_JOYPAD_A			8
#define RETRO_DEVICE_ID_JOYPAD_X			9
#define RETRO_DEVICE_ID_JOYPAD_L			10
#define RETRO_DEVICE_ID_JOYPAD_R			11
#define RETRO_DEVICE_ID_JOYPAD_L2			12
#define RETRO_DEVICE_ID_JOYPAD_R2			13
#define RETRO_DEVICE_ID_JOYPAD_L3			14
#define RETRO_DEVICE_ID_JOYPAD_R3			15

#define RETRO_DEVICE_JOYPAD					1
#define RETRO_DEVICE_ANALOG					5
#define RETRO_DEVICE_INDEX_ANALOG_LEFT		0
#define RETRO_DEVICE_INDEX_ANALOG_RIGHT		1
#define RETRO_DEVICE_ID_ANALOG_X			0
#define RETRO_DEVICE_ID_ANALOG_Y			1
