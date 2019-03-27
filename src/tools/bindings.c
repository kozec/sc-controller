/**
 * SC-Controller - Bindings
 *
 * Functions used by python (and potentially other) bindings.
 * libscc-bindings.so is compiled from this file.
 */
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/conversions.h"
#include "scc/bindings.h"
#include "scc/error.h"
#include "../conversions/conversions.h"
#include <string.h>


extern struct Item keys[];
extern struct Item rels_and_abses[];
extern const uint16_t SCC_KEYCODE_MAX;
extern const size_t SCC_REL_ABS_MAX;

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

Action* scc_action_get_child(Action* a) {
	if ((a == NULL) || (a->extended.get_child == NULL))
		return NULL;
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
}

void scc_action_unref(Action* a) {
	if (a && (a->_rc.count == 1) && ((a->flags & AF_ERROR) == 0))
		DDEBUG("Deleting action of type %s", a->type);
	RC_REL(a);
}

Parameter* scc_parameter_ref(Parameter* p) {
	RC_ADD(p);
}

void scc_parameter_unref(Parameter* p) {
	if (p && (p->_rc.count == 1))
		DDEBUG("Deleting parameter %p of type 0x%x", p, p->type);
	RC_REL(p);
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

Parameter* scc_get_string_const_parameter(const char* s) {
	const char* cnst = scc_get_string_constant(s);
	if (cnst == NULL) return NULL;
	
	return scc_new_const_string_parameter(cnst);
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
	return scc_get_constants(array, count, rels_and_abses, SCC_REL_ABS_MAX, "ABS_");
}

size_t scc_get_rels_constants(EnumValue array[], size_t count) {
	return scc_get_constants(array, count, rels_and_abses, SCC_REL_ABS_MAX, "REL_");
}

size_t scc_get_button_constants(EnumValue array[], size_t count) {
	return scc_get_constants(array, count, rels_and_abses, SCC_REL_ABS_MAX, "BTN_");
}

