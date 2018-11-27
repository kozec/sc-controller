#include "scc/utils/container_of.h"
#include "scc/utils/math.h"
#include "scc/controller.h"
#include "scc/mapper.h"
#include "scc/tools.h"
#include "testmapper.h"
#include <string.h>
#include <stdlib.h>

struct Testmapper {
	Mapper				mapper;
	ControllerInput		old_state;
	ControllerInput		state;
	dvec_t				mouse;
	AxisValue			axes[ABS_CNT];
};

static ControllerFlags get_flags(Mapper* _m) {
	return CF_NO_FLAGS;
}

static bool special_action(Mapper* _m, unsigned int sa_action_type, void* sa_data) {
	return false;
}

static bool is_touched(Mapper* _m, PadStickTrigger pad) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	SCButton b = scc_what_to_touch_button(pad);
	return m->state.buttons & b;
}

static bool was_touched(Mapper* _m, PadStickTrigger pad) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	SCButton b = scc_what_to_touch_button(pad);
	return m->old_state.buttons & b;
}

static bool is_pressed(Mapper* _m, SCButton button) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	return m->state.buttons & button;
}

static bool was_pressed(Mapper* _m, SCButton button) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	return m->old_state.buttons & button;
}

static void move_mouse(Mapper* _m, double dx, double dy) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	m->mouse.x += dx;
	m->mouse.y += dy;
}

static void move_wheel(Mapper* _m, double dx, double dy) {
	// struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	// pass
}

static void set_axis(Mapper* _m, Axis axis, AxisValue v) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	m->axes[axis] = v;
}

void testmapper_free(Mapper* _m) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	free(m);
}

void testmapper_set_buttons(Mapper* _m, SCButton buttons) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	m->old_state.buttons = m->state.buttons;
	m->state.buttons = buttons;
}

void testmapper_reset(Mapper* _m) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	vec_set(m->mouse, 0, 0);
}

void testmapper_get_mouse_position(Mapper* _m, double* x, double* y) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	if (x != NULL) *x = m->mouse.x;
	if (y != NULL) *y = m->mouse.y;
}

AxisValue testmapper_get_axis_position(Mapper* _m, Axis axis) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	return m->axes[axis];
}


Mapper* testmapper_new() {
	struct Testmapper* m = malloc(sizeof(struct Testmapper));
	if (m == NULL) return NULL;
	memset(m, 0, sizeof(struct Testmapper));
	
	testmapper_reset(&m->mapper);
	m->mapper.get_flags = &get_flags;
	m->mapper.set_profile = NULL;
	m->mapper.get_profile = NULL;
	m->mapper.set_controller = NULL;
	m->mapper.get_controller = NULL;
	m->mapper.set_axis = &set_axis;
	m->mapper.move_mouse = &move_mouse;
	m->mapper.move_wheel = &move_wheel;
	m->mapper.key_press = NULL;
	m->mapper.key_release = NULL;
	m->mapper.is_touched = &is_touched;
	m->mapper.was_touched = &was_touched;
	m->mapper.is_pressed = &is_pressed;
	m->mapper.was_pressed = &was_pressed;
	m->mapper.release_virtual_buttons = NULL;
	m->mapper.reset_gyros = NULL;
	m->mapper.special_action = &special_action;
	m->mapper.haptic_effect = NULL;
	m->mapper.schedule = NULL;
	m->mapper.cancel = NULL;
	m->mapper.input = NULL;
	return &m->mapper;
}
