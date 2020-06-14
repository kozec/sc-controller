/**
 * Generic SC-Controller driver - common code for generic driver
 */
#include "generic.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/controller.h"
#include "scc/config.h"
#include "scc/mapper.h"
#include "scc/tools.h"
#include <math.h>

#define SPAM_WITH_WARNINGS 0

struct _DerivedFromGenericController {
	Controller				controller;
	GenericController		gc;
};

inline static GenericController* get_gc_from_controller_instance(Controller* c) {
	// This depends on every structure that uses GenericController starting
	// with same field order
	struct _DerivedFromGenericController* dgc;
	dgc = container_of(c, struct _DerivedFromGenericController, controller);
	return &dgc->gc;
}


bool gc_alloc(Daemon* d, GenericController* gc) {
	gc->daemon = d;
	gc->mapper = NULL;
	gc->button_map = intmap_new();
	gc->axis_map = intmap_new();
	gc->button_max = 0;
	gc->emulate_c = false;
	gc->emulate_c_task = 0;
	gc->held_buttons = 0;
	return (gc->button_map != NULL) && (gc->axis_map != NULL);
}

static int axis_data_dealloc(any_t item, any_t _data) {
	free(_data);
	return MAP_OK;
}

void gc_dealloc(GenericController* gc) {
	if (gc->button_map != NULL) {
		intmap_free(gc->button_map);
		gc->button_map = NULL;
	}
	if (gc->axis_map != NULL) {
		intmap_iterate(gc->axis_map, axis_data_dealloc, NULL);
		intmap_free(gc->axis_map);
		gc->axis_map = NULL;
	}
}

const char* gc_get_id(Controller* c) {
	GenericController* gc = get_gc_from_controller_instance(c);
	return gc->id;
}

const char* gc_get_description(Controller* c) {
	GenericController* gc = get_gc_from_controller_instance(c);
	return gc->desc;
}

void gc_set_mapper(Controller* c, Mapper* mapper) {
	GenericController* gc = get_gc_from_controller_instance(c);
	gc->mapper = mapper;
}

void gc_turnoff(Controller* c) {
}

void gc_cancel_padpress_emulation(void* _gc) {
	GenericController* gc = (GenericController*)_gc;
	Daemon* d = gc->daemon;
	bool needs_reschedule = false;
	if ((gc->input.buttons & B_LPADTOUCH) != 0) {
		if ((gc->input.lpad_x == 0) && (gc->input.lpad_y == 0))
			gc->input.buttons &= ~(B_LPADPRESS | B_LPADTOUCH);
		else
			needs_reschedule = true;
	}
	if ((gc->input.buttons & B_RPADTOUCH) != 0) {
		if ((gc->input.rpad_x == 0) && (gc->input.rpad_y == 0))
			gc->input.buttons &= ~B_RPADTOUCH;
		else
			needs_reschedule = true;
	}
	if (needs_reschedule)
		gc->padpressemu_task = d->schedule(PADPRESS_EMULATION_TIMEOUT,
										gc_cancel_padpress_emulation, gc);
	else
		gc->padpressemu_task = 0;
	
	if (gc->mapper != NULL)
		gc->mapper->input(gc->mapper, &gc->input);
}

void gc_make_id(const char* base, GenericController* gc) {
	int counter = 0;
	do {
		static char buffer[MAX_ID_LEN];
		strncpy(gc->id, base, MAX_ID_LEN - 1);
		gc->id[MAX_ID_LEN - 1] = 0;
		if (counter > 0) {
			snprintf(buffer, 31, "%x", counter);
			size_t len = min(strlen(gc->id), MAX_ID_LEN - strlen(gc->id) - 1);
			strcpy(gc->id + len, buffer);
		}
		counter ++;
	} while (gc->daemon->get_controller_by_id(gc->id) != NULL);
}


static AxisID parse_axis_name(const char* s) {
	if (s == NULL) return A_NONE;
	// TODO: Use stricmp here?
	switch (s[0]) {
	case 'L':
	case 'l':
		if (0 == strcmp("lpad_x", s)) return A_LPAD_X;
		if (0 == strcmp("lpad_y", s)) return A_LPAD_Y;
		if (0 == strcmp("ltrig", s))  return A_LTRIG;
		break;
	case 'R':
	case 'r':
		if (0 == strcmp("rpad_x", s)) return A_RPAD_X;
		if (0 == strcmp("rpad_y", s)) return A_RPAD_Y;
		if (0 == strcmp("rtrig", s))  return A_RTRIG;
		break;
	case 'S':
	case 's':
		if (0 == strcmp("stick_x", s)) return A_STICK_X;
		if (0 == strcmp("stick_y", s)) return A_STICK_Y;
		break;
	}
	return A_NONE;
}

static AxisData* parse_axis(Config* ccfg, const char* key) {
	char buffer[256];
	AxisData* ad = malloc(sizeof(AxisData));
	if (ad == NULL) return NULL;
	
	ad->clamp_min = STICK_PAD_MIN;
	ad->clamp_max = STICK_PAD_MAX;
	
	snprintf(buffer, 256, "axes/%s/min", key);
	int min = config_get_double(ccfg, buffer);
	snprintf(buffer, 256, "axes/%s/max", key);
	int max = config_get_double(ccfg, buffer);
	if ((min == 0) && (max == 0)) {
#ifdef _WIN32
		// Those are default values with DInput
		min = 0;
		max = 65535;
#else
		// Those are defaults with anything else
		min = -127;
		max = 128;
#endif
	}
	snprintf(buffer, 256, "axes/%s/deadzone", key);
	double deadzone = config_get_double(ccfg, buffer);
	snprintf(buffer, 256, "axes/%s/center", key);
	ad->center = config_get_double(ccfg, buffer);
	
	ad->offset = 0;
	if ((max >= 0) && (min >= 0))
		ad->offset = 1;
	if (min == max) {
		ad->scale = 1.0;
	} else {
		ad->scale = -2.0 / (double)(min - max);
		if (max > min)
			ad->offset *= -1.0;
	}
	ad->deadzone = fabs(deadzone * ad->scale);
	return ad;
}

static bool load_axis_map(GenericController* gc, Config* ccfg) {
	const char* keys[64];
	char buffer[64];
	ssize_t count;
	count = (ccfg == NULL) ? 0 : config_get_strings(ccfg, "axes", keys, 64);
	for (ssize_t i=0; i<count; i++) {
		char* ok = NULL;
		int k = strtol(keys[i], &ok, 10);
		if (ok == keys[i]) {
			WARN("Ignoring mapping for '%s': '%s' is not a number",
							gc->desc, keys[i]);
			continue;
		}
		snprintf(buffer, 64, "axes/%s/axis", keys[i]);
		AxisID axis = parse_axis_name(config_get(ccfg, buffer));
		if (axis == A_NONE) {
			WARN("Ignoring mapping for '%s': '%s' is not valid axis name",
							gc->desc, config_get(ccfg, buffer));
			continue;
		}
		AxisData* data = parse_axis(ccfg, keys[i]);
		if (data == NULL)
			return false;						// OOM
		data->axis = axis;
#ifndef _WIN32
		// TODO: Find why this breaks dinput
		if ((data->axis == A_LTRIG) || (data->axis == A_RTRIG)) {
			data->clamp_min = TRIGGER_MIN;
			data->clamp_max = TRIGGER_MAX;
			data->offset += 1.0;
			data->scale *= 0.5;
		}
#endif
		
		if (intmap_put(gc->axis_map, k, (any_t)data) == MAP_OMEM) {
			free(data);
			return false;						// OOM
		}
	}
	return true;
}

static bool load_button_map(GenericController* gc, Config* ccfg) {
	const char* keys[64];
	char buffer[64];
	ssize_t count;
	count = (ccfg == NULL) ? 0 : config_get_strings(ccfg, "buttons", keys, 64);
	for (ssize_t i=0; i<count; i++) {
		char* ok = NULL;
		int k = strtol(keys[i], &ok, 10);
		if (ok == keys[i]) {
			WARN("Ignoring mapping for '%s': '%s' is not a number",
							gc->desc, keys[i]);
			continue;
		}
		snprintf(buffer, 64, "buttons/%s", keys[i]);
		SCButton b = scc_string_to_button(config_get(ccfg, buffer));
		if (b == 0) {
			WARN("Ignoring mapping for '%s': Unknown button '%s'",
							gc->desc, keys[i]);
			continue;
		}
		if (intmap_put(gc->button_map, k, (any_t)b) == MAP_OMEM)
			return false;
		if (k > gc->button_max)
			gc->button_max = k;
	}
	return true;
}

bool gc_load_mappings(GenericController* gc, Config* ccfg) {
	if (ccfg == NULL)
		return true;
	if (!load_axis_map(gc, ccfg))
		return false;
	if (!load_button_map(gc, ccfg))
		return false;
	gc->emulate_c = config_get_int(ccfg, "emulate_c");
	return true;
}

static void c_emulation_callback(void* _gc) {
	GenericController* gc = (GenericController*)_gc;
	gc->input.buttons |= gc->held_buttons;
	gc->emulate_c_task = 0;
	gc->held_buttons = 0;
	if (gc->mapper != NULL)
		gc->mapper->input(gc->mapper, &gc->input);
}

bool apply_button(Daemon* d, GenericController* gc, uintptr_t code, uint8_t value) {
	any_t val;
	if (intmap_get(gc->button_map, code, &val) == MAP_OK) {
		if ((gc->emulate_c) &&
					(((SCButton)val == B_START) || ((SCButton)val == B_BACK))) {
			if (value) {
				if (gc->emulate_c_task) {
					d->cancel(gc->emulate_c_task);
					gc->emulate_c_task = 0;
					val = (any_t)B_C;
				} else {
					gc->emulate_c_task = d->schedule(C_EMULATION_TIMEOUT,
							c_emulation_callback, gc);
					gc->held_buttons |= (SCButton)val;
					return false;
				}
			} else {
				gc->input.buttons &= ~B_C;
				gc->held_buttons = 0;
				if (gc->emulate_c_task) {
					d->cancel(gc->emulate_c_task);
					gc->emulate_c_task = 0;
				}
			}
		}
		if (value && !(gc->input.buttons & (SCButton)val)) {
			gc->input.buttons |= (SCButton)val;
			return true;
		} else if (!value && (gc->input.buttons | (SCButton)val)) {
			gc->input.buttons &= ~(SCButton)val;
			return true;
		}
#if SPAM_WITH_WARNINGS
	} else {
		WARN("Unknown keycode %i", code);
#endif
	}
	return false;
}

bool apply_axis(GenericController* gc, uintptr_t code, double value) {
	AxisData* a;
	if (intmap_get(gc->axis_map, code, (any_t)&a) != MAP_OK) {
#if SPAM_WITH_WARNINGS
		WARN("Unknown axis %i", code);
#endif
		return false;
	}
	
	value = (value * a->scale) + a->offset;
	if ((value >= -a->deadzone) && (value <= a->deadzone))
		value = 0;
	else
		value = clamp(a->clamp_min, value * a->clamp_max, a->clamp_max);
	
	switch (a->axis) {
		case A_NONE:
			break;
		case A_LTRIG:
		case A_RTRIG:
			gc->input.triggers[a->axis - A_LTRIG] = value;
			break;
		case A_LPAD_X:
		case A_LPAD_Y:
			gc->input.buttons |= B_LPADTOUCH | B_LPADPRESS;
			gc->input.axes[a->axis] = value;
			break;
		case A_RPAD_X:
		case A_RPAD_Y:
			gc->input.buttons |= B_RPADTOUCH;
			gc->input.axes[a->axis] = value;
			break;
		default:
			if ((a->axis < A_STICK_X) || (a->axis > A_CPAD_Y))
				break;
			gc->input.axes[a->axis] = value;
			break;
	}
	return true;
}

