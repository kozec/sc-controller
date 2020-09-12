/**
 * SC-Controller - Bindings
 *
 * Functions used by python (and potentially other) bindings.
 * libscc-bindings.so is compiled from this file.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/tokenizer.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/conversions.h"
#include "scc/parameter.h"
#include "scc/bindings.h"
#include "scc/action.h"
#include "scc/config.h"
#include "scc/error.h"
#include "../conversions/conversions.h"
#include <string.h>


extern struct Item keys[];
extern struct Item rels_and_abses[];
extern const uint16_t SCC_KEYCODE_MAX;
extern size_t rels_and_abses_cnt;


const char* scc_action_get_type(Action* a) {
	return a->type;
}

Parameter* scc_action_get_property(Action* a, const char* name) {
	return a->get_property(a, name);
}

Action* scc_action_get_compressed(Action* a) {
	if ((a == NULL) || (a->compress == NULL))
		return NULL;
	Action* compressed = a->compress(a);
	if (a == compressed)
		return NULL;
	
	RC_ADD(compressed);
	return compressed;
}

Parameter* scc_action_get_children(Action* a) {
	if (a->extended.get_children != NULL) {
		ActionList children = a->extended.get_children(a);
		if (children == NULL) {
			WARN("scc_action_get_children: no children returned");
			return NULL;
		}
		Parameter** arr = malloc(sizeof(Parameter*) * list_len(children));
		if (arr == NULL) {
			list_free(children);
			return NULL;
		}
		memset(arr, 0, sizeof(Parameter*) * list_len(children));
		for (size_t i=0; i<list_len(children); i++) {
			arr[i] = scc_new_action_parameter(list_get(children, i));
			if (arr[i] == NULL) {
				for (size_t j=0; j<i; j++)
					RC_REL(arr[j]);
				list_free(children);
				free(arr);
				return NULL;
			}
		}
		Parameter* tup = scc_new_tuple_parameter(list_len(children), arr);
		free(arr);
		list_free(children);
		return tup;
	}
	WARN("scc_action_get_children: no get_children handler");
	return NULL;
}

Action* scc_action_get_child(Action* a) {
	if (a == NULL)
		return NULL;
	if (a->extended.get_child == NULL) {
		WARN("scc_action_get_child: no get_child handler");
		return NULL;
	}
	return a->extended.get_child(a);
}

Action* scc_parameter_as_action(Parameter* p) {
	return p->as_action(p);
}

const char* scc_parameter_as_string(Parameter* p) {
	return p->as_string(p);
}

int64_t scc_parameter_as_int(Parameter* p) {
	return p->as_int(p);
}

float scc_parameter_as_float(Parameter* p) {
	return p->as_float(p);
}


Action* scc_action_ref(Action* a) {
	RC_ADD(a);
	return a;
}

void scc_action_unref(Action* a) {
	// if (a && (a->_rc.count == 1) && ((a->flags & AF_ERROR) == 0))
	//	DDEBUG("Deleting action of type %s", a->type);
	RC_REL(a);
}

Parameter* scc_parameter_ref(Parameter* p) {
	RC_ADD(p);
	return p;
}

void scc_parameter_unref(Parameter* p) {
	// if (p && (p->_rc.count == 1))
	//	DDEBUG("Deleting parameter %p of type 0x%x", p, p->type);
	RC_REL(p);
}

void scc_config_unref(Config* c) {
	RC_REL(c);
}

Parameter* scc_parameter_get_none() {
	return None;
}

ParameterList _scc_tokens_to_param_list(Tokens* tokens, ParamError** err);

ParamOE scc_parse_param_list(const char* str) {
	ParamOE rv = { NULL };
	Tokens* tokens = tokenize(str);
	if (tokens == NULL) return rv;			// OOM
	ParameterList lst = _scc_tokens_to_param_list(tokens, &rv.error);
	tokens_free(tokens);
	if (lst == NULL) return rv;				// OOM
	
	rv.parameter = scc_param_list_to_tuple(lst);
	return rv;
}


const char* scc_error_get_message(APError e) {
	return e.e->message;
}

ActionOE scc_action_new_from_array(const char* keyword, size_t count, Parameter* params[]) {
	ParameterList lst = list_new(Parameter, count);
	if (lst == NULL)
		return (ActionOE)scc_oom_action_error();
	for (int i=0; i<count; i++)
		list_add(lst, params[i]);
	
	ActionOE aoe = scc_action_new(keyword, lst);
	list_free(lst);
	return aoe;
}


extern struct Item keys[];

Keycode scc_hardware_keycode_to_keycode(uint16_t hw) {
	// TODO: Maybe optimize this? It's short loop not called often
	for (Keycode code = 1; code <= SCC_KEYCODE_MAX; code ++) {
#ifdef _WIN32
		if (keys[code].win32_vk == hw)
#else
		if (keys[code].x11_keycode == hw)
#endif
			return code;
	}
	return 0;
}


Parameter* scc_get_const_parameter(const char* name) {
	// Is it int constant?
	int32_t i = scc_get_int_constant(name);
	if (i >= 0)
		return scc_new_const_int_parameter(name, i);
	
	// Is it string constant?
	const char* s = scc_get_string_constant(name);
	if (s != NULL)
		return scc_new_const_string_parameter(s);
	
	return NULL;
}

static size_t scc_get_constants(EnumValue array[], size_t count,
						struct Item lst[], size_t max, const char* prefix) {
	size_t j = 0;
	for (size_t i=0; i<max; i++) {
		if (lst[i].name == NULL)
			continue;
		if ((prefix == NULL) || (strstr(lst[i].name, prefix) == lst[i].name)) {
			if (j < count) {
				array[j].name =  lst[i].name;
				array[j].value = lst[i].value;
			}
			j ++;
		}
	}
	return j;
}

size_t scc_get_key_constants(EnumValue array[], size_t count) {
	return scc_get_constants(array, count, keys, SCC_KEYCODE_MAX, NULL);
}

size_t scc_get_axis_constants(EnumValue array[], size_t count) {
	return scc_get_constants(array, count, rels_and_abses, rels_and_abses_cnt, "ABS_");
}

size_t scc_get_rels_constants(EnumValue array[], size_t count) {
	return scc_get_constants(array, count, rels_and_abses, rels_and_abses_cnt, "REL_");
}

size_t scc_get_button_constants(EnumValue array[], size_t count) {
	return scc_get_constants(array, count, rels_and_abses, rels_and_abses_cnt, "BTN_");
}

void scc_logging_set_handler(logging_handler handler) {
	logging_set_handler(handler);
}

