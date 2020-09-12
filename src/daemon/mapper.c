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

static inline void sa_menu(SAMenuActionData* data) {
	char* scc_osd_menu = NULL;
	StrBuilder* sb = NULL;
	char* menu = NULL;
	
	// Grab data
	Client* osdd = sccd_get_special_client(SCT_OSD);
	if (osdd == NULL) {
		WARN("OSD daemon not available, starting scc-osd-menu. This is suboptimal.");
		scc_osd_menu = scc_find_binary("scc-osd-menu");
		menu = scc_find_menu(data->menu_id);
		if (scc_osd_menu == NULL) {
			LERROR("Could not find 'scc-osd-menu'");
			goto sa_menu_fail;
		}
		if (menu == NULL) {
			LERROR("Could not find menu '%s'", data->menu_id);
			goto sa_menu_fail;
		}
	}
	
	// Build arguments
	StringList argv = list_new(char, 4);
	if (argv == NULL) {
		WARN("OOM while trying to display OSD menu");
		goto sa_menu_fail;
	}
	
	// Any call to strbuilder_cpy may fail on OOM bellow, but that will
	// result only in calling menu binary with wrong arguments, not crashing.
	list_add(argv, strbuilder_cpy((scc_osd_menu != NULL) ? scc_osd_menu : "menu"));
	
	const char* control_with = scc_what_to_string(data->control_with);
	const char* confirm_with = scc_button_to_string(data->confirm_with);
	const char* cancel_with  = scc_button_to_string(data->cancel_with);
	// scc-osd-menu executable can handle most of defaults, but it doesn't know
	// what triggered the menu. Knowing that is important for default value
	// of 'control_with' and 'confirm_with' when menu is bound on button.
	// TODO: Haptics
	// TODO: X, Y
	// TODO: Actual defaults from config
	switch (data->triggered_by) {
	case PST_LPAD:
		if ((control_with == NULL) || (0 == strcmp("DEFAULT", control_with)))
			control_with = "LPAD";
		list_add(argv, strbuilder_cpy("-u"));
		break;
	case PST_RPAD:
		if ((control_with == NULL) || (0 == strcmp("DEFAULT", control_with)))
			control_with = "RPAD";
		list_add(argv, strbuilder_cpy("-u"));
		break;
	case PST_STICK:
		if ((control_with == NULL) || (0 == strcmp("DEFAULT", control_with)))
			control_with = "STICK";
		break;
	case PST_CPAD:
		break;
	default:
		if ((confirm_with == NULL) || (0 == strcmp("DEFAULT", confirm_with)))
			confirm_with = "A";
		break;
	}
	if (confirm_with) {
		list_add(argv, strbuilder_cpy("--confirm-with"));
		list_add(argv, strbuilder_cpy(confirm_with));
	}
	if (control_with) {
		list_add(argv, strbuilder_cpy("--control-with"));
		list_add(argv, strbuilder_cpy(control_with));
	}
	if (cancel_with) {
		list_add(argv, strbuilder_cpy("--cancel-with"));
		list_add(argv, strbuilder_cpy(cancel_with));
	}
	if (strcmp(data->menu_type, "menu") != 0) {
		list_add(argv, strbuilder_cpy("--type"));
		list_add(argv, strbuilder_cpy(data->menu_type));
	}
	if (data->size > 0) {
		if (strcmp(data->menu_type, "hmenu") == 0)
			list_add(argv, strbuilder_cpy("--icon-size"));
		else
			list_add(argv, strbuilder_cpy("--size"));
		list_add(argv, strbuilder_fmt("%i", data->size));
	}
	
	if (osdd == NULL) {
		list_add(argv, strbuilder_cpy("-f"));
		list_add(argv, strbuilder_cpy(menu));
		// Call binary
		if (!list_add(argv, NULL)) {
			// That last list_add adds sentinel and so it's crucial
			WARN("OOM while trying to call 'scc-osd-menu'");
		} else {
			scc_spawn(argv->items, 0);
		}
	} else {
		// Send message to OSD daemon
		StrBuilder* sb = strbuilder_new();
		if (sb != NULL) {
			ListIterator it = iter_get(argv);
			strbuilder_add_all(sb, it, strbuilder_cpy, " ");
			iter_free(it);
			
			strbuilder_insert(sb, 0, "OSD: ");
			strbuilder_add(sb, " -m \"");
			strbuilder_add_escaped(sb, data->menu_id, "\"'", '\\');
			strbuilder_add(sb, "\"\n");
		}
		
		if ((sb == NULL) || strbuilder_failed(sb)) {
			WARN("OOM while trying to talk to OSD daemon");
			goto sa_menu_fail0;
		}
		
		sccd_socket_send(osdd, strbuilder_get_value(sb));
	}
	
sa_menu_fail0:
	// Free memory
	list_set_dealloc_cb(argv, free);
	strbuilder_free(sb);
	list_free(argv);
sa_menu_fail:
	free(scc_osd_menu);
	free(menu);
}

static bool special_action(Mapper* m, unsigned int sa_action_type, void* sa_data) {
	switch (sa_action_type) {
	case SAT_MENU:
		sa_menu((SAMenuActionData*)sa_data);
		return true;
	case SAT_KEYBOARD: {
		char* scc_osd_keyboard = scc_find_binary("scc-osd-keyboard");
		if (scc_osd_keyboard == NULL) {
			LERROR("Could not find 'scc-osd-keyboard'");
		} else {
			char* argv[] = { scc_osd_keyboard, NULL };
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

