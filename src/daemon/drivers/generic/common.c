/**
 * Generic SC-Controller driver - common code for generic driver
 */
#include "generic.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/math.h"
#include "scc/controller.h"
#include "scc/tools.h"
#include <math.h>


intmap_t axis_map_new() {
	return intmap_new();
}


static int axis_data_dealloc(any_t item, any_t _data) {
	free(_data);
	return MAP_OK;
}

void axis_map_free(intmap_t map) {
	intmap_iterate(map, axis_data_dealloc, NULL);
	intmap_free(map);
}


void make_id(const char* base, char target[MAX_ID_LEN], int counter) {
	static char buffer[32];
	strncpy(target, base, MAX_ID_LEN - 1);
	target[MAX_ID_LEN - 1] = 0;
	if (counter > 0) {
		snprintf(buffer, 31, "%x", counter);
		size_t len = min(strlen(target), MAX_ID_LEN - strlen(buffer) - 1);
		strcpy(target + len, buffer);
	}
}


static AxisData* parse_axis(json_object* data) {
	bool valid = false;
	AxisData* ad = malloc(sizeof(AxisData));
	if (ad == NULL) return NULL;
	
	ad->clamp_min = STICK_PAD_MIN;
	ad->clamp_max = STICK_PAD_MAX;
	
	int min = json_object_get_double(data, "min", &valid);
	if (!valid) min = -127;
	int max = json_object_get_double(data, "max", &valid);
	if (!valid) max = 128;
	double deadzone = json_object_get_double(data, "deadzone", &valid);
	if (!valid) deadzone = 0;
	ad->center = json_object_get_double(data, "center", &valid);
	if (!valid) ad->center = 0;
	
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

bool load_button_map(const char* name, json_object* json, intmap_t button_map) {
	if (json == NULL) return true;
	
	for(size_t i=0; i<json_object_numkeys(json); i++) {
		const char* key = json_object_get_key(json, i);
		char* value = json_object_get_string(json, key);
		if (value == NULL) continue;
		SCButton b = scc_string_to_button(value);
		char* ok = NULL;
		int k = strtol(key, &ok, 10);
		if (ok == key) {
			WARN("Ignoring mapping for '%s': '%s' is not a number", name, key);
			continue;
		}
		if (b == 0) {
			WARN("Ignoring mapping for '%s': Unknown button '%s'", name, value);
			continue;
		}
		if (intmap_put(button_map, k, (any_t)b) == MAP_OMEM)
			return false;
	}
	
	return true;
}


bool load_axis_map(const char* name, json_object* json, intmap_t axis_map) {
	if (json == NULL) return true;
	
	for(size_t i=0; i<json_object_numkeys(json); i++) {
		const char* key = json_object_get_key(json, i);
		json_object* value = json_object_get_object(json, key);
		if (value == NULL) continue;
		char* ok = NULL;
		int k = strtol(key, &ok, 10);
		if (ok == key) {
			WARN("Ignoring mapping for '%s': '%s' is not a number", name, key);
			continue;
		}
		AxisID axis = parse_axis_name(json_object_get_string(value, "axis"));
		if (axis == A_NONE) {
			WARN("Ignoring mapping for '%s': '%s' is not valid axis name", name,
					json_object_get_string(value, "axis"));
			continue;
		}
		AxisData* data = parse_axis(value);
		if (data == NULL)
			return false;
		data->axis = axis;
		if ((data->axis == A_LTRIG) || (data->axis == A_RTRIG)) {
			data->clamp_min = TRIGGER_MIN;
			data->clamp_max = TRIGGER_MAX;
			data->offset += 1.0;
			data->scale *= 0.5;
		}
		
		if (intmap_put(axis_map, k, (any_t)data) == MAP_OMEM) {
			free(data);
			return false;
		}
	}
	
	return true;
}


void apply_axis(const AxisData* a, double value, ControllerInput* input) {
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
		input->triggers[a->axis - A_LTRIG] = value;
		break;
	case A_LPAD_X:
	case A_LPAD_Y:
		input->buttons |= B_LPADTOUCH | B_LPADPRESS;
		input->axes[a->axis] = value;
		break;
	case A_RPAD_X:
	case A_RPAD_Y:
		input->buttons |= B_RPADTOUCH;
		input->axes[a->axis] = value;
		break;
	default:
		if ((a->axis < A_STICK_X) || (a->axis > A_CPAD_Y))
			break;
		input->axes[a->axis] = value;
		break;
	}
}

