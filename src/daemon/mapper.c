/**
 * SC Controller - Default Mapper
 *
 * This is mapper used by daemon. It outputs to set of virtual devices created
 * with uinput.
 *
 * There are other, specialized mappers, but this one is most important.
 */
#define LOG_TAG "Mapper"
#include "scc/utils/logging.h"
#include "scc/utils/rc.h"
#include "scc/virtual_device.h"
#include "scc/special_action.h"
#include "scc/profile.h"
#include "scc/mapper.h"
#include "scc/config.h"
#include "scc/tools.h"
#include "daemon.h"
#include "errno.h"
#include <stdlib.h>
#ifndef _WIN32
	#include <spawn.h>
#else
	#include <windows.h>
	#include <process.h>
#endif

typedef enum ForceEvent {
	// TODO: Is this still needed?
	FE_STICK	= 1<<0,
	FE_LPAD		= 1<<1,
	FE_RPAD		= 1<<2,
	FE_TRIGGER	= 1<<3,
} ForceEvent;

struct SCCDMapper {
	Mapper				mapper;
	Profile*			profile;
	char*				profile_filename;
	Controller*			controller;
	VirtualDevice*		gamepad;
	VirtualDevice*		keyboard;
	VirtualDevice*		mouse;
	ControllerInput		old_state;
	ControllerInput		state;
	ForceEvent			force_event;
	VirtualDeviceType	to_sync;
	ControllerFlags		c_flags;
	uint8_t				keys[KEY_CNT];
};

static void input(Mapper* _m, ControllerInput* i);

static const char* SCCD_MAPPER_TYPE = "SCCD";


static void set_profile(Mapper* _m, Profile* p, bool cancel_effects) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	RC_REL(m->profile);
	
	// TODO: Before profile is set, mapper should automatically cancel all long-running
	// TODO: effects they may have created. For example, it should stop any active rumble.
	if (p != NULL) RC_ADD(p);
	m->profile = p;
}

static Profile* get_profile(Mapper* _m) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	return m->profile;
}

static void set_controller(Mapper* _m, Controller* c) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	// Controller is not reference-counted
	m->controller = c;
	m->c_flags = (c == NULL) ? 0 : c->flags;
	memset(&m->old_state, 0, sizeof(ControllerInput));
	m->to_sync = 0;
}

static Controller* get_controller(Mapper* _m) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	return m->controller;
}

static ControllerFlags get_flags(Mapper* _m) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	return m->c_flags;
}

static void haptic_effect(Mapper* _m, HapticData* hdata) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	if ((m->controller != NULL) && (m->controller->haptic_effect != NULL))
		m->controller->haptic_effect(m->controller, hdata);
}

void sccd_mapper_deallocate(SCCDMapper* m) {
	if (m->profile != NULL) RC_REL(m->profile);
	free(m);
	DDEBUG("Unloaded mapper 0x%p", m);
}

Mapper* sccd_mapper_to_mapper(SCCDMapper* m) {
	return &m->mapper;
}

bool sccd_mapper_is(Mapper* m) {
	return m->type == SCCD_MAPPER_TYPE;
}

SCCDMapper* sccd_mapper_to_sccd_mapper(Mapper* m) {
	if (m->type == SCCD_MAPPER_TYPE)
		return container_of(m, SCCDMapper, mapper);
	return NULL;
}

inline static VirtualDevice* device_for_button(SCCDMapper* m, Keycode b) {
	if ((b >= BTN_JOYSTICK) && (b <= BTN_GEAR_UP)) {
		m->to_sync |= VTP_GAMEPAD;
		return m->gamepad;
	}
	if ((b >= BTN_MOUSE) && (b <= BTN_TASK))
		return m->mouse;
	m->to_sync |= VTP_KEYBOARD;
	return m->keyboard;
}

static void key_press(Mapper* _m, Keycode b, bool release_press) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	VirtualDevice* d = device_for_button(m, b);
	if (m->keys[b] == 0) {
		scc_virtual_device_key_press(d, b);
	} else if (release_press) {
		scc_virtual_device_key_release(d, b);
		scc_virtual_device_key_press(d, b);
	}
	
	if (m->keys[b] < 0xFE)
		m->keys[b] ++;
}

static void key_release(Mapper* _m, Keycode b) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	VirtualDevice* d = device_for_button(m, b);
	if (m->keys[b] > 1) {
		m->keys[b] --;
	} else if (m->keys[b] == 1) {
		scc_virtual_device_key_release(d, b);
		m->keys[b] --;
	}
}

static bool is_touched(Mapper* _m, PadStickTrigger pad) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	SCButton b = scc_what_to_touch_button(pad);
	return m->state.buttons & b;
}

static bool was_touched(Mapper* _m, PadStickTrigger pad) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	SCButton b = scc_what_to_touch_button(pad);
	return m->old_state.buttons & b;
}

static bool is_pressed(Mapper* _m, SCButton button) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	return m->state.buttons & button;
}

static bool is_virtual_key_pressed(Mapper* _m, Keycode key) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	if ((key < 0) || (key > KEY_CNT)) return false;
	return m->keys[key] > 0;
}

static bool was_pressed(Mapper* _m, SCButton button) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	return m->old_state.buttons & button;
}


static void set_axis(Mapper* _m, Axis axis, AxisValue v) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	scc_virtual_device_set_axis(m->gamepad, axis, v);
	m->to_sync |= VTP_GAMEPAD;
}

static void move_mouse(Mapper* _m, double dx, double dy) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	scc_virtual_device_mouse_move(m->mouse, dx, dy);
	m->to_sync |= VTP_MOUSE;
}

static void move_wheel(Mapper* _m, double dx, double dy) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	scc_virtual_device_mouse_scroll(m->mouse, dx, dy);
	m->to_sync |= VTP_MOUSE;
}

static TaskID schedule(Mapper* m, uint32_t delay, MapperScheduleCallback cb, void* userdata) {
	return sccd_scheduler_schedule(delay, (sccd_scheduler_cb_internal)cb, m, userdata);
}

static void cancel(Mapper* _m, TaskID task_id) {
	sccd_scheduler_cancel(task_id);
}

static bool special_action(Mapper* m, unsigned int sa_action_type, void* sa_data) {
	switch (sa_action_type) {
	case SAT_MENU: {
		SAMenuActionData* sa_menu_data = (SAMenuActionData*)sa_data;
		char* scc_osd_menu = scc_find_binary("scc-osd-menu");
		char* menu = scc_find_menu(sa_menu_data->menu_id);
		if (scc_osd_menu == NULL)
			LERROR("Could not find 'scc-osd-menu'");
		if (menu == NULL)
			LERROR("Could not find menu '%s'", sa_menu_data->menu_id);
		if ((scc_osd_menu != NULL) && (menu != NULL)) {
			const char* argv[] = { scc_osd_menu, "-f", menu, NULL };
			scc_spawn(argv, 0);
		}
		free(scc_osd_menu);
		free(menu);
		return true;
	}
	case SAT_KEYBOARD: {
		char* scc_osd_keyboard = scc_find_binary("scc-osd-keyboard");
		if (scc_osd_keyboard == NULL) {
			LERROR("Could not find 'scc-osd-keyboard'");
		} else {
			const char* argv[] = { scc_osd_keyboard, NULL };
			scc_spawn(argv, 0);
		}
		return true;
	}
	case SAT_CEMUHOOK:
		// TODO: Determine index, multicontroller support here
		sccd_cemuhook_feed(0, (float*)sa_data);
		return true;
	// TODO: All This
	case SAT_PROFILE:
	case SAT_TURNOFF:
	default:
		return false;
	}
}


void sccd_mapper_flush(SCCDMapper* m) {
	// Generate events
	if (m->to_sync & VTP_MOUSE)
		scc_virtual_device_flush(m->mouse);
	if (m->to_sync & VTP_KEYBOARD)
		scc_virtual_device_flush(m->keyboard);
	if (m->to_sync & VTP_GAMEPAD)
		scc_virtual_device_flush(m->gamepad);
	if ((m->controller != NULL) && (m->controller->flush != NULL))
		m->controller->flush(m->controller, &m->mapper);
	m->to_sync = 0;
}

bool sccd_mapper_set_profile_filename(SCCDMapper* m, const char* filename) {
	char* cpy = strbuilder_cpy(filename);
	if (cpy == NULL) return false;
	free(m->profile_filename);
	m->profile_filename = cpy;
	return true;
}

const char* sccd_mapper_get_profile_filename(SCCDMapper* m) {
	return m->profile_filename;
}

/**
 * Applies gamepad configuration settings to 'VirtualDeviceSettings' struct.
 * This is platform-dependent.
 */
static void apply_gamepad_config(Config* c, VirtualDeviceSettings* settings) {
	// TODO: Linux here
#ifdef _WIN32
	const char* output = config_get(c, "output");
	if (0 == strcmp(output, "ds4")) {
		settings->gamepad_type = VGT_DS4;
	} else if (0 == strcmp(output, "x360")) {
		settings->gamepad_type = VGT_X360;
	} else {		// 'auto'
		settings->gamepad_type = VGT_AUTO;
	}
#else
	settings->gamepad_type = VGT_AUTO;
#endif
}


SCCDMapper* sccd_mapper_create() {
	SCCDMapper* m = malloc(sizeof(struct SCCDMapper));
	if (m == NULL) return NULL;
	memset(m, 0, sizeof(struct SCCDMapper));
	Config* c = config_load();

	DEBUG("Creating virtual devices...");
	
	VirtualDeviceSettings settings = { NULL };
	settings.name = NULL; // take default
	apply_gamepad_config(c, &settings);
	m->gamepad = scc_virtual_device_create(VTP_GAMEPAD, &settings);
	if (m->gamepad == NULL) m->gamepad = scc_virtual_device_create(VTP_DUMMY, NULL);
	DDEBUG("Gamepad:  %s", scc_virtual_device_to_string(m->gamepad));
	settings.name = NULL; // take default
	m->mouse = scc_virtual_device_create(VTP_MOUSE, &settings);
	if (m->mouse == NULL) m->mouse = scc_virtual_device_create(VTP_DUMMY, NULL);
	DDEBUG("Mouse:    %s", scc_virtual_device_to_string(m->mouse));
	settings.name = NULL; // take default
	m->keyboard = scc_virtual_device_create(VTP_KEYBOARD, &settings);
	if (m->keyboard == NULL) m->keyboard = scc_virtual_device_create(VTP_DUMMY, NULL);
	DDEBUG("keyboard: %s", scc_virtual_device_to_string(m->keyboard));
	RC_REL(c);
	
	m->mapper.type = SCCD_MAPPER_TYPE;
	m->mapper.get_flags = &get_flags;
	m->mapper.set_profile = &set_profile;
	m->mapper.get_profile = &get_profile;
	m->mapper.set_controller = &set_controller;
	m->mapper.get_controller = &get_controller;
	m->mapper.set_axis = &set_axis;
	m->mapper.move_mouse = &move_mouse;
	m->mapper.move_wheel = &move_wheel;
	m->mapper.key_press = &key_press;
	m->mapper.key_release = &key_release;
	m->mapper.is_touched = &is_touched;
	m->mapper.was_touched = &was_touched;
	m->mapper.is_pressed = &is_pressed;
	m->mapper.was_pressed = &was_pressed;
	m->mapper.is_virtual_key_pressed = &is_virtual_key_pressed;
	m->mapper.release_virtual_buttons = NULL;
	m->mapper.reset_gyros = NULL;
	m->mapper.special_action = &special_action;
	m->mapper.haptic_effect = &haptic_effect;
	m->mapper.schedule = &schedule;
	m->mapper.cancel = &cancel;
	m->mapper.input = &input;
	return m;
}


static void input(Mapper* _m, ControllerInput* i) {
	SCCDMapper* m = container_of(_m, SCCDMapper, mapper);
	if (m->profile == NULL) return;	// Just in case
	
	memcpy(&m->old_state, &m->state, sizeof(ControllerInput));
	memcpy(&m->state, i, sizeof(ControllerInput));
	
	uint8_t force_event = m->force_event;
	m->force_event = 0;
	
	SCButton xor = m->old_state.buttons ^ m->state.buttons;
	SCButton btn_rem = xor & m->old_state.buttons;
	SCButton btn_add = xor & m->state.buttons;
	
	// Buttons
	if ((btn_add != 0) || (btn_rem != 0)) {
		int i = 1;
		SCButton b;
		do {
			b = 1 << (i++);
			if (b & btn_add) {
				Action* a = m->profile->get_button(m->profile, b);
				a->button_press(a, _m);
			} else if (b & btn_rem) {
				Action* a = m->profile->get_button(m->profile, b);
				a->button_release(a, _m);
			}
		} while (b != B_STICKPRESS);
	}
	
	// Stick
	if ((force_event & FE_STICK) || (m->old_state.stick_x != m->state.stick_x)
								|| (m->old_state.stick_y != m->state.stick_y)) {
		Action* a = m->profile->get_stick(m->profile);
		a->whole(a, _m, m->state.stick_x, m->state.stick_y, PST_STICK);
	}
	
	// Gyro
	Controller* c = _m->get_controller(_m);
	if ((c != NULL) && (c->get_gyro_enabled != NULL) && (c->get_gyro_enabled(c))) {
		Action* a = m->profile->get_gyro(m->profile);
		// LOG("GYYYYRO %s", scc_action_to_string(a));
		a->gyro(a, _m, &i->gyro);
	}
	/*
	if c.GyroEnabled() {
		m.profile.Gyro().Gyro(m, i.GPitch(), i.GRoll(), i.GYaw(), i.Q1(), i.Q2(), i.Q3(), i.Q4())
	}
	*/
	
	// Triggers
	if ((force_event & FE_TRIGGER) || (m->old_state.ltrig != m->state.ltrig)) {
		Action *a = m->profile->get_trigger(m->profile, PST_LTRIGGER);
		a->trigger(a, _m, m->old_state.ltrig, m->state.ltrig, PST_LTRIGGER);
	}
	if ((force_event & FE_TRIGGER) || (m->old_state.rtrig != m->state.rtrig)) {
		Action *a = m->profile->get_trigger(m->profile, PST_RTRIGGER);
		a->trigger(a, _m, m->old_state.rtrig, m->state.rtrig, PST_RTRIGGER);
	}
	
	// LPAD
	if ((m->old_state.lpad_x != m->state.lpad_x) || (m->old_state.lpad_y != m->state.lpad_y)) {
		Action* a = m->profile->get_pad(m->profile, PST_LPAD);
		a->whole(a, _m, m->state.lpad_x, m->state.lpad_y, PST_LPAD);
	}
	
	// RPAD
	if ((m->old_state.rpad_x != m->state.rpad_x) || (m->old_state.rpad_y != m->state.rpad_y)) {
		Action* a = m->profile->get_pad(m->profile, PST_RPAD);
		a->whole(a, _m, m->state.rpad_x, m->state.rpad_y, PST_RPAD);
	}
	
	/*
	
	// CPAD (touchpad on DS4 controller)
	if (flags & scc.HAS_CPAD) != 0 {
		if (force_event & FE_PAD != 0) || m.old_state.cpadx != m.state.cpadx || m.old_state.cpady != m.state.cpady {
			m.profile.Pad(scc.CPAD).Whole(m, m.state.cpadx, m.state.cpady, scc.CPAD)
		}
	}
	
	*/
	
	sccd_mapper_flush(m);
}

