#include "scc/utils/strbuilder.h"
#include "scc/utils/hashmap.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include "scc/action.h"
#include "action_initializers.inc"
#include <stdarg.h>
#include <locale.h>

static map_t actions = NULL;
#define QUOTE(str) #str
#define EXPAND_AND_QUOTE(str) QUOTE(str)

static any_t trash;


void scc_action_register(const char* keyword, scc_action_constructor constructor) {
	if (actions == NULL) actions = hashmap_new();
	
	if (MAP_OK == hashmap_get(actions, keyword, &trash))
		FATAL("Action with keyword '%s' already registered", keyword);
	
	if (MAP_OMEM == hashmap_put(actions, keyword, constructor))
		FATAL("Out of memory while registering '%s'", keyword);
}


bool scc_action_known(const char* keyword) {
	if (actions == NULL) return false;
	return (MAP_OK == hashmap_get(actions, keyword, &trash));
}


void release_action(void* _a) {
	Action* a = (Action*)_a;
	RC_REL(a);
}


ActionList _scc_make_action_list(Action* a1, ...) {
	va_list ap;
	ActionList lst = list_new(Action, 1);
	if (lst == NULL) return NULL;
	list_set_dealloc_cb(lst, &release_action);
	if (a1 != NULL) {
		// a1 == NULL means empty param list
		list_add(lst, a1);
		RC_ADD(a1);
		va_start(ap, a1);
		Action* i = va_arg(ap, Action*);
		while (i != NULL) {
			if (!list_add(lst, i)) {
				va_end(ap);
				list_free(lst);
				return NULL;
			}
			RC_ADD(i);
			i = va_arg(ap, Action*);
		}
		va_end(ap);
	}
	return lst;
}


ActionList scc_copy_action_list(ActionList lst) {
	ActionList cpy = list_new(Action, list_len(lst));
	ListIterator it = iter_get(lst);
	if ((cpy == NULL) || (it == NULL))
		return NULL;
	list_set_dealloc_cb(cpy, &release_action);
	FOREACH(Action*, a, it) {
		RC_ADD(a);
		list_add(cpy, a);
	}
	iter_free(it);
	return cpy;
}


// What follows are default handlers that are set to inputs that every action
// has to have by 'scc_action_init'. Those defaults can only log message about
// not being overriden.

#define RATE_LIMIT(code) do {				\
		static monotime_t last_warn = 0;	\
		monotime_t now = mono_time_ms();	\
		if (now > last_warn + 5000) {		\
			code;							\
			last_warn = now;				\
		}									\
	} while (0)

static void def_button_press(Action* a, Mapper* m) {
	DWARN("Action %s can't handle button press event", a->type);
}

static void def_button_release(Action* a, Mapper* m) {
	DWARN("Action %s can't handle button release event", a->type);
}

static void def_axis(Action* a, Mapper* m, AxisValue value, PadStickTrigger what) {
	RATE_LIMIT(DWARN("Action %s can't handle axis event", a->type));
}

static void def_gyro(Action* a, Mapper* m, const struct GyroInput* value) {
	RATE_LIMIT(DWARN("Action %s can't handle gyro event", a->type));
}

static void def_whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	RATE_LIMIT(DWARN("Action %s can't handle whole stick/pad event", a->type));
}

static void def_trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	RATE_LIMIT(DWARN("Action %s can't handle trigger event", a->type));
}

static Parameter* def_get_property(Action* a, const char* name) {
	if (0 != strcmp("name", name))
		// 'name' is always known, just often undefined
		DWARN("Requested unknown property '%s' from '%s'", name, a->type);
	return NULL;
}


void scc_action_init(Action* a, const char* type, ActionFlags flags,
					void(*dealloc)(Action* a), char*(*to_string)(Action* a)) {
	ASSERT(((flags & AF_ACTION) == 0) || ((flags & AF_ACTION) == AF_ACTION));
	ASSERT(((flags & AF_ERROR) == 0) || ((flags & AF_ERROR) == AF_ERROR));
	RC_INIT(a, dealloc);
	a->type = type;
	a->flags = flags;
	a->to_string = to_string;
	a->describe = NULL;
	a->compress = NULL;
	
	memset(&a->extended, 0, sizeof(a->extended));
	a->extended.size = sizeof(a->extended);
	
	a->button_press = &def_button_press;
	a->button_release = &def_button_release;
	a->get_property = &def_get_property;
	a->axis = &def_axis;
	a->gyro = &def_gyro;
	a->whole = &def_whole;
	a->trigger = &def_trigger;
}


bool scc_action_is_none(Action* a) {
	ASSERT(a != NULL);
	return (a->flags == AF_NONE);
}

bool scc_action_compress(Action** a) {
	if ((a == NULL) || (*a == NULL) || ((*a)->compress == NULL)) return false;
	Action* original = *a;
	Action* compressed = original->compress(original);
	ASSERT(compressed != NULL);
	if (original == compressed)
		return false;
	
	RC_ADD(compressed);
	RC_REL(original);
	*a = compressed;
	return true;
}

char* scc_action_to_string(Action* a) {
	ASSERT(a->to_string != NULL);
	return a->to_string(a);
}

char* scc_action_get_description(Action* a, ActionDescContext ctx) {
	if (a->describe != NULL)
		return a->describe(a, ctx);
	return strbuilder_cpy(a->type);
}

Parameter* scc_action_get_property_with_type(Action* a, const char* name, ParameterType expected_type) {
	if (a == NULL) return NULL;
	Parameter* p = a->get_property(a, name);
	if ((p != NULL) && ((p->type & expected_type) == 0)) {
		RC_REL(p);
		p = NULL;
	}
	return p;
}

ActionOE scc_action_new(const char* keyword, ParameterList params) {
	scc_action_constructor ctr;
	if (MAP_OK != hashmap_get(actions, keyword, (any_t)&ctr))
		return (ActionOE)scc_new_action_error(AEC_UNKNOWN_KEYWORD, "Unknown keyword: '%s'", keyword);
	return ctr(keyword, params);
}

void scc_initialize_none();

__attribute__((constructor)) void whatever() {
	ASSERT(sizeof(ActionFlags) == sizeof(ParameterType));
	ASSERT(sizeof(ActionFlags) == sizeof(ErrorFlag));
	if (actions == NULL) actions = hashmap_new();
	if (0 != strcmp(localeconv()->decimal_point, ".")) {
		WARN("Decimal separator is not dot. Unsetting LC_NUMERIC to prevent parser from going mad");
		setlocale(LC_NUMERIC, "C");
	}
	scc_run_action_initializers();
	scc_initialize_none();
}

