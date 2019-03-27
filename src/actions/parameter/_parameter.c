#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include <stdarg.h>
static void release_param(void* _p);

ParameterList _scc_make_param_list(Parameter* p1, ...) {
	va_list ap;
	ParameterList lst = list_new(Parameter, 1);
	if (lst == NULL) return NULL;
	list_set_dealloc_cb(lst, &release_param);
	if (p1 != NULL) {
		// p1 == NULL means empty param list
		list_add(lst, p1);
		RC_ADD(p1);
		va_start(ap, p1);
		Parameter* i = va_arg(ap, Parameter*);
		while (i != NULL) {
			if (!list_add(lst, i)) {
				va_end(ap);
				list_free(lst);
				return NULL;
			}
			RC_ADD(i);
			i = va_arg(ap, Parameter*);
		}
		va_end(ap);
	}
	return lst;
}

ParameterList scc_copy_param_list(ParameterList lst) {
	ParameterList cpy = list_new(Parameter, list_len(lst));
	ListIterator it = iter_get(lst);
	if ((cpy == NULL) || (it == NULL))
		return NULL;
	list_set_dealloc_cb(cpy, &release_param);
	FOREACH(Parameter*, p, it) {
		RC_ADD(p);
		list_add(cpy, p);
	}
	iter_free(it);
	return cpy;
}

char* scc_param_list_to_string(ParameterList lst) {
	if (lst == NULL) return NULL;
	
	StrBuilder* sb = strbuilder_new();
	ListIterator it = iter_get(lst);
	if ((sb == NULL) || (it == NULL))
		goto scc_param_list_to_string_fail;
	if (!strbuilder_add_all(sb, it, &scc_parameter_to_string, ", "))
		goto scc_param_list_to_string_fail;
	iter_free(it);
	return strbuilder_consume(sb);
	
scc_param_list_to_string_fail:
	strbuilder_free(sb);
	iter_free(it);
	return NULL;
}

ParameterList _scc_inline_param_list(Parameter* p1, ...) {
	va_list ap;
	ParameterList lst = list_new(Parameter, 1);
	if ((lst == NULL) || (p1 == NULL)) goto _scc_inline_param_list_fail;
	list_set_dealloc_cb(lst, &release_param);
	if (p1 != (void*)-1) {
		// p1 == (void*)-1 means empty param list
		list_add(lst, p1);
		va_start(ap, p1);
		Parameter* i = va_arg(ap, Parameter*);
		while (i != (void*)-1) {
			if (i == NULL) {
				va_end(ap);
				goto _scc_inline_param_list_fail;
			}
			if (!list_add(lst, i)) {
				va_end(ap);
				goto _scc_inline_param_list_fail;
			}
			i = va_arg(ap, Parameter*);
		}
		va_end(ap);
	}
	return lst;
	
_scc_inline_param_list_fail:
	if (lst != NULL)
		list_free(lst);
	va_start(ap, p1);
	Parameter* i = va_arg(ap, Parameter*);
	while (i != (void*)-1) {
		if (i != NULL) RC_REL(i);
		i = va_arg(ap, Parameter*);
	}
	if ((p1 != (void*)-1) && (p1 != NULL))
		RC_REL(i);
	return NULL;
}

static void release_param(void* _p) {
	Parameter* p = (Parameter*)_p;
	RC_REL(p);
}

char* scc_parameter_to_string(Parameter* p) {
	if (p == NULL)
		return strbuilder_cpy("(null)");
	return p->to_string(p);
}

