/**
 * SC-Controller - Type (verb)
 * 
 * Special type of Macro where keys to press are specified as string.
 * Basically, writing type("iddqd") is same thing as
 * button(KEY_I) ; button(KEY_D) ; button(KEY_D); button(KEY_Q); button(KEY_D)
 * 
 * Recognizes only lowercase letters, uppercase letters, numbers and space.
 * Adding anything else will make action unparseable.
 * 
 * Internally, 'type' is just wrapper for macro.
 */
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/param_checker.h"
#include "scc/conversions.h"
#include "scc/action.h"
#include "tostring.h"

static ParamChecker pc;

const char* KW_TYPE = "type";

typedef struct {
	Action				action;
	ParameterList		params;
	Action*				macro;
} Type;


ACTION_MAKE_TO_STRING(Type, type, KW_TYPE, NULL);


static void type_dealloc(Action* a) {
	Type* t = container_of(a, Type, action);
	RC_REL(t->macro);
	list_free(t->params);
	free(t);
}

static Action* compress(Action* a) {
	// When compressed, 'type' is basically thrown away
	// and macro it generates is used instead.
	Type* t = container_of(a, Type, action);
	ASSERT(t->macro->compress != NULL);
	ASSERT(t->macro->compress(t->macro) == t->macro);
	return t->macro;
}


static ActionOE type_constructor(const char* keyword, ParameterList params) {
	ParamError* err = scc_param_checker_check(&pc, keyword, params);
	if (err != NULL) return (ActionOE)err;
	params = scc_copy_param_list(params);
	
	Type* t = malloc(sizeof(Type));
	if ((t == NULL) || (params == NULL)) {
		free(t);
		list_free(params);
		return (ActionOE)scc_oom_action_error();
	}
	scc_action_init(&t->action, KW_TYPE, AF_ACTION, &type_dealloc, &type_to_string);
	t->action.compress = &compress;
	
	t->params = params;
	t->macro = scc_macro_new(NULL, 0);
	if (t->macro == NULL)
		goto type_constructor_fail;
	
	const char* string = scc_parameter_as_string(params->items[0]);
	for (size_t i=0; i<strlen(string); i++) {
		const char c = string[i];
		char* constant = NULL;
		bool shift = false;
		int64_t key = -1;
		if (c == ' ') {
			key = 57;		// KEY_SPACE
		} else if ((c >= 'A') && (c <= 'Z')) {
			constant = strbuilder_fmt("KEY_%c", c);
			shift = true;
		} else if ((c >= '0') && (c <= '9')) {
			constant = strbuilder_fmt("KEY_%c", c);
		} else if ((c >= 'a') && (c <= 'z')) {
			constant = strbuilder_fmt("KEY_%c",
							(char)((int)c - (int)'a' + (int)'A'));
		}
		if (constant != NULL) {
			key = scc_get_int_constant(constant);
			free(constant);
		}
		
		if (key < 0) {
			RC_REL(&t->action);
			return (ActionOE)scc_new_param_error(AEC_INVALID_VALUE,
				"Invalid character for type(): '%c'", c);
		} else {
			Action* b = scc_button_action_from_keycode(key);
			if ((b != NULL) && shift) {
				Action* shift = scc_button_action_from_keycode(KEY_LEFTSHIFT);
				if (shift == NULL) {
					// OOM
					RC_REL(b);
					b = NULL;
				} else {
					Action* multi = scc_multiaction_combine(shift, b);
					RC_REL(b);
					RC_REL(shift);
					b = multi;
				}
			}
			if ((b == NULL) || (!scc_macro_add_action(t->macro, b))) {
				// OOM
				RC_REL(b);
				goto type_constructor_fail;
			}
			RC_REL(b);	// Reference was taken by macro
		}
	}
	
	return (ActionOE)&t->action;
	
type_constructor_fail:
	RC_REL(&t->action);
	return (ActionOE)scc_oom_action_error();
}

void scc_actions_init_type() {
	scc_param_checker_init(&pc, "s");
	scc_action_register(KW_TYPE, &type_constructor);
}
