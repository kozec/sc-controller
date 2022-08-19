/**
 * SC Controller - remotepad driver
 *
 * This is implementation or protocol used by Retroarch's Remote RetroPad core.
 *
 * Based on https://github.com/libretro/RetroArch/blob/master/cores/libretro-net-retropad.
 */

#include <stdlib.h>
#include <stddef.h>
#include <stdio.h>
#include "remotepad.h"

#define REMOTEPAD_MODULE_VERSION 1

static uint32_t next_id = 0;

inline static SCButton libretro_button_to_sc_button(int id) {
	switch (id) {
	case RETRO_DEVICE_ID_JOYPAD_B:			return B_B;
	case RETRO_DEVICE_ID_JOYPAD_Y:			return B_Y;
	case RETRO_DEVICE_ID_JOYPAD_SELECT:		return B_BACK;
	case RETRO_DEVICE_ID_JOYPAD_START:		return B_START;
	case RETRO_DEVICE_ID_JOYPAD_A:			return B_A;
	case RETRO_DEVICE_ID_JOYPAD_X:			return B_X;
	case RETRO_DEVICE_ID_JOYPAD_L:			return B_LB;
	case RETRO_DEVICE_ID_JOYPAD_R:			return B_RB;
	case RETRO_DEVICE_ID_JOYPAD_L2:			return B_LT;
	case RETRO_DEVICE_ID_JOYPAD_R2:			return B_RT;
	case RETRO_DEVICE_ID_JOYPAD_L3:			return B_STICKPRESS;
	case RETRO_DEVICE_ID_JOYPAD_R3:			return B_RPADPRESS;
	default:
		return 0;
	}
}


void remotepad_input(RemotePad* pad, struct remote_joypad_message* msg) {
	SCButton b;
	// LOG("on_data_ready %i %i %i %i", msg->device, msg->index, msg->id, msg->state);
	
	if (sizeof(SCButton) != sizeof(uint32_t)) {
		printf("sizeof(SCButton) != sizeof(uint32_t): %i != %i\n",
				sizeof(SCButton), sizeof(uint32_t));
	}
	
	switch (msg->device) {
	case RETRO_DEVICE_JOYPAD:
		b = libretro_button_to_sc_button(msg->id);
		if (b != 0) {
			if (msg->state)
				pad->input.buttons |= b;
			else
				pad->input.buttons &= ~b;
		}
		
		switch (msg->id) {
		case RETRO_DEVICE_ID_JOYPAD_UP:
			pad->input.lpad_y = (msg->state) ? STICK_PAD_MAX : 0;
			break;
		case RETRO_DEVICE_ID_JOYPAD_DOWN:
			pad->input.lpad_y = (msg->state) ? STICK_PAD_MIN : 0;
			break;
		case RETRO_DEVICE_ID_JOYPAD_LEFT:
			pad->input.lpad_x = (msg->state) ? STICK_PAD_MIN : 0;
			break;
		case RETRO_DEVICE_ID_JOYPAD_RIGHT:
			pad->input.lpad_x = (msg->state) ? STICK_PAD_MAX : 0;
			break;
		case RETRO_DEVICE_ID_JOYPAD_L2:
			pad->input.ltrig = (msg->state) ? TRIGGER_MAX : 0;
			break;
		case RETRO_DEVICE_ID_JOYPAD_R2:
			pad->input.rtrig = (msg->state) ? TRIGGER_MAX : 0;
			break;
		case RETRO_DEVICE_ID_JOYPAD_SELECT:
		case RETRO_DEVICE_ID_JOYPAD_START:
			// If both start+select are pressed, "C" button is emulated
			if ((pad->input.buttons & (B_BACK | B_START)) == (B_BACK | B_START)) {
				pad->input.buttons &= ~(B_BACK | B_START);
				pad->input.buttons |= B_C;
			} else {
				pad->input.buttons &= ~B_C;
			}
		}
	
	case RETRO_DEVICE_ANALOG:
		switch (msg->index) {
		case RETRO_DEVICE_INDEX_ANALOG_LEFT:
			switch (msg->id) {
			case RETRO_DEVICE_ID_ANALOG_X:
				pad->input.stick_x = (AxisValue)msg->state;
				break;
			case RETRO_DEVICE_ID_ANALOG_Y:
				pad->input.stick_y = -(AxisValue)msg->state;
				break;
			}
			break;
		case RETRO_DEVICE_INDEX_ANALOG_RIGHT:
			switch (msg->id) {
			case RETRO_DEVICE_ID_ANALOG_X:
				pad->input.rpad_x = (AxisValue)msg->state;
				break;
			case RETRO_DEVICE_ID_ANALOG_Y:
				pad->input.rpad_y = -(AxisValue)msg->state;
				break;
			}
			break;
		}
	}
	
	pad->mapper->input(pad->mapper, &pad->input);
}


const int remotepad_module_version(void) {
	return REMOTEPAD_MODULE_VERSION;
}
