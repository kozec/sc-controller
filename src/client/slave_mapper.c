/**
 * SC-Controller - Client - Slave Mapper
 *
 * Slave mapper... right now... does almost nothing :)
 * If used with SAProfileAction or SATurnoffAction, it forwads request to daemon.
 */

// TODO: Almost everything here

#define LOG_TAG "SlaveMapper"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/virtual_device.h"
#include "scc/special_action.h"
#include "scc/profile.h"
#include "scc/mapper.h"
#include "scc/tools.h"
#include "client.h"

const char* SLAVE_MAPPER_TYPE = "slave";

struct SlaveMapper {
	Mapper				mapper;
	ControllerFlags		c_flags;
	SCCClient*			client;
	Profile*			profile;
	ControllerInput		old_state;
	ControllerInput		state;
	VirtualDevice*		keyboard;
	VirtualDevice*		mouse;
	VirtualDeviceType	to_sync;
	sccc_sa_handler		sa_handler;
	void*				userdata;
	uint8_t				keys[BTN_DIGI];
};


static bool special_action(Mapper* _m, unsigned int sa_action_type, void* sa_data) {
	// TODO: Move all of this to menu code
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	if (sa_action_type == SAT_PROFILE) {
		char* command = strbuilder_fmt("Profile: %s", sa_data);
		if (command == NULL) {
			LERROR("Failed to send SAT_PROFILE: Out of memory");
			return true;
		}
		int32_t rid = sccc_request(m->client, command);
		free(command);
		if (rid < 0) {
			LERROR("Failed to send SAT_PROFILE: sccc_request failed");
			return true;
		}
		free(sccc_get_response(m->client, rid));
		return true;
	} else if (sa_action_type == SAT_TURNOFF) {
		int32_t rid = sccc_request(m->client, "Turnoff.");
		// TODO: This is documented worngly
		if (rid < 0) {
			LERROR("Failed to send SAT_TURNOFF: sccc_request failed");
			return true;
		}
		free(sccc_get_response(m->client, rid));
		return true;
	} else if (sa_action_type == SAT_MENU) {
		LOG("Menu selected");
		return true;
	} else if (m->sa_handler) {
		return m->sa_handler(_m, sa_action_type, sa_data);
	}
	return false;
}

static bool send_button(Mapper* _m, unsigned int controller_index, Keycode b, bool pressed) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	char command[64];
	if (snprintf(command, 63, "Button: %i %i", b, pressed) >= 63) {
		LERROR("Failed to send button press: Out of memory");
		return false;
	}
	int32_t rid = sccc_request(m->client, command);
	free(sccc_get_response(m->client, rid));
	return true;
}

inline static VirtualDevice* device_for_button(struct SlaveMapper* m, Keycode b) {
	// To prevent games from going absolutelly crazy over rapidly adding and
	// removing virtual pads, slave mapper doesn't work with virtual gamepad.
	if ((b >= BTN_MOUSE) && (b < BTN_JOYSTICK))
		return m->mouse;
	if ((b >= BTN_JOYSTICK) && (b < BTN_DIGI))
		return NULL;
	m->to_sync |= VTP_KEYBOARD;
	return m->keyboard;
}

static void key_press(Mapper* _m, Keycode b, bool release_press) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	VirtualDevice* d = device_for_button(m, b);
	if (d == NULL) {
		// Special case for gamepad. Since creating gamepads on the fly would
		// basically break every game in existence, gamepad events are sent to
		// daemon and handled there instead.
		if (m->keys[b] == 0) {
			send_button(_m, 0, b, 1);
			m->keys[b] = 1;
		}
	} else {
		if (m->keys[b] == 0) {
			scc_virtual_device_key_press(d, b);
		} else if (release_press) {
			scc_virtual_device_key_release(d, b);
			scc_virtual_device_key_press(d, b);
		}
		
		if (m->keys[b] < 0xFE)
			m->keys[b] ++;
	}
}

static void key_release(Mapper* _m, Keycode b) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	VirtualDevice* d = device_for_button(m, b);
	if (d == NULL) {
		// See above
		if (m->keys[b] > 0) {
			send_button(_m, 0, b, 0);
			m->keys[b] = 0;
		}
	} else {
		if (m->keys[b] > 1) {
			m->keys[b] --;
		} else if (m->keys[b] == 1) {
			scc_virtual_device_key_release(d, b);
			m->keys[b] --;
		}
	}
}

static bool is_touched(Mapper* _m, PadStickTrigger pad) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	SCButton b = scc_what_to_touch_button(pad);
	return m->state.buttons & b;
}

static bool was_touched(Mapper* _m, PadStickTrigger pad) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	SCButton b = scc_what_to_touch_button(pad);
	return m->old_state.buttons & b;
}

static bool is_pressed(Mapper* _m, SCButton button) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	return m->state.buttons & button;
}

static bool is_virtual_key_pressed(Mapper* _m, Keycode key) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	if ((key < 0) || (key > BTN_DIGI)) return false;
	return m->keys[key] > 0;
}

static bool was_pressed(Mapper* _m, SCButton button) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	return m->old_state.buttons & button;
}

static void set_profile(Mapper* _m, Profile* p, bool cancel_effects) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	RC_REL(m->profile);
	if (p != NULL) RC_ADD(p);
	m->profile = p;
}

static Profile* get_profile(Mapper* _m) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	return m->profile;
}

static ControllerFlags get_flags(Mapper* _m) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	return m->c_flags;
}

static void haptic_effect(Mapper* _m, HapticData* hdata) { }

static void input(Mapper* _m, ControllerInput* i) { }

static TaskID schedule(Mapper* m, uint32_t delay, MapperScheduleCallback cb, void* userdata) {
	// return sccd_scheduler_schedule(delay, (sccd_scheduler_cb_internal)cb, m, userdata);
	return 0;
}

static void cancel(Mapper* _m, TaskID task_id) {
	// sccd_scheduler_cancel(task_id);
}


void sccc_slave_mapper_set_devices(Mapper* _m, VirtualDevice* keyboard, VirtualDevice* mouse) {
	ASSERT(_m->type == SLAVE_MAPPER_TYPE);
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	m->keyboard = keyboard;
	m->mouse = mouse;
}

void sccc_slave_mapper_feed(Mapper* _m, SCButton button, PadStickTrigger pst, int values[]) {
	ASSERT(_m->type == SLAVE_MAPPER_TYPE);
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	if (button != 0) {
		memcpy(&m->old_state, &m->state, sizeof(ControllerInput));
		if (values[0]) {
			// Pressed
			m->state.buttons |= button;
			Action* a = m->profile->get_button(m->profile, button);
			a->button_press(a, _m);
		} else {
			// Released
			m->state.buttons &= ~button;
			Action* a = m->profile->get_button(m->profile, button);
			a->button_release(a, _m);
		}
	} else if (pst != 0) {
		Action* a = NULL;
		switch (pst) {
		case PST_LPAD:
		case PST_RPAD:
		case PST_CPAD:
			a = m->profile->get_pad(m->profile, pst);
			a->whole(a, _m, values[0], values[1], pst);
			break;
		case PST_STICK:
			a = m->profile->get_stick(m->profile);
			a->whole(a, _m, values[0], values[1], pst);
			break;
		case PST_LTRIGGER:
		case PST_RTRIGGER:
			a = m->profile->get_trigger(m->profile, pst);
			a->trigger(a, _m, values[0], values[1], pst);
			break;
		case PST_GYRO:
			// TODO: This? Needed?
			break;
		}
	}
}

void sccc_slave_mapper_set_sa_handler(Mapper* _m, sccc_sa_handler callback) {
	ASSERT(_m->type == SLAVE_MAPPER_TYPE);
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	m->sa_handler = callback;
}

void sccc_slave_mapper_set_userdata(Mapper* _m, void* data) {
	ASSERT(_m->type == SLAVE_MAPPER_TYPE);
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	m->userdata = data;
}

void* sccc_slave_mapper_get_userdata(Mapper* _m) {
	ASSERT(_m->type == SLAVE_MAPPER_TYPE);
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	return m->userdata;
}


void sccc_slave_mapper_free(Mapper* _m, bool close_attached_devices) {
	ASSERT(_m->type == SLAVE_MAPPER_TYPE);
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	
	if (close_attached_devices) {
		if (m->keyboard != NULL)
			scc_virtual_device_close(m->keyboard);
		if (m->mouse != NULL)
			scc_virtual_device_close(m->mouse);
	}
	RC_REL(m->client);
	RC_REL(m->profile);
	free(m);
}

Mapper* sccc_slave_mapper_new(SCCClient* c) {
	struct SlaveMapper* m = malloc(sizeof(struct SlaveMapper));
	if (m == NULL) return NULL;
	memset(m, 0, sizeof(struct SlaveMapper));
	
	// TODO: All of this. Right now it can work only with OSD menu
	m->mapper.type = SLAVE_MAPPER_TYPE;
	m->client = c;
	m->c_flags = CF_NO_FLAGS;
	RC_ADD(m->client);
	
	m->mapper.get_flags = get_flags;
	m->mapper.set_profile = set_profile;
	m->mapper.get_profile = get_profile;
	m->mapper.set_controller = NULL;
	m->mapper.get_controller = NULL;
	m->mapper.set_axis = NULL;
	m->mapper.move_mouse = NULL;
	m->mapper.move_wheel = NULL;
	m->mapper.key_press = key_press;
	m->mapper.key_release = key_release;
	m->mapper.is_touched = is_touched;
	m->mapper.was_touched = was_touched;
	m->mapper.is_pressed = is_pressed;
	m->mapper.was_pressed = was_pressed;
	m->mapper.release_virtual_buttons = NULL;
	m->mapper.reset_gyros = NULL;
	m->mapper.special_action = special_action;
	m->mapper.haptic_effect = haptic_effect;
	m->mapper.schedule = schedule;
	m->mapper.cancel = cancel;
	m->mapper.input = input;
	return &m->mapper;
}

