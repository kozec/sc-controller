#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/list.h"
#include "scc/utils/math.h"
#include "scc/controller.h"
#include "scc/mapper.h"
#include "scc/tools.h"
#include "testmapper.h"
#include <string.h>
#include <stdlib.h>

typedef struct Task {
	MapperScheduleCallback		callback;
	void*						userdata;
	bool						canceled;
	uint32_t					at;
} Task;

typedef LIST_TYPE(Task) Schedule;

struct Testmapper {
	Mapper						mapper;
	ControllerInput				old_state;
	ControllerInput				state;
	dvec_t						mouse;
	AxisValue					axes[ABS_CNT];
	uint8_t						keys[KEY_CNT];
	Schedule					schedule;
	StrBuilder*					keylog;
	uint32_t					now;
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

static bool is_virtual_key_pressed(Mapper* _m, Keycode key) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	if ((key < 0) || (key > KEY_CNT)) return false;
	return m->keys[key] > 0;
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
}

static void set_axis(Mapper* _m, Axis axis, AxisValue v) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	m->axes[axis] = v;
}

static void key_press(Mapper* _m, Keycode b, bool release_press) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	if ((m->keys[b] == 0) || release_press) {
		if (strlen(strbuilder_get_value(m->keylog)) == 0)
			strbuilder_addf(m->keylog, "%i", b);
		else
			strbuilder_addf(m->keylog, ", %i", b);
	}
	
	if (m->keys[b] < 0xFE)
		m->keys[b] ++;
}

static void key_release(Mapper* _m, Keycode b) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	if (m->keys[b] > 0)
		m->keys[b] --;
}

static TaskID schedule(Mapper* _m, uint32_t delay, MapperScheduleCallback cb, void* userdata) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	if (!list_allocate(m->schedule, 1)) return 0;		// OOM
	Task* task = malloc(sizeof(Task));
	if (task == NULL) return 0;							// OOM
	task->userdata = userdata;
	task->canceled = false;
	task->callback = cb;
	task->at = m->now + delay;
	list_add(m->schedule, task);
	
	return (TaskID)task;
}

static void cancel(Mapper* _m, TaskID task_id) {
	Task* task = (Task*)task_id;
	task->canceled = true;
}


void testmapper_free(Mapper* _m) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	strbuilder_free(m->keylog);
	list_foreach(m->schedule, &free);
	list_free(m->schedule);
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
	memset(m->keys, 0, KEY_CNT);
	strbuilder_clear(m->keylog);
	list_foreach(m->schedule, &free);
	list_clear(m->schedule);
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

const char* testmapper_get_keylog(Mapper* _m) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	return strbuilder_get_value(m->keylog);
}

size_t testmapper_get_key_count(Mapper* _m) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	size_t c = 0;
	for (size_t i=0; i<KEY_CNT; i++)
		if (m->keys[i])
			c ++;
	
	return c;
}

bool testmapper_has_scheduled(Mapper* _m) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	return list_len(m->schedule) > 0;
}

bool testmapper_run_scheduled(Mapper* _m, uint32_t time_delta) {
	struct Testmapper* m = container_of(_m, struct Testmapper, mapper);
	m->now += time_delta;
	FOREACH_IN(Task*, task, m->schedule) {
		if (task->at <= m->now) {
			list_remove(m->schedule, task);
			if (!task->canceled)
				task->callback(_m, task->userdata);
			free(task);
			return testmapper_has_scheduled(_m);
		}
	}
	return testmapper_has_scheduled(_m);
}


Mapper* testmapper_new() {
	struct Testmapper* m = malloc(sizeof(struct Testmapper));
	if (m == NULL) return NULL;
	memset(m, 0, sizeof(struct Testmapper));
	
	m->now = 1;
	m->keylog = strbuilder_new();
	m->schedule = list_new(Task, 5);
	if ((m->keylog == NULL) || (m->schedule == NULL)) {
		list_free(m->schedule);
		strbuilder_free(m->keylog);
		free(m);
		return NULL;
	}
	testmapper_reset(&m->mapper);
	m->mapper.type = "testmapper";
	m->mapper.get_flags = &get_flags;
	m->mapper.set_profile = NULL;
	m->mapper.get_profile = NULL;
	m->mapper.set_controller = NULL;
	m->mapper.get_controller = NULL;
	m->mapper.set_axis = &set_axis;
	m->mapper.move_mouse = &move_mouse;
	m->mapper.move_wheel = &move_wheel;
	m->mapper.key_press = &key_press;
	m->mapper.key_release = &key_release;
	m->mapper.is_touched = &is_touched;
	m->mapper.was_touched = &was_touched;
	m->mapper.is_pressed = &is_pressed;
	m->mapper.was_pressed = &was_pressed;
	m->mapper.release_virtual_buttons = NULL;
	m->mapper.is_virtual_key_pressed = &is_virtual_key_pressed;
	m->mapper.reset_gyros = NULL;
	m->mapper.special_action = &special_action;
	m->mapper.haptic_effect = NULL;
	m->mapper.schedule = &schedule;
	m->mapper.cancel = &cancel;
	m->mapper.input = NULL;
	return &m->mapper;
}
