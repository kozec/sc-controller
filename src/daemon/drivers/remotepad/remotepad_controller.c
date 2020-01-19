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
#include "scc/utils/strbuilder.h"
#include "scc/mapper.h"
#include <stdlib.h>
#include "remotepad.h"

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

static const char* remotepad_get_id(Controller* c) {
	RemotePad* pad = container_of(c, RemotePad, controller);
	return pad->id;
}

static const char* remotepad_get_type(Controller* c) {
	return "rpad";
}

static const char* remotepad_get_description(Controller* c) {
	RemotePad* pad = container_of(c, RemotePad, controller);
	return pad->desc;
}

static void remotepad_set_mapper(Controller* c, Mapper* mapper) {
	RemotePad* pad = container_of(c, RemotePad, controller);
	pad->mapper = mapper;
}

static void remotepad_turnoff(Controller* c) {
	// Here is the thing: There is no way to actually turn off remote pad
	// What this does instead if "banning" IP associated with controller
	// for 10s in hope that user manages to close Retroarch in that time.
	//
	// This is done by removing gamepad from daemon, setting 'removed' flag
	// and adding timer that will really remove and deallocate memory
	// when that's done.
	// Timer is started in remotepad_dealloc.
	RemotePad* pad = container_of(c, RemotePad, controller);
	pad->removed = true;
	pad->daemon->controller_remove(c);
	
}

static void remotepad_dealloc_real(void* _pad) {
	RemotePad* pad = (RemotePad*)_pad;
	remove_pad_by_address(pad->address);
	remotepad_free(pad);
	DDEBUG("RemotePad deallocated");
}

void remotepad_free(RemotePad* pad) {
	free((char*)pad->address);
	free(pad);
}

static void remotepad_dealloc(Controller* c) {
	RemotePad* pad = container_of(c, RemotePad, controller);
	pad->removed = true;
	pad->daemon->schedule(10 * 1000, &remotepad_dealloc_real, pad);
}

RemotePad* remotepad_new(Daemon* daemon, const char* address) {
	RemotePad* pad = malloc(sizeof(RemotePad));
	if (pad == NULL) return NULL;
	
	next_id ++;
	memset(pad, 0, sizeof(RemotePad));
	pad->address = strbuilder_cpy(address);
	if (pad->address == NULL) {
		free(pad);
		return NULL;
	}
	pad->daemon = daemon;
	pad->controller.flags = CF_HAS_DPAD | CF_NO_GRIPS | CF_HAS_RSTICK | CF_SEPARATE_STICK;
	pad->controller.deallocate = &remotepad_dealloc;
	pad->controller.get_id = &remotepad_get_id;
	pad->controller.get_type = &remotepad_get_type;
	pad->controller.get_description = &remotepad_get_description;
	pad->controller.set_mapper = &remotepad_set_mapper;
	pad->controller.turnoff = &remotepad_turnoff;
	pad->controller.set_gyro_enabled = NULL;
	pad->controller.get_gyro_enabled = NULL;
	pad->controller.flush = NULL;
	
	snprintf(pad->id, MAX_ID_LEN, "rpad%i", next_id);
	snprintf(pad->desc, MAX_DESC_LEN, "<RemotePad at %s>", address);
	return pad;
}


void remotepad_input(RemotePad* pad, struct remote_joypad_message* msg) {
	if (pad->removed) return;
	SCButton b;
	// LOG("on_data_ready %i %i %i %i", msg->device, msg->index, msg->id, msg->state);
	
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
			pad->input.rpad_y = (msg->state) ? STICK_PAD_MIN : 0;
			break;
		case RETRO_DEVICE_ID_JOYPAD_DOWN:
			pad->input.rpad_y = (msg->state) ? STICK_PAD_MAX : 0;
			break;
		case RETRO_DEVICE_ID_JOYPAD_LEFT:
			pad->input.rpad_x = (msg->state) ? STICK_PAD_MIN : 0;
			break;
		case RETRO_DEVICE_ID_JOYPAD_RIGHT:
			pad->input.rpad_x = (msg->state) ? STICK_PAD_MAX : 0;
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
